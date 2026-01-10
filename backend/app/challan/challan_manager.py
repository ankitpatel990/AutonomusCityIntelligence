"""
Challan Generation & Management (FRD-09)

Digital challan generation system that:
- Creates challans from violations
- Tracks payment status
- Manages automatic fine deduction
- Provides statistics and reporting
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Any
import time
import json

from sqlalchemy.orm import Session
from app.database.database import SessionLocal
from app.database.models import (
    Challan as ChallanDB,
    Violation as ViolationDB,
    ChallanTransaction as TransactionDB
)

from .violation_detector import ViolationEvent, ViolationType
from .vehicle_owner_db import VehicleOwnerDatabase, VehicleOwnerRecord


class ChallanStatus(str, Enum):
    """Challan payment status"""
    ISSUED = "ISSUED"
    PAID = "PAID"
    PENDING = "PENDING"
    CANCELLED = "CANCELLED"


@dataclass
class ChallanRecord:
    """Digital traffic challan record"""
    challan_id: str
    violation_id: str
    vehicle_id: str
    number_plate: str
    owner_id: str
    owner_name: str
    violation_type: str
    violation_description: str
    violation_timestamp: float
    issued_at: float
    fine_amount: float
    status: ChallanStatus
    location: str
    location_name: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    paid_at: Optional[float] = None
    transaction_id: Optional[str] = None
    evidence: dict = field(default_factory=dict)


class ChallanManager:
    """
    Manage digital traffic challans
    
    Responsibilities:
    - Generate challans from violations
    - Process payments (automatic and manual)
    - Track challan status
    - Calculate revenue statistics
    - Persist to database
    
    Integrates with VehicleOwnerDatabase for owner lookup
    and wallet balance management.
    """
    
    # Violation descriptions
    VIOLATION_DESCRIPTIONS = {
        'RED_LIGHT': "Violated red light signal",
        'SPEEDING': "Exceeded speed limit",
        'WRONG_DIRECTION': "Driving in wrong direction",
        'WRONG_LANE': "Driving in wrong lane",
        'NO_STOPPING': "Failed to stop at stop sign"
    }
    
    def __init__(self, vehicle_owner_db: VehicleOwnerDatabase):
        """
        Initialize challan manager
        
        Args:
            vehicle_owner_db: VehicleOwnerDatabase instance for owner lookup
        """
        self.vehicle_owner_db = vehicle_owner_db
        
        # In-memory challans
        self.challans: List[ChallanRecord] = []
        self.challan_counter = 0
        
        # Statistics
        self.total_challans = 0
        self.total_revenue = 0.0
        self.pending_revenue = 0.0
        
        # Processed violations tracking (to avoid duplicates)
        self._processed_violations: set = set()
        
        # WebSocket emitter for real-time notifications
        self._ws_emitter = None
        
        # Load existing challans
        self._load_from_database()
        
        print(f"✅ Challan Manager initialized ({len(self.challans)} challans loaded)")
    
    def set_ws_emitter(self, emitter):
        """Set WebSocket emitter for real-time notifications"""
        self._ws_emitter = emitter
    
    def _load_from_database(self):
        """Load existing challans from database"""
        try:
            db = SessionLocal()
            challans = db.query(ChallanDB).order_by(ChallanDB.violation_timestamp.desc()).limit(500).all()
            
            for c in challans:
                record = ChallanRecord(
                    challan_id=c.challan_id,
                    violation_id=c.violation_id,
                    vehicle_id=c.number_plate,  # Use number_plate as vehicle_id
                    number_plate=c.number_plate,
                    owner_id="",
                    owner_name=c.owner_name,
                    violation_type=c.violation_type,
                    violation_description=c.violation_description or "",
                    violation_timestamp=c.violation_timestamp,
                    issued_at=c.violation_timestamp,
                    fine_amount=c.fine_amount,
                    status=ChallanStatus(c.status),
                    location=c.location,
                    paid_at=c.payment_timestamp,
                    transaction_id=c.transaction_id
                )
                self.challans.append(record)
                self._processed_violations.add(c.violation_id)
                
                # Update statistics
                self.total_challans += 1
                if record.status == ChallanStatus.PAID:
                    self.total_revenue += record.fine_amount
                else:
                    self.pending_revenue += record.fine_amount
            
            # Get counter from max challan ID
            if self.challans:
                max_id = max(
                    int(c.challan_id.split('-')[1]) 
                    for c in self.challans 
                    if c.challan_id.startswith('CH-')
                )
                self.challan_counter = max_id
            
            db.close()
        except Exception as e:
            print(f"⚠️ Could not load challans from database: {e}")
    
    def generate_challan(self, violation: ViolationEvent) -> Optional[str]:
        """
        Generate challan from violation
        
        Args:
            violation: ViolationEvent from detector
        
        Returns:
            challan_id if successful, None otherwise
        """
        # Check if already processed
        if violation.violation_id in self._processed_violations:
            print(f"⚠️ Violation already processed: {violation.violation_id}")
            return None
        
        # Get vehicle owner
        owner = self.vehicle_owner_db.get_owner(violation.number_plate)
        
        if not owner:
            print(f"❌ Owner not found for vehicle: {violation.number_plate}")
            return None
        
        # Generate challan ID
        self.challan_counter += 1
        challan_id = f"CH-{self.challan_counter:08d}"
        
        # Generate description
        description = self._generate_description(violation)
        
        # Create challan record
        challan = ChallanRecord(
            challan_id=challan_id,
            violation_id=violation.violation_id,
            vehicle_id=violation.vehicle_id,
            number_plate=violation.number_plate,
            owner_id=owner.owner_id,
            owner_name=owner.name,
            violation_type=violation.violation_type.value,
            violation_description=description,
            violation_timestamp=violation.timestamp,
            issued_at=time.time(),
            fine_amount=violation.fine_amount,
            status=ChallanStatus.ISSUED,
            location=violation.junction_id or violation.road_id or "UNKNOWN",
            location_name=violation.location_name,
            lat=violation.lat,
            lon=violation.lon,
            evidence=violation.evidence
        )
        
        # Store in memory
        self.challans.append(challan)
        self.total_challans += 1
        self.pending_revenue += challan.fine_amount
        self._processed_violations.add(violation.violation_id)
        
        # Save to database
        self._save_to_database(challan, violation)
        
        print(f"📄 Challan issued: {challan_id} to {owner.name} (₹{challan.fine_amount:.2f})")
        
        # Emit WebSocket notification
        if self._ws_emitter:
            self._emit_challan_event('challan:issued', challan)
        
        return challan_id
    
    def _generate_description(self, violation: ViolationEvent) -> str:
        """Generate human-readable violation description"""
        base_desc = self.VIOLATION_DESCRIPTIONS.get(
            violation.violation_type.value,
            f"{violation.violation_type.value} violation"
        )
        
        evidence = violation.evidence
        
        if violation.violation_type == ViolationType.RED_LIGHT:
            junction = evidence.get('junctionName') or evidence.get('junctionId', 'unknown junction')
            return f"{base_desc} at {junction}"
        
        elif violation.violation_type == ViolationType.SPEEDING:
            speed = evidence.get('speed', 0)
            limit = evidence.get('speedLimit', 0)
            return f"{base_desc}: {speed:.0f} km/h in {limit:.0f} km/h zone"
        
        return base_desc
    
    def _save_to_database(self, challan: ChallanRecord, violation: ViolationEvent = None):
        """Save challan to database"""
        try:
            db = SessionLocal()
            
            # Save violation first if provided
            if violation:
                existing_violation = db.query(ViolationDB).filter(
                    ViolationDB.id == violation.violation_id
                ).first()
                
                if not existing_violation:
                    db_violation = ViolationDB(
                        id=violation.violation_id,
                        vehicle_id=violation.vehicle_id,
                        number_plate=violation.number_plate,
                        violation_type=violation.violation_type.value,
                        severity=violation.severity,
                        location=violation.junction_id or violation.road_id or "UNKNOWN",
                        junction_id=violation.junction_id,
                        road_id=violation.road_id,
                        position_x=violation.location[0] if violation.location else None,
                        position_y=violation.location[1] if violation.location else None,
                        timestamp=violation.timestamp,
                        evidence_speed=violation.evidence.get('speed'),
                        evidence_speed_limit=violation.evidence.get('speedLimit'),
                        evidence_signal_state=violation.evidence.get('signalState'),
                        evidence_snapshot=json.dumps(violation.evidence),
                        processed=True,
                        challan_id=challan.challan_id
                    )
                    db.add(db_violation)
            
            # Check if challan exists
            existing = db.query(ChallanDB).filter(
                ChallanDB.challan_id == challan.challan_id
            ).first()
            
            if existing:
                # Update existing
                existing.status = challan.status.value
                existing.payment_timestamp = challan.paid_at
                existing.transaction_id = challan.transaction_id
            else:
                # Create new
                db_challan = ChallanDB(
                    challan_id=challan.challan_id,
                    violation_id=challan.violation_id,
                    number_plate=challan.number_plate,
                    owner_name=challan.owner_name,
                    violation_type=challan.violation_type,
                    violation_description=challan.violation_description,
                    fine_amount=challan.fine_amount,
                    location=challan.location,
                    violation_timestamp=challan.violation_timestamp,
                    status=challan.status.value,
                    payment_timestamp=challan.paid_at,
                    transaction_id=challan.transaction_id
                )
                db.add(db_challan)
            
            db.commit()
            db.close()
        except Exception as e:
            print(f"⚠️ Could not save challan to database: {e}")
    
    def process_auto_payment(self, challan_id: str) -> tuple[bool, Optional[str]]:
        """
        Process automatic payment (fine deduction)
        
        Args:
            challan_id: Challan ID
        
        Returns:
            (success, error_message)
        """
        challan = self._get_challan(challan_id)
        
        if not challan:
            return False, "Challan not found"
        
        if challan.status == ChallanStatus.PAID:
            return True, None  # Already paid
        
        # Attempt to deduct fine from wallet
        success, error = self.vehicle_owner_db.deduct_fine(
            number_plate=challan.number_plate,
            amount=challan.fine_amount
        )
        
        if success:
            # Update challan status
            challan.status = ChallanStatus.PAID
            challan.paid_at = time.time()
            challan.transaction_id = f"TXN-{int(time.time())}"
            
            # Update revenue
            self.total_revenue += challan.fine_amount
            self.pending_revenue -= challan.fine_amount
            
            # Save transaction
            self._save_transaction(challan)
            
            # Update database
            self._save_to_database(challan)
            
            print(f"✅ Challan paid: {challan_id}")
            
            # Emit WebSocket notification
            if self._ws_emitter:
                self._emit_challan_event('challan:paid', challan)
            
            return True, None
        else:
            # Mark as pending (insufficient balance)
            challan.status = ChallanStatus.PENDING
            self._save_to_database(challan)
            
            print(f"⚠️ Payment failed: {challan_id} ({error})")
            return False, error
    
    def _save_transaction(self, challan: ChallanRecord):
        """Save payment transaction to database"""
        try:
            db = SessionLocal()
            
            owner = self.vehicle_owner_db.get_owner(challan.number_plate)
            if owner:
                transaction = TransactionDB(
                    transaction_id=challan.transaction_id,
                    challan_id=challan.challan_id,
                    number_plate=challan.number_plate,
                    amount=challan.fine_amount,
                    previous_balance=owner.wallet_balance + challan.fine_amount,
                    new_balance=owner.wallet_balance,
                    timestamp=challan.paid_at,
                    status="SUCCESS"
                )
                db.add(transaction)
                db.commit()
            
            db.close()
        except Exception as e:
            print(f"⚠️ Could not save transaction: {e}")
    
    def _emit_challan_event(self, event: str, challan: ChallanRecord):
        """Emit WebSocket event for challan"""
        try:
            import asyncio
            asyncio.create_task(
                self._ws_emitter.emit(event, {
                    'challanId': challan.challan_id,
                    'violationId': challan.violation_id,
                    'vehicleId': challan.vehicle_id,
                    'numberPlate': challan.number_plate,
                    'ownerName': challan.owner_name,
                    'violationType': challan.violation_type,
                    'fineAmount': challan.fine_amount,
                    'status': challan.status.value,
                    'location': challan.location,
                    'issuedAt': challan.issued_at,
                    'paidAt': challan.paid_at,
                    'transactionId': challan.transaction_id
                })
            )
        except Exception as e:
            print(f"⚠️ Failed to emit challan event: {e}")
    
    def get_challan(self, challan_id: str) -> Optional[ChallanRecord]:
        """Get challan by ID"""
        return self._get_challan(challan_id)
    
    def _get_challan(self, challan_id: str) -> Optional[ChallanRecord]:
        """Internal: Get challan by ID"""
        for challan in self.challans:
            if challan.challan_id == challan_id:
                return challan
        return None
    
    def get_vehicle_challans(self, number_plate: str) -> List[ChallanRecord]:
        """Get all challans for a vehicle"""
        return [c for c in self.challans if c.number_plate == number_plate]
    
    def get_pending_challans(self) -> List[ChallanRecord]:
        """Get all pending/unpaid challans"""
        return [
            c for c in self.challans 
            if c.status in (ChallanStatus.ISSUED, ChallanStatus.PENDING)
        ]
    
    def get_recent_challans(self, limit: int = 50) -> List[ChallanRecord]:
        """Get recent challans"""
        return sorted(
            self.challans,
            key=lambda c: c.issued_at,
            reverse=True
        )[:limit]
    
    def get_statistics(self) -> dict:
        """Get challan statistics"""
        paid = len([c for c in self.challans if c.status == ChallanStatus.PAID])
        pending = len([c for c in self.challans if c.status in (ChallanStatus.ISSUED, ChallanStatus.PENDING)])
        
        # By violation type
        by_type: Dict[str, int] = {}
        for c in self.challans:
            by_type[c.violation_type] = by_type.get(c.violation_type, 0) + 1
        
        # Revenue by type
        revenue_by_type: Dict[str, float] = {}
        for c in self.challans:
            if c.status == ChallanStatus.PAID:
                revenue_by_type[c.violation_type] = revenue_by_type.get(c.violation_type, 0) + c.fine_amount
        
        return {
            'totalChallans': self.total_challans,
            'totalRevenue': self.total_revenue,
            'pendingRevenue': self.pending_revenue,
            'paidCount': paid,
            'pendingCount': pending,
            'paymentRate': (paid / self.total_challans * 100) if self.total_challans > 0 else 0,
            'byViolationType': by_type,
            'revenueByType': revenue_by_type
        }
    
    def cancel_challan(self, challan_id: str, reason: str = "Cancelled") -> bool:
        """Cancel a challan (admin action)"""
        challan = self._get_challan(challan_id)
        
        if not challan:
            return False
        
        if challan.status == ChallanStatus.PAID:
            return False  # Cannot cancel paid challan
        
        # Update pending revenue
        self.pending_revenue -= challan.fine_amount
        
        challan.status = ChallanStatus.CANCELLED
        self._save_to_database(challan)
        
        print(f"❌ Challan cancelled: {challan_id} ({reason})")
        
        return True


# Global instance
_challan_manager: Optional[ChallanManager] = None


def init_challan_manager(vehicle_owner_db: VehicleOwnerDatabase) -> ChallanManager:
    """Initialize global challan manager"""
    global _challan_manager
    _challan_manager = ChallanManager(vehicle_owner_db)
    return _challan_manager


def get_challan_manager() -> Optional[ChallanManager]:
    """Get global challan manager instance"""
    return _challan_manager

