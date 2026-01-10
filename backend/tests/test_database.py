"""
Database Tests

Tests for SQLite database, ORM models, and CRUD operations.
Covers FRD-01 Section 2.5 requirements.
"""

import pytest
import time
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.database import Base, get_db
from app.database.models import (
    DetectionRecord,
    VehicleOwner,
    Violation,
    Challan,
    ChallanTransaction,
    AgentLog,
    SystemEvent,
    MapCache,
    APICache,
    TrafficHistory,
)


# Test database setup
TEST_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(name="db")
def db_fixture():
    """Create tables and provide test database session"""
    Base.metadata.create_all(bind=test_engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=test_engine)


# ============================================
# Detection Records Tests
# ============================================

class TestDetectionRecords:
    """Test DetectionRecord model (FRD-08)"""
    
    def test_create_detection_record(self, db):
        """Test creating a detection record"""
        record = DetectionRecord(
            id="det-001",
            vehicle_id="v-123",
            number_plate="GJ18AB1234",
            junction_id="J-5",
            timestamp=time.time(),
            direction="N",
            incoming_road="R-1",
            outgoing_road="R-2",
            speed=35.0,
            violation_detected=False
        )
        db.add(record)
        db.commit()
        
        retrieved = db.query(DetectionRecord).filter_by(id="det-001").first()
        assert retrieved is not None
        assert retrieved.number_plate == "GJ18AB1234"
        assert retrieved.junction_id == "J-5"
        assert retrieved.violation_detected is False
    
    def test_query_by_number_plate(self, db):
        """Test querying detections by number plate"""
        # Create multiple records
        for i in range(5):
            record = DetectionRecord(
                id=f"det-{i}",
                vehicle_id=f"v-{i}",
                number_plate="GJ18AB1234",
                junction_id=f"J-{i}",
                timestamp=time.time() + i,
                direction="N"
            )
            db.add(record)
        db.commit()
        
        records = db.query(DetectionRecord)\
            .filter_by(number_plate="GJ18AB1234")\
            .order_by(DetectionRecord.timestamp.desc())\
            .all()
        
        assert len(records) == 5
        # Should be ordered newest first
        assert records[0].timestamp > records[4].timestamp
    
    def test_query_by_junction_and_time(self, db):
        """Test querying detections by junction and time range"""
        base_time = time.time()
        
        for i in range(10):
            record = DetectionRecord(
                id=f"det-time-{i}",
                vehicle_id=f"v-{i}",
                number_plate=f"GJ18TEST{i}",
                junction_id="J-5",
                timestamp=base_time + (i * 60),  # 1 minute apart
                direction="N"
            )
            db.add(record)
        db.commit()
        
        # Query for records in the middle 5 minutes
        # i=2 -> 120s, i=3 -> 180s, i=4 -> 240s, i=5 -> 300s, i=6 -> 360s
        # That's 5 records at 120, 180, 240, 300, 360
        start_time = base_time + 120
        end_time = base_time + 360  # Inclusive will get 5 records
        
        records = db.query(DetectionRecord)\
            .filter(DetectionRecord.junction_id == "J-5")\
            .filter(DetectionRecord.timestamp >= start_time)\
            .filter(DetectionRecord.timestamp <= end_time)\
            .all()
        
        assert len(records) == 5


# ============================================
# Vehicle Owner Tests
# ============================================

class TestVehicleOwner:
    """Test VehicleOwner model (FRD-09)"""
    
    def test_create_vehicle_owner(self, db):
        """Test creating a vehicle owner"""
        owner = VehicleOwner(
            number_plate="GJ18AB1234",
            owner_name="John Doe",
            contact="9876543210",
            email="john@example.com",
            address="123 Main St, Gandhinagar",
            wallet_balance=5000.0
        )
        db.add(owner)
        db.commit()
        
        retrieved = db.query(VehicleOwner).filter_by(number_plate="GJ18AB1234").first()
        assert retrieved is not None
        assert retrieved.owner_name == "John Doe"
        assert retrieved.wallet_balance == 5000.0
        assert retrieved.total_challans == 0
    
    def test_update_wallet_balance(self, db):
        """Test updating owner's wallet balance"""
        owner = VehicleOwner(
            number_plate="GJ18TEST001",
            owner_name="Test User",
            contact="1234567890",
            wallet_balance=1000.0
        )
        db.add(owner)
        db.commit()
        
        # Deduct fine
        owner.wallet_balance -= 500.0
        owner.total_challans += 1
        owner.total_fines_paid += 500.0
        db.commit()
        
        retrieved = db.query(VehicleOwner).filter_by(number_plate="GJ18TEST001").first()
        assert retrieved.wallet_balance == 500.0
        assert retrieved.total_challans == 1
        assert retrieved.total_fines_paid == 500.0


# ============================================
# Violation Tests
# ============================================

class TestViolations:
    """Test Violation model (FRD-09)"""
    
    def test_create_violation(self, db):
        """Test creating a traffic violation"""
        violation = Violation(
            id="vio-001",
            vehicle_id="v-123",
            number_plate="GJ18AB1234",
            violation_type="RED_LIGHT",
            severity="HIGH",
            location="J-5",
            timestamp=time.time(),
            evidence_signal_state="RED",
            processed=False
        )
        db.add(violation)
        db.commit()
        
        retrieved = db.query(Violation).filter_by(id="vio-001").first()
        assert retrieved is not None
        assert retrieved.violation_type == "RED_LIGHT"
        assert retrieved.severity == "HIGH"
        assert retrieved.processed is False
    
    def test_query_unprocessed_violations(self, db):
        """Test querying unprocessed violations"""
        # Create mix of processed and unprocessed
        for i in range(5):
            violation = Violation(
                id=f"vio-proc-{i}",
                vehicle_id=f"v-{i}",
                number_plate=f"GJ18TEST{i}",
                violation_type="SPEEDING",
                severity="MEDIUM",
                location="R-1",
                timestamp=time.time(),
                processed=(i < 3)  # First 3 are processed
            )
            db.add(violation)
        db.commit()
        
        unprocessed = db.query(Violation).filter_by(processed=False).all()
        assert len(unprocessed) == 2


# ============================================
# Challan Tests
# ============================================

class TestChallans:
    """Test Challan model (FRD-09)"""
    
    def test_create_challan(self, db):
        """Test creating a challan"""
        # First create owner
        owner = VehicleOwner(
            number_plate="GJ18AB1234",
            owner_name="John Doe",
            contact="9876543210"
        )
        db.add(owner)
        
        # Create violation
        violation = Violation(
            id="vio-ch-001",
            vehicle_id="v-123",
            number_plate="GJ18AB1234",
            violation_type="RED_LIGHT",
            severity="HIGH",
            location="J-5",
            timestamp=time.time()
        )
        db.add(violation)
        db.commit()
        
        # Create challan
        challan = Challan(
            challan_id="CH-001",
            violation_id="vio-ch-001",
            number_plate="GJ18AB1234",
            owner_name="John Doe",
            violation_type="RED_LIGHT",
            violation_description="Ran red light at Junction J-5",
            fine_amount=1000.0,
            location="J-5",
            violation_timestamp=time.time(),
            status="ISSUED"
        )
        db.add(challan)
        db.commit()
        
        retrieved = db.query(Challan).filter_by(challan_id="CH-001").first()
        assert retrieved is not None
        assert retrieved.fine_amount == 1000.0
        assert retrieved.status == "ISSUED"
    
    def test_challan_payment(self, db):
        """Test recording challan payment"""
        # Setup
        owner = VehicleOwner(
            number_plate="GJ18PAY001",
            owner_name="Payer Test",
            contact="1111111111",
            wallet_balance=5000.0
        )
        db.add(owner)
        
        violation = Violation(
            id="vio-pay-001",
            vehicle_id="v-pay",
            number_plate="GJ18PAY001",
            violation_type="SPEEDING",
            severity="MEDIUM",
            location="R-5",
            timestamp=time.time()
        )
        db.add(violation)
        
        challan = Challan(
            challan_id="CH-PAY-001",
            violation_id="vio-pay-001",
            number_plate="GJ18PAY001",
            owner_name="Payer Test",
            violation_type="SPEEDING",
            fine_amount=500.0,
            location="R-5",
            violation_timestamp=time.time(),
            status="ISSUED"
        )
        db.add(challan)
        db.commit()
        
        # Process payment
        challan.status = "PAID"
        challan.payment_timestamp = time.time()
        challan.transaction_id = "TXN-001"
        
        owner.wallet_balance -= 500.0
        owner.total_challans += 1
        owner.total_fines_paid += 500.0
        
        # Create transaction record
        transaction = ChallanTransaction(
            transaction_id="TXN-001",
            challan_id="CH-PAY-001",
            number_plate="GJ18PAY001",
            amount=500.0,
            previous_balance=5000.0,
            new_balance=4500.0,
            timestamp=time.time(),
            status="SUCCESS"
        )
        db.add(transaction)
        db.commit()
        
        # Verify
        updated_challan = db.query(Challan).filter_by(challan_id="CH-PAY-001").first()
        assert updated_challan.status == "PAID"
        assert updated_challan.transaction_id == "TXN-001"
        
        updated_owner = db.query(VehicleOwner).filter_by(number_plate="GJ18PAY001").first()
        assert updated_owner.wallet_balance == 4500.0


# ============================================
# Agent Log Tests
# ============================================

class TestAgentLogs:
    """Test AgentLog model (FRD-03)"""
    
    def test_create_agent_log(self, db):
        """Test creating an agent decision log"""
        log = AgentLog(
            timestamp=time.time(),
            mode="NORMAL",
            strategy="RL",
            decision_latency=15.5,
            decisions_json='[{"junction": "J-5", "action": "switch_green"}]',
            state_summary_json='{"vehicle_count": 45, "avg_density": 0.6}'
        )
        db.add(log)
        db.commit()
        
        retrieved = db.query(AgentLog).first()
        assert retrieved is not None
        assert retrieved.mode == "NORMAL"
        assert retrieved.strategy == "RL"
        assert retrieved.decision_latency == 15.5
    
    def test_query_agent_logs_pagination(self, db):
        """Test paginated agent log queries"""
        # Create 20 logs
        for i in range(20):
            log = AgentLog(
                timestamp=time.time() + i,
                mode="NORMAL",
                strategy="RL",
                decision_latency=10.0 + i
            )
            db.add(log)
        db.commit()
        
        # Get page 1 (10 records)
        page1 = db.query(AgentLog)\
            .order_by(AgentLog.timestamp.desc())\
            .limit(10)\
            .offset(0)\
            .all()
        
        # Get page 2
        page2 = db.query(AgentLog)\
            .order_by(AgentLog.timestamp.desc())\
            .limit(10)\
            .offset(10)\
            .all()
        
        assert len(page1) == 10
        assert len(page2) == 10
        assert page1[0].timestamp > page2[0].timestamp


# ============================================
# System Event Tests
# ============================================

class TestSystemEvents:
    """Test SystemEvent model (FRD-05)"""
    
    def test_create_system_event(self, db):
        """Test creating a system event"""
        event = SystemEvent(
            timestamp=time.time(),
            event_type="MODE_CHANGE",
            severity="INFO",
            message="System mode changed from NORMAL to EMERGENCY",
            metadata_json='{"old_mode": "NORMAL", "new_mode": "EMERGENCY"}'
        )
        db.add(event)
        db.commit()
        
        retrieved = db.query(SystemEvent).first()
        assert retrieved is not None
        assert retrieved.event_type == "MODE_CHANGE"
        assert retrieved.severity == "INFO"
    
    def test_query_events_by_type(self, db):
        """Test querying events by type"""
        event_types = ["MODE_CHANGE", "ERROR", "ALERT", "MODE_CHANGE", "ERROR"]
        
        for i, event_type in enumerate(event_types):
            event = SystemEvent(
                timestamp=time.time() + i,
                event_type=event_type,
                severity="INFO",
                message=f"Event {i}"
            )
            db.add(event)
        db.commit()
        
        mode_changes = db.query(SystemEvent).filter_by(event_type="MODE_CHANGE").all()
        errors = db.query(SystemEvent).filter_by(event_type="ERROR").all()
        
        assert len(mode_changes) == 2
        assert len(errors) == 2


# ============================================
# Map Cache Tests (FRD-01 v2.0)
# ============================================

class TestMapCache:
    """Test MapCache model"""
    
    def test_create_map_cache(self, db):
        """Test creating a map cache entry"""
        cache = MapCache(
            area_id="gift_city",
            area_name="GIFT City",
            bounds_json='{"north": 23.2, "south": 23.1, "east": 72.7, "west": 72.6}',
            map_data_json='{"junctions": [], "roads": []}',
            junction_count=25,
            road_count=40
        )
        db.add(cache)
        db.commit()
        
        retrieved = db.query(MapCache).filter_by(area_id="gift_city").first()
        assert retrieved is not None
        assert retrieved.area_name == "GIFT City"
        assert retrieved.junction_count == 25


# ============================================
# API Cache Tests (FRD-01 v2.0)
# ============================================

class TestAPICache:
    """Test APICache model for TomTom/Google API caching"""
    
    def test_create_api_cache(self, db):
        """Test creating an API cache entry"""
        cache = APICache(
            cache_key="tomtom_road_R-1-2",
            response_data='{"current_speed": 35, "congestion": "MEDIUM"}',
            expires_at=time.time() + 60  # Expires in 1 minute
        )
        db.add(cache)
        db.commit()
        
        retrieved = db.query(APICache).filter_by(cache_key="tomtom_road_R-1-2").first()
        assert retrieved is not None
        assert retrieved.expires_at > time.time()
    
    def test_query_expired_cache(self, db):
        """Test querying expired cache entries"""
        now = time.time()
        
        # Create expired and valid entries
        expired = APICache(
            cache_key="expired_key",
            response_data='{}',
            expires_at=now - 60  # Expired 1 minute ago
        )
        valid = APICache(
            cache_key="valid_key",
            response_data='{}',
            expires_at=now + 60  # Expires in 1 minute
        )
        db.add_all([expired, valid])
        db.commit()
        
        # Query expired entries
        expired_entries = db.query(APICache)\
            .filter(APICache.expires_at < now)\
            .all()
        
        assert len(expired_entries) == 1
        assert expired_entries[0].cache_key == "expired_key"


# ============================================
# Traffic History Tests (FRD-01 v2.0)
# ============================================

class TestTrafficHistory:
    """Test TrafficHistory model"""
    
    def test_create_traffic_history(self, db):
        """Test creating traffic history record"""
        history = TrafficHistory(
            road_id="R-1-2",
            congestion_level="HIGH",
            current_speed=15.0,
            vehicle_count=25,
            density_score=75.0,
            timestamp=time.time(),
            source="API"
        )
        db.add(history)
        db.commit()
        
        retrieved = db.query(TrafficHistory).first()
        assert retrieved is not None
        assert retrieved.congestion_level == "HIGH"
    
    def test_query_road_history(self, db):
        """Test querying traffic history for a road"""
        base_time = time.time()
        
        # Create history records
        for i in range(24):  # 24 hours of data
            history = TrafficHistory(
                road_id="R-1-2",
                congestion_level=["LOW", "MEDIUM", "HIGH"][i % 3],
                current_speed=30 + (i * 2),
                timestamp=base_time + (i * 3600),  # 1 hour apart
                source="API"
            )
            db.add(history)
        db.commit()
        
        # Query last 6 hours
        since_time = base_time + (18 * 3600)
        recent = db.query(TrafficHistory)\
            .filter(TrafficHistory.road_id == "R-1-2")\
            .filter(TrafficHistory.timestamp >= since_time)\
            .order_by(TrafficHistory.timestamp.desc())\
            .all()
        
        assert len(recent) == 6


# ============================================
# Integration Tests
# ============================================

class TestDatabaseIntegration:
    """Integration tests for complete flows"""
    
    def test_complete_violation_flow(self, db):
        """Test complete flow: Detection → Violation → Challan → Payment"""
        # 1. Create vehicle owner
        owner = VehicleOwner(
            number_plate="GJ18FLOW01",
            owner_name="Flow Test",
            contact="9999999999",
            wallet_balance=2000.0
        )
        db.add(owner)
        
        # 2. Create detection records (vehicle approaching and passing junction)
        detections = [
            DetectionRecord(
                id="det-flow-1",
                vehicle_id="v-flow",
                number_plate="GJ18FLOW01",
                junction_id="J-5",
                timestamp=time.time(),
                direction="N",
                speed=60.0  # Speeding
            ),
            DetectionRecord(
                id="det-flow-2",
                vehicle_id="v-flow",
                number_plate="GJ18FLOW01",
                junction_id="J-5",
                timestamp=time.time() + 2,
                direction="N",
                speed=65.0,
                violation_detected=True
            )
        ]
        db.add_all(detections)
        
        # 3. Create violation
        violation = Violation(
            id="vio-flow-01",
            vehicle_id="v-flow",
            number_plate="GJ18FLOW01",
            violation_type="RED_LIGHT",
            severity="HIGH",
            location="J-5",
            timestamp=time.time(),
            evidence_signal_state="RED",
            processed=False
        )
        db.add(violation)
        db.commit()
        
        # 4. Process violation - create challan
        violation.processed = True
        challan = Challan(
            challan_id="CH-FLOW-01",
            violation_id="vio-flow-01",
            number_plate="GJ18FLOW01",
            owner_name="Flow Test",
            violation_type="RED_LIGHT",
            violation_description="Red light violation at J-5",
            fine_amount=1000.0,
            location="J-5",
            violation_timestamp=violation.timestamp,
            status="ISSUED"
        )
        violation.challan_id = challan.challan_id
        db.add(challan)
        db.commit()
        
        # 5. Process payment
        challan.status = "PAID"
        challan.payment_timestamp = time.time()
        challan.transaction_id = "TXN-FLOW-01"
        
        owner.wallet_balance -= 1000.0
        owner.total_challans += 1
        owner.total_fines_paid += 1000.0
        
        transaction = ChallanTransaction(
            transaction_id="TXN-FLOW-01",
            challan_id="CH-FLOW-01",
            number_plate="GJ18FLOW01",
            amount=1000.0,
            previous_balance=2000.0,
            new_balance=1000.0,
            timestamp=time.time(),
            status="SUCCESS"
        )
        db.add(transaction)
        
        # Log the event
        event = SystemEvent(
            timestamp=time.time(),
            event_type="CHALLAN_PAID",
            severity="INFO",
            message=f"Challan CH-FLOW-01 paid by GJ18FLOW01",
            metadata_json='{"challan_id": "CH-FLOW-01", "amount": 1000.0}'
        )
        db.add(event)
        db.commit()
        
        # Verify complete flow
        final_owner = db.query(VehicleOwner).filter_by(number_plate="GJ18FLOW01").first()
        final_challan = db.query(Challan).filter_by(challan_id="CH-FLOW-01").first()
        final_violation = db.query(Violation).filter_by(id="vio-flow-01").first()
        
        assert final_owner.wallet_balance == 1000.0
        assert final_owner.total_challans == 1
        assert final_challan.status == "PAID"
        assert final_violation.processed is True
        assert final_violation.challan_id == "CH-FLOW-01"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

