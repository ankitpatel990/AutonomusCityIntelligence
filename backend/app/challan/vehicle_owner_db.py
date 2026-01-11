"""
Mock Vehicle Owner Database (FRD-09)

Mock database of vehicle owners with details for challan generation
and fine deduction. Generates realistic Indian names and data.

For demo purposes - simulates a real vehicle registration database.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, List
import random
import time

from sqlalchemy.orm import Session
from app.database.database import SessionLocal
from app.database.models import VehicleOwner as VehicleOwnerDB


@dataclass
class VehicleOwnerRecord:
    """Vehicle owner record in memory"""
    owner_id: str
    name: str
    vehicle_id: str
    number_plate: str
    license_number: str
    phone: str
    email: str
    address: str
    wallet_balance: float
    total_challans: int = 0
    total_fines_paid: float = 0.0
    registration_date: float = field(default_factory=time.time)


class VehicleOwnerDatabase:
    """
    Mock vehicle owner database
    
    Features:
    - Auto-generates owner data for new vehicles
    - Maintains wallet balance for each owner
    - Supports fine deduction
    - Persists to SQLite database
    
    For demo purposes - generates random Indian names and data.
    """
    
    # Mock owner names (Indian names for demo)
    MOCK_FIRST_NAMES = [
        "Rajesh", "Priya", "Amit", "Sneha", "Vikram",
        "Anjali", "Rahul", "Pooja", "Sanjay", "Neha",
        "Arjun", "Kavita", "Deepak", "Sunita", "Manish",
        "Rekha", "Suresh", "Geeta", "Ramesh", "Anita"
    ]
    
    MOCK_LAST_NAMES = [
        "Kumar", "Sharma", "Patel", "Singh", "Reddy",
        "Gupta", "Verma", "Desai", "Mehta", "Joshi",
        "Shah", "Rao", "Nair", "Pillai", "Iyer"
    ]
    
    MOCK_CITIES = [
        "Gandhinagar", "Ahmedabad", "GIFT City", 
        "Vadodara", "Surat", "Rajkot"
    ]
    
    MOCK_SECTORS = [
        "Sector 1", "Sector 2", "Sector 5", "Sector 7",
        "Sector 11", "Sector 21", "Sector 28", "Sector 30"
    ]
    
    def __init__(self, config: dict = None):
        """
        Initialize vehicle owner database
        
        Args:
            config: Configuration with min/max balance settings
        """
        self.config = config or {}
        
        # In-memory cache
        self.owners: Dict[str, VehicleOwnerRecord] = {}
        self.owner_counter = 0
        
        # Balance configuration
        self.min_balance = self.config.get('minBalance', 5000)
        self.max_balance = self.config.get('maxBalance', 50000)
        
        # Load existing owners from database
        self._load_from_database()
        
        print(f"[OK] Vehicle Owner Database initialized ({len(self.owners)} owners loaded)")
    
    def _load_from_database(self):
        """Load existing owners from SQLite database"""
        try:
            db = SessionLocal()
            owners = db.query(VehicleOwnerDB).all()
            
            for owner in owners:
                record = VehicleOwnerRecord(
                    owner_id=f"OWN-{len(self.owners) + 1:04d}",
                    name=owner.owner_name,
                    vehicle_id=owner.number_plate,
                    number_plate=owner.number_plate,
                    license_number=f"DL-{random.randint(10, 99)}-{random.randint(1000, 9999)}",
                    phone=owner.contact,
                    email=owner.email or f"{owner.number_plate.lower()}@mock.com",
                    address=owner.address or "Mock Address",
                    wallet_balance=owner.wallet_balance,
                    total_challans=owner.total_challans,
                    total_fines_paid=owner.total_fines_paid,
                    registration_date=time.time()
                )
                self.owners[owner.number_plate] = record
            
            db.close()
        except Exception as e:
            print(f"[WARN] Could not load owners from database: {e}")
    
    def _generate_number_plate(self) -> str:
        """Generate a realistic Gujarat number plate"""
        # Format: GJ-XX-YY-ZZZZ
        district_codes = ["01", "02", "03", "05", "06", "18", "21"]
        district = random.choice(district_codes)
        
        letters = "".join(random.choices("ABCDEFGHJKLMNPQRSTUVWXYZ", k=2))
        numbers = random.randint(1000, 9999)
        
        return f"GJ{district}{letters}{numbers}"
    
    def _generate_mock_owner(self, number_plate: str) -> VehicleOwnerRecord:
        """Generate mock owner data"""
        self.owner_counter += 1
        
        first_name = random.choice(self.MOCK_FIRST_NAMES)
        last_name = random.choice(self.MOCK_LAST_NAMES)
        name = f"{first_name} {last_name}"
        
        city = random.choice(self.MOCK_CITIES)
        sector = random.choice(self.MOCK_SECTORS)
        house_no = random.randint(1, 999)
        
        return VehicleOwnerRecord(
            owner_id=f"OWN-{self.owner_counter:04d}",
            name=name,
            vehicle_id=number_plate,
            number_plate=number_plate,
            license_number=f"DL-{random.randint(10, 99)}-{random.randint(1000, 9999)}",
            phone=f"+91-{random.randint(7000000000, 9999999999)}",
            email=f"{first_name.lower()}.{last_name.lower()}@email.com",
            address=f"{house_no}, {sector}, {city}, Gujarat",
            wallet_balance=random.uniform(self.min_balance, self.max_balance),
            total_challans=0,
            total_fines_paid=0.0,
            registration_date=time.time()
        )
    
    def register_vehicle(self, number_plate: str) -> VehicleOwnerRecord:
        """
        Register a vehicle with mock owner data
        
        If already registered, returns existing record.
        
        Args:
            number_plate: Vehicle number plate
        
        Returns:
            VehicleOwnerRecord
        """
        # Check if already registered
        if number_plate in self.owners:
            return self.owners[number_plate]
        
        # Generate mock owner
        owner = self._generate_mock_owner(number_plate)
        self.owners[number_plate] = owner
        
        # Persist to database
        self._save_to_database(owner)
        
        print(f"📝 Registered vehicle: {number_plate} -> {owner.name}")
        
        return owner
    
    def _save_to_database(self, owner: VehicleOwnerRecord):
        """Save owner to SQLite database"""
        try:
            db = SessionLocal()
            
            # Check if exists
            existing = db.query(VehicleOwnerDB).filter(
                VehicleOwnerDB.number_plate == owner.number_plate
            ).first()
            
            if existing:
                # Update existing
                existing.wallet_balance = owner.wallet_balance
                existing.total_challans = owner.total_challans
                existing.total_fines_paid = owner.total_fines_paid
            else:
                # Create new
                db_owner = VehicleOwnerDB(
                    number_plate=owner.number_plate,
                    owner_name=owner.name,
                    contact=owner.phone,
                    email=owner.email,
                    address=owner.address,
                    wallet_balance=owner.wallet_balance,
                    total_challans=owner.total_challans,
                    total_fines_paid=owner.total_fines_paid
                )
                db.add(db_owner)
            
            db.commit()
            db.close()
        except Exception as e:
            print(f"[WARN] Could not save owner to database: {e}")
    
    def get_owner(self, number_plate: str) -> Optional[VehicleOwnerRecord]:
        """
        Get owner for vehicle
        
        Auto-registers if not exists (for demo convenience).
        
        Args:
            number_plate: Vehicle number plate
        
        Returns:
            VehicleOwnerRecord or None
        """
        # Auto-register if not exists (for demo)
        if number_plate not in self.owners:
            return self.register_vehicle(number_plate)
        
        return self.owners.get(number_plate)
    
    def get_owner_by_vehicle_id(self, vehicle_id: str) -> Optional[VehicleOwnerRecord]:
        """Get owner by vehicle ID (searches by vehicle_id field)"""
        for owner in self.owners.values():
            if owner.vehicle_id == vehicle_id:
                return owner
        return None
    
    def deduct_fine(self, number_plate: str, amount: float) -> tuple[bool, Optional[str]]:
        """
        Deduct fine from owner's wallet
        
        Args:
            number_plate: Vehicle number plate
            amount: Fine amount to deduct
        
        Returns:
            (success, error_message)
        """
        owner = self.get_owner(number_plate)
        
        if not owner:
            return False, "Owner not found"
        
        # Check sufficient balance
        if owner.wallet_balance < amount:
            print(f"[WARN] Insufficient balance for {number_plate}: ₹{owner.wallet_balance:.2f} < ₹{amount:.2f}")
            return False, f"Insufficient balance: ₹{owner.wallet_balance:.2f}"
        
        # Deduct amount
        previous_balance = owner.wallet_balance
        owner.wallet_balance -= amount
        owner.total_fines_paid += amount
        owner.total_challans += 1
        
        # Update database
        self._save_to_database(owner)
        
        print(f"💰 Fine deducted: {number_plate} - ₹{amount:.2f} (Balance: ₹{previous_balance:.2f} → ₹{owner.wallet_balance:.2f})")
        
        return True, None
    
    def add_balance(self, number_plate: str, amount: float) -> bool:
        """
        Add balance to owner's wallet (for demo)
        
        Args:
            number_plate: Vehicle number plate
            amount: Amount to add
        
        Returns:
            success
        """
        owner = self.get_owner(number_plate)
        
        if not owner:
            return False
        
        owner.wallet_balance += amount
        self._save_to_database(owner)
        
        print(f"💳 Balance added: {number_plate} + ₹{amount:.2f} (New balance: ₹{owner.wallet_balance:.2f})")
        
        return True
    
    def get_all_owners(self) -> List[VehicleOwnerRecord]:
        """Get all registered owners"""
        return list(self.owners.values())
    
    def get_owner_count(self) -> int:
        """Get total number of registered owners"""
        return len(self.owners)
    
    def get_statistics(self) -> dict:
        """Get owner database statistics"""
        owners = list(self.owners.values())
        
        total_balance = sum(o.wallet_balance for o in owners)
        total_fines = sum(o.total_fines_paid for o in owners)
        total_challans = sum(o.total_challans for o in owners)
        
        return {
            'totalOwners': len(owners),
            'totalBalance': total_balance,
            'totalFinesPaid': total_fines,
            'totalChallans': total_challans,
            'avgBalance': total_balance / len(owners) if owners else 0
        }
    
    def seed_mock_owners(self, count: int = 50):
        """
        Seed database with mock owners
        
        Creates 'count' random vehicle owners for demo.
        """
        for _ in range(count):
            number_plate = self._generate_number_plate()
            if number_plate not in self.owners:
                self.register_vehicle(number_plate)
        
        print(f"[OK] Seeded {count} mock vehicle owners")


# Global instance
_vehicle_owner_db: Optional[VehicleOwnerDatabase] = None


def init_vehicle_owner_db(config: dict = None) -> VehicleOwnerDatabase:
    """Initialize global vehicle owner database"""
    global _vehicle_owner_db
    _vehicle_owner_db = VehicleOwnerDatabase(config)
    return _vehicle_owner_db


def get_vehicle_owner_db() -> Optional[VehicleOwnerDatabase]:
    """Get global vehicle owner database instance"""
    return _vehicle_owner_db

