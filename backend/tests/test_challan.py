"""
Tests for Auto-Challan System (FRD-09)

Tests violation detection, challan generation, payment processing,
and the complete auto-challan workflow.
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, MagicMock, AsyncMock

# Import challan system components
from app.challan.violation_detector import (
    ViolationDetector,
    ViolationType,
    ViolationEvent,
)
from app.challan.vehicle_owner_db import (
    VehicleOwnerDatabase,
    VehicleOwnerRecord,
)
from app.challan.challan_manager import (
    ChallanManager,
    ChallanStatus,
    ChallanRecord,
)
from app.challan.auto_challan_service import AutoChallanService

# Import models
from app.models import (
    Vehicle,
    Position,
    Junction,
    JunctionSignals,
    SignalState,
    SignalColor,
    ConnectedRoads,
    create_default_signals,
)


# ============================================
# Fixtures
# ============================================

@pytest.fixture
def violation_detector():
    """Create a fresh ViolationDetector instance"""
    return ViolationDetector()


@pytest.fixture
def vehicle_owner_db():
    """Create a fresh VehicleOwnerDatabase instance"""
    return VehicleOwnerDatabase(config={
        'minBalance': 5000,
        'maxBalance': 50000
    })


@pytest.fixture
def challan_manager(vehicle_owner_db):
    """Create a ChallanManager with mocked vehicle owner db"""
    return ChallanManager(vehicle_owner_db)


@pytest.fixture
def auto_challan_service(violation_detector, challan_manager):
    """Create an AutoChallanService instance"""
    return AutoChallanService(
        violation_detector=violation_detector,
        challan_manager=challan_manager,
        config={'processingInterval': 1, 'autoPayment': {'enabled': True}}
    )


@pytest.fixture
def test_vehicle():
    """Create a test vehicle"""
    return Vehicle(
        id="v-test-001",
        number_plate="GJ18AB1234",
        type="car",
        position=Position(x=200, y=200),
        speed=35.0,
        heading=90.0,
        destination="J-9"
    )


@pytest.fixture
def test_junction():
    """Create a test junction with signals"""
    signals = JunctionSignals(
        north=SignalState(
            current=SignalColor.RED,
            duration=30.0,
            last_change=time.time()
        ),
        east=SignalState(
            current=SignalColor.GREEN,
            duration=30.0,
            last_change=time.time()
        ),
        south=SignalState(
            current=SignalColor.RED,
            duration=30.0,
            last_change=time.time()
        ),
        west=SignalState(
            current=SignalColor.RED,
            duration=30.0,
            last_change=time.time()
        )
    )
    
    return Junction(
        id="J-5",
        position=Position(x=200, y=200),
        signals=signals,
        connected_roads=ConnectedRoads(),
        name="Test Junction"
    )


# ============================================
# ViolationDetector Tests
# ============================================

class TestViolationDetector:
    """Tests for ViolationDetector"""
    
    def test_initialization(self, violation_detector):
        """Test detector initializes correctly"""
        assert violation_detector is not None
        assert violation_detector.violations == []
        assert violation_detector.total_violations == 0
    
    def test_red_light_violation_detected(self, violation_detector, test_vehicle, test_junction):
        """Test red light violation is detected"""
        # Vehicle heading east (90 degrees) should see EAST signal
        # But EAST is GREEN, so let's modify to detect NORTH (RED)
        test_vehicle.heading = 0  # Heading North
        test_vehicle.speed = 20.0  # Moving
        
        # Position at junction
        test_vehicle.position.x = test_junction.position.x
        test_vehicle.position.y = test_junction.position.y
        
        violations = violation_detector.check_violations(
            vehicles=[test_vehicle],
            junctions=[test_junction]
        )
        
        # Should detect red light violation
        assert len(violations) == 1
        assert violations[0].violation_type == ViolationType.RED_LIGHT
        assert violations[0].number_plate == test_vehicle.number_plate
    
    def test_no_violation_on_green(self, violation_detector, test_vehicle, test_junction):
        """Test no violation when signal is green"""
        # Vehicle heading east sees GREEN signal
        test_vehicle.heading = 90  # Heading East
        test_vehicle.speed = 20.0
        test_vehicle.position.x = test_junction.position.x
        test_vehicle.position.y = test_junction.position.y
        
        violations = violation_detector.check_violations(
            vehicles=[test_vehicle],
            junctions=[test_junction]
        )
        
        # Should NOT detect violation
        assert len(violations) == 0
    
    def test_speeding_violation(self, violation_detector, test_vehicle, test_junction):
        """Test speeding violation is detected"""
        # Vehicle going too fast
        test_vehicle.speed = 80.0  # Well over limit
        test_vehicle.heading = 90  # East (GREEN signal)
        test_vehicle.position.x = 500  # Away from junction
        test_vehicle.position.y = 500
        
        violations = violation_detector.check_violations(
            vehicles=[test_vehicle],
            junctions=[test_junction]
        )
        
        # Should detect speeding
        assert len(violations) == 1
        assert violations[0].violation_type == ViolationType.SPEEDING
    
    def test_no_duplicate_violations(self, violation_detector, test_vehicle, test_junction):
        """Test that duplicate violations are not recorded"""
        test_vehicle.heading = 0  # North (RED)
        test_vehicle.speed = 20.0
        test_vehicle.position.x = test_junction.position.x
        test_vehicle.position.y = test_junction.position.y
        
        # First check
        violations1 = violation_detector.check_violations(
            vehicles=[test_vehicle],
            junctions=[test_junction]
        )
        
        # Second check immediately
        violations2 = violation_detector.check_violations(
            vehicles=[test_vehicle],
            junctions=[test_junction]
        )
        
        assert len(violations1) == 1
        assert len(violations2) == 0  # No duplicate
    
    def test_emergency_vehicles_exempt(self, violation_detector, test_junction):
        """Test that emergency vehicles are not cited"""
        ambulance = Vehicle(
            id="v-ambulance-001",
            number_plate="GJ01EMER001",
            type="ambulance",
            position=Position(x=200, y=200),
            speed=50.0,
            heading=0,  # North (RED)
            destination="J-9",
            is_emergency=True
        )
        
        violations = violation_detector.check_violations(
            vehicles=[ambulance],
            junctions=[test_junction]
        )
        
        assert len(violations) == 0
    
    def test_statistics_tracking(self, violation_detector, test_vehicle, test_junction):
        """Test that statistics are tracked correctly"""
        test_vehicle.heading = 0
        test_vehicle.speed = 20.0
        test_vehicle.position.x = test_junction.position.x
        test_vehicle.position.y = test_junction.position.y
        
        violation_detector.check_violations([test_vehicle], [test_junction])
        
        stats = violation_detector.get_statistics()
        
        assert stats['totalViolations'] == 1
        assert stats['violationsByType']['RED_LIGHT'] == 1


# ============================================
# VehicleOwnerDatabase Tests
# ============================================

class TestVehicleOwnerDatabase:
    """Tests for VehicleOwnerDatabase"""
    
    def test_initialization(self, vehicle_owner_db):
        """Test database initializes correctly"""
        assert vehicle_owner_db is not None
    
    def test_register_vehicle(self, vehicle_owner_db):
        """Test vehicle registration"""
        owner = vehicle_owner_db.register_vehicle("GJ18TEST123")
        
        assert owner is not None
        assert owner.number_plate == "GJ18TEST123"
        assert owner.wallet_balance >= 5000
    
    def test_get_owner(self, vehicle_owner_db):
        """Test owner lookup"""
        # Register first
        vehicle_owner_db.register_vehicle("GJ18TEST456")
        
        # Lookup
        owner = vehicle_owner_db.get_owner("GJ18TEST456")
        
        assert owner is not None
        assert owner.number_plate == "GJ18TEST456"
    
    def test_auto_register_on_lookup(self, vehicle_owner_db):
        """Test auto-registration on lookup"""
        # Lookup without registering
        owner = vehicle_owner_db.get_owner("GJ18NEW789")
        
        assert owner is not None
        assert owner.number_plate == "GJ18NEW789"
    
    def test_deduct_fine(self, vehicle_owner_db):
        """Test fine deduction"""
        import uuid
        unique_id = uuid.uuid4().hex[:6]
        plate = f"GJ18FINE{unique_id}"
        
        owner = vehicle_owner_db.register_vehicle(plate)
        owner.wallet_balance = 10000.0  # Reset balance
        owner.total_fines_paid = 0.0  # Reset fines
        initial_balance = owner.wallet_balance
        
        success, error = vehicle_owner_db.deduct_fine(plate, 1000.0)
        
        assert success is True
        assert error is None
        assert owner.wallet_balance == initial_balance - 1000.0
        assert owner.total_fines_paid == 1000.0
    
    def test_insufficient_balance(self, vehicle_owner_db):
        """Test deduction fails with insufficient balance"""
        owner = vehicle_owner_db.register_vehicle("GJ18LOW001")
        owner.wallet_balance = 500.0  # Set low balance
        
        success, error = vehicle_owner_db.deduct_fine("GJ18LOW001", 1000.0)
        
        assert success is False
        assert "Insufficient" in error
    
    def test_add_balance(self, vehicle_owner_db):
        """Test adding balance to wallet"""
        owner = vehicle_owner_db.register_vehicle("GJ18ADD001")
        initial = owner.wallet_balance
        
        success = vehicle_owner_db.add_balance("GJ18ADD001", 5000.0)
        
        assert success is True
        assert owner.wallet_balance == initial + 5000.0


# ============================================
# ChallanManager Tests
# ============================================

class TestChallanManager:
    """Tests for ChallanManager"""
    
    def test_initialization(self, challan_manager):
        """Test manager initializes correctly"""
        assert challan_manager is not None
        # Manager loads existing challans from DB, so just verify it initializes
        assert challan_manager.total_challans >= 0
    
    def test_generate_challan(self, challan_manager, vehicle_owner_db):
        """Test challan generation from violation"""
        import uuid
        unique_id = uuid.uuid4().hex[:6]
        plate = f"GJ18CH{unique_id}"
        
        # Register owner first
        vehicle_owner_db.register_vehicle(plate)
        
        violation = ViolationEvent(
            violation_id=f"VIO-GEN-{unique_id}",
            vehicle_id=f"v-test-{unique_id}",
            number_plate=plate,
            violation_type=ViolationType.RED_LIGHT,
            location=(200, 200),
            junction_id="J-5",
            road_id=None,
            location_name="Test Junction",
            lat=None,
            lon=None,
            timestamp=time.time(),
            evidence={'signalState': 'RED'},
            fine_amount=1000.0,
            severity='HIGH'
        )
        
        initial_count = challan_manager.total_challans
        challan_id = challan_manager.generate_challan(violation)
        
        assert challan_id is not None
        assert challan_id.startswith("CH-")
        assert challan_manager.total_challans == initial_count + 1
    
    def test_auto_payment_success(self, challan_manager, vehicle_owner_db):
        """Test automatic payment processing"""
        import uuid
        unique_id = uuid.uuid4().hex[:6]
        plate = f"GJ18PAY{unique_id}"
        
        owner = vehicle_owner_db.register_vehicle(plate)
        owner.wallet_balance = 5000.0
        
        violation = ViolationEvent(
            violation_id=f"VIO-PAY-{unique_id}",
            vehicle_id=f"v-pay-{unique_id}",
            number_plate=plate,
            violation_type=ViolationType.SPEEDING,
            location=(200, 200),
            junction_id=None,
            road_id="R-1",
            location_name=None,
            lat=None,
            lon=None,
            timestamp=time.time(),
            evidence={'speed': 70, 'speedLimit': 50},
            fine_amount=2000.0,
            severity='MEDIUM'
        )
        
        challan_id = challan_manager.generate_challan(violation)
        assert challan_id is not None
        
        success, error = challan_manager.process_auto_payment(challan_id)
        
        assert success is True
        
        challan = challan_manager.get_challan(challan_id)
        assert challan.status == ChallanStatus.PAID
        assert owner.wallet_balance == 3000.0  # 5000 - 2000
    
    def test_payment_failure_insufficient_balance(self, challan_manager, vehicle_owner_db):
        """Test payment fails with insufficient balance"""
        import uuid
        unique_id = uuid.uuid4().hex[:6]
        plate = f"GJ18FAIL{unique_id}"
        
        owner = vehicle_owner_db.register_vehicle(plate)
        owner.wallet_balance = 100.0  # Very low balance
        
        violation = ViolationEvent(
            violation_id=f"VIO-FAIL-{unique_id}",
            vehicle_id=f"v-fail-{unique_id}",
            number_plate=plate,
            violation_type=ViolationType.RED_LIGHT,
            location=(200, 200),
            junction_id="J-5",
            road_id=None,
            location_name=None,
            lat=None,
            lon=None,
            timestamp=time.time(),
            evidence={},
            fine_amount=1000.0,
            severity='HIGH'
        )
        
        challan_id = challan_manager.generate_challan(violation)
        assert challan_id is not None
        
        success, error = challan_manager.process_auto_payment(challan_id)
        
        assert success is False
        
        challan = challan_manager.get_challan(challan_id)
        assert challan.status == ChallanStatus.PENDING
    
    def test_get_statistics(self, challan_manager, vehicle_owner_db):
        """Test statistics calculation"""
        import uuid
        unique_id = uuid.uuid4().hex[:6]
        plate = f"GJ18STAT{unique_id}"
        
        vehicle_owner_db.register_vehicle(plate)
        
        violation = ViolationEvent(
            violation_id=f"VIO-STAT-{unique_id}",
            vehicle_id=f"v-stat-{unique_id}",
            number_plate=plate,
            violation_type=ViolationType.RED_LIGHT,
            location=(200, 200),
            junction_id="J-5",
            road_id=None,
            location_name=None,
            lat=None,
            lon=None,
            timestamp=time.time(),
            evidence={},
            fine_amount=1000.0,
            severity='HIGH'
        )
        
        challan_manager.generate_challan(violation)
        
        stats = challan_manager.get_statistics()
        
        assert stats['totalChallans'] >= 1
        assert 'pendingRevenue' in stats
        assert 'byViolationType' in stats
    
    def test_duplicate_violation_rejected(self, challan_manager, vehicle_owner_db):
        """Test that duplicate violations are rejected"""
        import uuid
        unique_id = uuid.uuid4().hex[:6]
        plate = f"GJ18DUP{unique_id}"
        
        vehicle_owner_db.register_vehicle(plate)
        
        violation = ViolationEvent(
            violation_id=f"VIO-DUP-{unique_id}",
            vehicle_id=f"v-dup-{unique_id}",
            number_plate=plate,
            violation_type=ViolationType.RED_LIGHT,
            location=(200, 200),
            junction_id="J-5",
            road_id=None,
            location_name=None,
            lat=None,
            lon=None,
            timestamp=time.time(),
            evidence={},
            fine_amount=1000.0,
            severity='HIGH'
        )
        
        # First attempt
        challan_id1 = challan_manager.generate_challan(violation)
        
        # Second attempt with same violation ID
        challan_id2 = challan_manager.generate_challan(violation)
        
        assert challan_id1 is not None
        assert challan_id2 is None  # Rejected as duplicate


# ============================================
# AutoChallanService Tests
# ============================================

class TestAutoChallanService:
    """Tests for AutoChallanService"""
    
    def test_initialization(self, auto_challan_service):
        """Test service initializes correctly"""
        assert auto_challan_service is not None
        assert auto_challan_service.running is False
    
    @pytest.mark.asyncio
    async def test_start_stop(self, auto_challan_service):
        """Test service start and stop"""
        await auto_challan_service.start()
        assert auto_challan_service.running is True
        
        await auto_challan_service.stop()
        assert auto_challan_service.running is False
    
    def test_sync_processing(self, auto_challan_service, vehicle_owner_db):
        """Test synchronous violation processing"""
        import uuid
        unique_id = uuid.uuid4().hex[:6]
        plate = f"GJ18SYNC{unique_id}"
        
        vehicle_owner_db.register_vehicle(plate)
        
        violation = ViolationEvent(
            violation_id=f"VIO-SYNC-{unique_id}",
            vehicle_id=f"v-sync-{unique_id}",
            number_plate=plate,
            violation_type=ViolationType.SPEEDING,
            location=(200, 200),
            junction_id=None,
            road_id="R-1",
            location_name=None,
            lat=None,
            lon=None,
            timestamp=time.time(),
            evidence={'speed': 80},
            fine_amount=2000.0,
            severity='HIGH'
        )
        
        initial_processed = auto_challan_service.total_processed
        challan_id = auto_challan_service.process_violation_sync(violation)
        
        assert challan_id is not None
        assert auto_challan_service.total_processed == initial_processed + 1
    
    def test_statistics(self, auto_challan_service):
        """Test statistics retrieval"""
        stats = auto_challan_service.get_statistics()
        
        assert 'running' in stats
        assert 'totalProcessed' in stats
        assert 'violationStats' in stats
        assert 'challanStats' in stats


# ============================================
# Integration Tests
# ============================================

class TestChallanIntegration:
    """End-to-end integration tests"""
    
    def test_complete_workflow(self):
        """Test complete violation → challan → payment workflow"""
        import uuid
        unique_id = uuid.uuid4().hex[:6]
        
        # Initialize all components
        detector = ViolationDetector()
        owner_db = VehicleOwnerDatabase()
        manager = ChallanManager(owner_db)
        service = AutoChallanService(detector, manager)
        
        plate = f"GJ{unique_id}"
        
        # Create test data
        vehicle = Vehicle(
            id=f"v-int-{unique_id}",
            number_plate=plate,
            type="car",
            position=Position(x=200, y=200),
            speed=30.0,
            heading=0,
            destination="J-9"
        )
        
        junction = Junction(
            id=f"J-INT-{unique_id}",
            position=Position(x=200, y=200),
            signals=JunctionSignals(
                north=SignalState(current=SignalColor.RED, duration=30, last_change=time.time()),
                east=SignalState(current=SignalColor.GREEN, duration=30, last_change=time.time()),
                south=SignalState(current=SignalColor.RED, duration=30, last_change=time.time()),
                west=SignalState(current=SignalColor.RED, duration=30, last_change=time.time())
            ),
            connected_roads=ConnectedRoads()
        )
        
        # Register owner with sufficient balance
        owner = owner_db.register_vehicle(plate)
        owner.wallet_balance = 10000.0
        
        # Detect violation
        violations = detector.check_violations([vehicle], [junction])
        assert len(violations) == 1
        
        # Process violation
        challan_id = service.process_violation_sync(violations[0])
        assert challan_id is not None
        
        # Verify challan was paid
        challan = manager.get_challan(challan_id)
        assert challan.status == ChallanStatus.PAID
        
        # Verify owner balance was deducted
        assert owner.wallet_balance < 10000.0
        
        # Verify statistics - check relative rather than absolute
        assert service.total_paid >= 1
    
    def test_revenue_tracking(self):
        """Test revenue is tracked correctly within this test session"""
        import uuid
        unique_id = uuid.uuid4().hex[:4]
        
        owner_db = VehicleOwnerDatabase()
        manager = ChallanManager(owner_db)
        
        # Record initial revenue
        initial_revenue = manager.total_revenue
        initial_paid = len([c for c in manager.challans if c.status == ChallanStatus.PAID])
        
        # Create multiple violations with unique IDs
        for i in range(5):
            plate = f"GJ{unique_id}R{i:02d}"
            owner = owner_db.register_vehicle(plate)
            owner.wallet_balance = 10000.0
            
            violation = ViolationEvent(
                violation_id=f"VIO-{unique_id}-{i:03d}",
                vehicle_id=f"v-{unique_id}-{i}",
                number_plate=plate,
                violation_type=ViolationType.RED_LIGHT,
                location=(200, 200),
                junction_id="J-5",
                road_id=None,
                location_name=None,
                lat=None,
                lon=None,
                timestamp=time.time(),
                evidence={},
                fine_amount=1000.0,
                severity='HIGH'
            )
            
            challan_id = manager.generate_challan(violation)
            manager.process_auto_payment(challan_id)
        
        # Verify revenue increased by expected amount
        stats = manager.get_statistics()
        revenue_increase = stats['totalRevenue'] - initial_revenue
        assert revenue_increase == 5000.0  # 5 * 1000
        
        paid_increase = stats['paidCount'] - initial_paid
        assert paid_increase == 5


# ============================================
# Run tests with: pytest tests/test_challan.py -v
# ============================================

