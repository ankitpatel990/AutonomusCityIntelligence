"""
Challan Routes - Auto-challan and violation enforcement endpoints (FRD-09)

Endpoints:
- GET /api/violations - Get all violations
- GET /api/violations/recent - Get recent violations
- GET /api/challans - Get all challans
- GET /api/challans/{id} - Get specific challan
- GET /api/challans/stats - Get challan statistics
- POST /api/challans/pay/{id} - Pay a challan
- GET /api/owners - Get vehicle owners
- GET /api/owners/{numberPlate} - Get owner by plate
- GET /api/revenue/stats - Get revenue statistics
- GET /api/challan/service/stats - Get auto-challan service stats
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from typing import Optional, List, Dict, Any, Literal
import time

from app.database.database import get_db
from app.database.models import Violation, Challan, VehicleOwner, ChallanTransaction

router = APIRouter(tags=["challan"])

# Global instances (set by main.py)
_violation_detector = None
_vehicle_owner_db = None
_challan_manager = None
_auto_challan_service = None


def set_challan_components(
    violation_detector=None,
    vehicle_owner_db=None,
    challan_manager=None,
    auto_challan_service=None
):
    """Set global challan system components"""
    global _violation_detector, _vehicle_owner_db, _challan_manager, _auto_challan_service
    _violation_detector = violation_detector
    _vehicle_owner_db = vehicle_owner_db
    _challan_manager = challan_manager
    _auto_challan_service = auto_challan_service


# ============================================
# Response Models
# ============================================

class ViolationResponse(BaseModel):
    """Traffic violation response"""
    id: str
    vehicleId: str
    numberPlate: str
    violationType: str
    severity: str
    location: str
    timestamp: float
    processed: bool
    challanId: Optional[str]


class ChallanResponse(BaseModel):
    """Challan response"""
    challanId: str
    violationId: str
    numberPlate: str
    ownerName: str
    violationType: str
    violationDescription: Optional[str]
    fineAmount: float
    location: str
    timestamp: float
    status: str
    paymentTimestamp: Optional[float]


class ChallanStatsResponse(BaseModel):
    """Challan statistics"""
    totalViolations: int
    totalChallans: int
    totalRevenue: float
    pendingRevenue: float
    violationsByType: Dict[str, int]
    complianceRate: float
    topViolators: List[Dict[str, Any]]


class OwnerResponse(BaseModel):
    """Vehicle owner response"""
    numberPlate: str
    ownerName: str
    contact: str
    walletBalance: float
    totalChallans: int
    totalFinesPaid: float


class PaymentResponse(BaseModel):
    """Payment response"""
    status: str
    challanId: str
    transactionId: str
    amount: float
    previousBalance: float
    newBalance: float
    timestamp: float


class RevenueStatsResponse(BaseModel):
    """Revenue statistics"""
    totalRevenue: float
    revenueToday: float
    revenuePending: float
    revenueByType: Dict[str, float]
    revenueTimeseries: List[Dict[str, Any]]


# ============================================
# Violation Endpoints
# ============================================

@router.get("/api/violations", response_model=List[ViolationResponse])
async def get_violations(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    type: Optional[str] = Query(None, description="Filter by violation type"),
    processed: Optional[bool] = Query(None, description="Filter by processed status"),
    db: Session = Depends(get_db)
):
    """
    Get all violations
    
    Returns paginated list of traffic violations.
    Can filter by type (RED_LIGHT, SPEEDING, WRONG_LANE) and processed status.
    
    Response time target: < 200ms
    """
    query = db.query(Violation)
    
    if type:
        query = query.filter(Violation.violation_type == type)
    if processed is not None:
        query = query.filter(Violation.processed == processed)
    
    violations = query.order_by(Violation.timestamp.desc())\
        .limit(limit)\
        .offset(offset)\
        .all()
    
    return [
        ViolationResponse(
            id=v.id,
            vehicleId=v.vehicle_id,
            numberPlate=v.number_plate,
            violationType=v.violation_type,
            severity=v.severity,
            location=v.location,
            timestamp=v.timestamp,
            processed=v.processed,
            challanId=v.challan_id
        )
        for v in violations
    ]


@router.get("/api/violations/recent", response_model=List[ViolationResponse])
async def get_recent_violations(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Get recent violations (last 20)
    
    Quick endpoint for dashboard display.
    """
    violations = db.query(Violation)\
        .order_by(Violation.timestamp.desc())\
        .limit(limit)\
        .all()
    
    return [
        ViolationResponse(
            id=v.id,
            vehicleId=v.vehicle_id,
            numberPlate=v.number_plate,
            violationType=v.violation_type,
            severity=v.severity,
            location=v.location,
            timestamp=v.timestamp,
            processed=v.processed,
            challanId=v.challan_id
        )
        for v in violations
    ]


@router.get("/api/violations/{violation_id}")
async def get_violation(
    violation_id: str,
    db: Session = Depends(get_db)
):
    """Get specific violation by ID"""
    violation = db.query(Violation).filter(Violation.id == violation_id).first()
    
    if not violation:
        raise HTTPException(status_code=404, detail="Violation not found")
    
    return {
        "id": violation.id,
        "vehicleId": violation.vehicle_id,
        "numberPlate": violation.number_plate,
        "violationType": violation.violation_type,
        "severity": violation.severity,
        "location": violation.location,
        "junctionId": violation.junction_id,
        "roadId": violation.road_id,
        "timestamp": violation.timestamp,
        "evidenceSpeed": violation.evidence_speed,
        "evidenceSpeedLimit": violation.evidence_speed_limit,
        "evidenceSignalState": violation.evidence_signal_state,
        "processed": violation.processed,
        "challanId": violation.challan_id
    }


# ============================================
# Challan Endpoints
# ============================================

@router.get("/api/challans", response_model=List[ChallanResponse])
async def get_challans(
    status: Optional[Literal["ISSUED", "PAID", "PENDING", "CANCELLED"]] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """
    Get all challans
    
    Returns paginated list of generated challans.
    Can filter by status.
    
    Response time target: < 200ms
    """
    query = db.query(Challan)
    
    if status:
        query = query.filter(Challan.status == status)
    
    challans = query.order_by(Challan.violation_timestamp.desc())\
        .limit(limit)\
        .offset(offset)\
        .all()
    
    return [
        ChallanResponse(
            challanId=c.challan_id,
            violationId=c.violation_id,
            numberPlate=c.number_plate,
            ownerName=c.owner_name,
            violationType=c.violation_type,
            violationDescription=c.violation_description,
            fineAmount=c.fine_amount,
            location=c.location,
            timestamp=c.violation_timestamp,
            status=c.status,
            paymentTimestamp=c.payment_timestamp
        )
        for c in challans
    ]


@router.get("/api/challans/stats", response_model=ChallanStatsResponse)
async def get_challan_stats(db: Session = Depends(get_db)):
    """
    Get challan statistics
    
    Returns aggregate statistics for dashboard display.
    
    Response time target: < 200ms
    """
    total_violations = db.query(Violation).count()
    total_challans = db.query(Challan).count()
    
    # Revenue calculations
    total_revenue = db.query(func.sum(Challan.fine_amount))\
        .filter(Challan.status == "PAID").scalar() or 0.0
    
    pending_revenue = db.query(func.sum(Challan.fine_amount))\
        .filter(Challan.status == "ISSUED").scalar() or 0.0
    
    # Violations by type
    type_counts = db.query(
        Violation.violation_type,
        func.count(Violation.id)
    ).group_by(Violation.violation_type).all()
    
    violations_by_type = {t: c for t, c in type_counts}
    
    # Compliance rate
    paid_count = db.query(Challan).filter(Challan.status == "PAID").count()
    compliance_rate = (paid_count / total_challans * 100) if total_challans > 0 else 100.0
    
    # Top violators
    top_violators_query = db.query(
        Violation.number_plate,
        func.count(Violation.id).label('count')
    ).group_by(Violation.number_plate)\
     .order_by(func.count(Violation.id).desc())\
     .limit(10).all()
    
    top_violators = [
        {"numberPlate": plate, "count": count}
        for plate, count in top_violators_query
    ]
    
    return ChallanStatsResponse(
        totalViolations=total_violations,
        totalChallans=total_challans,
        totalRevenue=total_revenue,
        pendingRevenue=pending_revenue,
        violationsByType=violations_by_type,
        complianceRate=compliance_rate,
        topViolators=top_violators
    )


@router.get("/api/challans/{challan_id}", response_model=ChallanResponse)
async def get_challan(
    challan_id: str,
    db: Session = Depends(get_db)
):
    """Get specific challan by ID"""
    challan = db.query(Challan).filter(Challan.challan_id == challan_id).first()
    
    if not challan:
        raise HTTPException(status_code=404, detail="Challan not found")
    
    return ChallanResponse(
        challanId=challan.challan_id,
        violationId=challan.violation_id,
        numberPlate=challan.number_plate,
        ownerName=challan.owner_name,
        violationType=challan.violation_type,
        violationDescription=challan.violation_description,
        fineAmount=challan.fine_amount,
        location=challan.location,
        timestamp=challan.violation_timestamp,
        status=challan.status,
        paymentTimestamp=challan.payment_timestamp
    )


@router.post("/api/challans/pay/{challan_id}", response_model=PaymentResponse)
async def pay_challan(
    challan_id: str,
    db: Session = Depends(get_db)
):
    """
    Pay a challan (demo only)
    
    Deducts fine amount from owner's wallet and marks challan as paid.
    Uses mock payment gateway.
    """
    # Get challan
    challan = db.query(Challan).filter(Challan.challan_id == challan_id).first()
    if not challan:
        raise HTTPException(status_code=404, detail="Challan not found")
    
    if challan.status == "PAID":
        raise HTTPException(status_code=400, detail="Challan already paid")
    
    # Get owner
    owner = db.query(VehicleOwner).filter(
        VehicleOwner.number_plate == challan.number_plate
    ).first()
    
    if not owner:
        raise HTTPException(status_code=404, detail="Vehicle owner not found")
    
    # Check balance
    if owner.wallet_balance < challan.fine_amount:
        raise HTTPException(status_code=400, detail="Insufficient wallet balance")
    
    # Process payment
    previous_balance = owner.wallet_balance
    new_balance = previous_balance - challan.fine_amount
    
    owner.wallet_balance = new_balance
    owner.total_fines_paid += challan.fine_amount
    
    challan.status = "PAID"
    challan.payment_timestamp = time.time()
    
    # Create transaction record
    transaction_id = f"txn-{int(time.time())}"
    transaction = ChallanTransaction(
        transaction_id=transaction_id,
        challan_id=challan_id,
        number_plate=challan.number_plate,
        amount=challan.fine_amount,
        previous_balance=previous_balance,
        new_balance=new_balance,
        timestamp=time.time(),
        status="SUCCESS"
    )
    
    db.add(transaction)
    db.commit()
    
    return PaymentResponse(
        status="PAID",
        challanId=challan_id,
        transactionId=transaction_id,
        amount=challan.fine_amount,
        previousBalance=previous_balance,
        newBalance=new_balance,
        timestamp=time.time()
    )


# ============================================
# Owner Endpoints
# ============================================

@router.get("/api/owners", response_model=List[OwnerResponse])
async def get_owners(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """
    Get vehicle owner database
    
    Returns paginated list of registered vehicle owners.
    """
    owners = db.query(VehicleOwner)\
        .limit(limit)\
        .offset(offset)\
        .all()
    
    return [
        OwnerResponse(
            numberPlate=o.number_plate,
            ownerName=o.owner_name,
            contact=o.contact,
            walletBalance=o.wallet_balance,
            totalChallans=o.total_challans,
            totalFinesPaid=o.total_fines_paid
        )
        for o in owners
    ]


@router.get("/api/owners/{number_plate}", response_model=OwnerResponse)
async def get_owner(
    number_plate: str,
    db: Session = Depends(get_db)
):
    """Get owner by number plate"""
    owner = db.query(VehicleOwner).filter(
        VehicleOwner.number_plate == number_plate
    ).first()
    
    if not owner:
        raise HTTPException(status_code=404, detail="Owner not found")
    
    return OwnerResponse(
        numberPlate=owner.number_plate,
        ownerName=owner.owner_name,
        contact=owner.contact,
        walletBalance=owner.wallet_balance,
        totalChallans=owner.total_challans,
        totalFinesPaid=owner.total_fines_paid
    )


# ============================================
# Revenue Endpoints
# ============================================

@router.get("/api/revenue/stats", response_model=RevenueStatsResponse)
async def get_revenue_stats(db: Session = Depends(get_db)):
    """
    Get revenue statistics
    
    Returns aggregate revenue data for dashboard display.
    """
    # Total revenue (paid challans)
    total_revenue = db.query(func.sum(Challan.fine_amount))\
        .filter(Challan.status == "PAID").scalar() or 0.0
    
    # Today's revenue
    today_start = time.time() - (time.time() % 86400)
    revenue_today = db.query(func.sum(Challan.fine_amount))\
        .filter(Challan.status == "PAID")\
        .filter(Challan.payment_timestamp >= today_start).scalar() or 0.0
    
    # Pending revenue
    pending = db.query(func.sum(Challan.fine_amount))\
        .filter(Challan.status == "ISSUED").scalar() or 0.0
    
    # Revenue by violation type
    by_type_query = db.query(
        Challan.violation_type,
        func.sum(Challan.fine_amount)
    ).filter(Challan.status == "PAID")\
     .group_by(Challan.violation_type).all()
    
    revenue_by_type = {t: float(amt) for t, amt in by_type_query}
    
    return RevenueStatsResponse(
        totalRevenue=total_revenue,
        revenueToday=revenue_today,
        revenuePending=pending,
        revenueByType=revenue_by_type,
        revenueTimeseries=[]  # TODO: Implement timeseries
    )


# ============================================
# Auto-Challan Service Endpoints (FRD-09)
# ============================================

@router.get("/api/challan/service/stats")
async def get_service_stats():
    """
    Get auto-challan service statistics
    
    Returns real-time status and statistics of the automated
    violation detection and challan processing service.
    """
    if not _auto_challan_service:
        return {
            "status": "not_initialized",
            "message": "Auto-challan service not initialized"
        }
    
    return _auto_challan_service.get_statistics()


@router.post("/api/challan/service/start")
async def start_service():
    """Start the auto-challan service"""
    if not _auto_challan_service:
        raise HTTPException(status_code=500, detail="Auto-challan service not initialized")
    
    await _auto_challan_service.start()
    
    return {"status": "started", "message": "Auto-challan service started"}


@router.post("/api/challan/service/stop")
async def stop_service():
    """Stop the auto-challan service"""
    if not _auto_challan_service:
        raise HTTPException(status_code=500, detail="Auto-challan service not initialized")
    
    await _auto_challan_service.stop()
    
    return {"status": "stopped", "message": "Auto-challan service stopped"}


@router.post("/api/challan/service/process")
async def force_process():
    """Force process all pending violations"""
    if not _auto_challan_service:
        raise HTTPException(status_code=500, detail="Auto-challan service not initialized")
    
    _auto_challan_service.force_process_all()
    
    return {
        "status": "processed",
        "message": "All pending violations processed",
        "stats": _auto_challan_service.get_statistics()
    }


@router.get("/api/challan/violations/live")
async def get_live_violations():
    """
    Get live violations from in-memory detector
    
    Returns recent violations detected during current simulation.
    """
    if not _violation_detector:
        return {"violations": [], "stats": {}}
    
    violations = _violation_detector.get_recent_violations(100)
    
    return {
        "violations": [
            {
                "violationId": v.violation_id,
                "vehicleId": v.vehicle_id,
                "numberPlate": v.number_plate,
                "type": v.violation_type.value,
                "severity": v.severity,
                "location": v.location,
                "junctionId": v.junction_id,
                "fineAmount": v.fine_amount,
                "timestamp": v.timestamp,
                "evidence": v.evidence
            }
            for v in violations
        ],
        "stats": _violation_detector.get_statistics()
    }


@router.get("/api/challan/challans/live")
async def get_live_challans():
    """
    Get live challans from in-memory manager
    
    Returns recent challans generated during current simulation.
    """
    if not _challan_manager:
        return {"challans": [], "stats": {}}
    
    challans = _challan_manager.get_recent_challans(100)
    
    return {
        "challans": [
            {
                "challanId": c.challan_id,
                "violationId": c.violation_id,
                "numberPlate": c.number_plate,
                "ownerName": c.owner_name,
                "violationType": c.violation_type,
                "fineAmount": c.fine_amount,
                "status": c.status.value,
                "location": c.location,
                "issuedAt": c.issued_at,
                "paidAt": c.paid_at
            }
            for c in challans
        ],
        "stats": _challan_manager.get_statistics()
    }


@router.post("/api/owners/{number_plate}/add-balance")
async def add_owner_balance(
    number_plate: str,
    amount: float = Query(1000, ge=100, le=50000),
    db: Session = Depends(get_db)
):
    """
    Add balance to owner's wallet (demo only)
    
    Allows adding funds to test payment processing.
    """
    if _vehicle_owner_db:
        success = _vehicle_owner_db.add_balance(number_plate, amount)
        if success:
            owner = _vehicle_owner_db.get_owner(number_plate)
            return {
                "status": "success",
                "numberPlate": number_plate,
                "addedAmount": amount,
                "newBalance": owner.wallet_balance if owner else 0
            }
    
    # Fallback to database
    owner = db.query(VehicleOwner).filter(
        VehicleOwner.number_plate == number_plate
    ).first()
    
    if not owner:
        raise HTTPException(status_code=404, detail="Owner not found")
    
    owner.wallet_balance += amount
    db.commit()
    
    return {
        "status": "success",
        "numberPlate": number_plate,
        "addedAmount": amount,
        "newBalance": owner.wallet_balance
    }

