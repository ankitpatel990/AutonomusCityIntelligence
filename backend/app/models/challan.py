"""
Challan (Traffic Fine) Models

Models for digital challan generation, payment, and tracking.
"""

from pydantic import BaseModel, Field
from typing import Literal, Optional
from uuid import uuid4
import time


class VehicleOwner(BaseModel):
    """
    Mock vehicle owner data
    
    Simulates a vehicle registration database.
    """
    number_plate: str
    owner_name: str
    contact: str                          # Phone number
    email: Optional[str] = None
    address: Optional[str] = None
    wallet_balance: float = 5000.0        # Mock wallet balance
    total_challans: int = 0
    total_fines_paid: float = 0.0
    registration_date: Optional[float] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "number_plate": "GJ18AB1234",
                "owner_name": "John Doe",
                "contact": "9876543210",
                "wallet_balance": 10000.0,
                "total_challans": 2
            }
        }


class Challan(BaseModel):
    """
    Digital traffic challan
    
    Represents a traffic fine issued for a violation.
    """
    challan_id: str = Field(default_factory=lambda: f"CH-{uuid4().hex[:10].upper()}")
    violation_id: str
    
    # Vehicle & Owner
    number_plate: str
    owner_name: str
    
    # Violation details
    violation_type: str
    violation_description: Optional[str] = None
    fine_amount: float
    
    # Location
    location: str                         # Junction/Road ID
    location_name: Optional[str] = None   # Human-readable name
    lat: Optional[float] = None
    lon: Optional[float] = None
    
    # Timestamps
    violation_timestamp: float            # When violation occurred
    issued_timestamp: float = Field(default_factory=time.time)
    
    # Status
    status: Literal['ISSUED', 'PAID', 'PENDING', 'APPEALED', 'CANCELLED'] = 'ISSUED'
    paid_at: Optional[float] = None
    transaction_id: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "challan_id": "CH-ABC1234567",
                "violation_id": "vio-xyz789",
                "number_plate": "GJ18AB1234",
                "owner_name": "John Doe",
                "violation_type": "RED_LIGHT",
                "fine_amount": 1000.0,
                "location": "J-5",
                "status": "ISSUED"
            }
        }


class ChallanTransaction(BaseModel):
    """
    Challan payment transaction
    
    Records payment attempts and wallet deductions.
    """
    transaction_id: str = Field(default_factory=lambda: f"TXN-{uuid4().hex[:10].upper()}")
    challan_id: str
    number_plate: str
    
    amount: float
    previous_balance: float
    new_balance: float
    
    timestamp: float = Field(default_factory=time.time)
    status: Literal['SUCCESS', 'FAILED', 'PENDING'] = 'SUCCESS'
    failure_reason: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "transaction_id": "TXN-ABC1234567",
                "challan_id": "CH-XYZ789",
                "number_plate": "GJ18AB1234",
                "amount": 1000.0,
                "previous_balance": 5000.0,
                "new_balance": 4000.0,
                "status": "SUCCESS"
            }
        }


class ChallanStats(BaseModel):
    """Statistics about challans"""
    total_challans: int
    paid_count: int
    pending_count: int
    total_fine_amount: float
    collected_amount: float
    pending_amount: float
    by_violation_type: dict[str, int]
    
    class Config:
        json_schema_extra = {
            "example": {
                "total_challans": 150,
                "paid_count": 120,
                "pending_count": 30,
                "total_fine_amount": 175000.0,
                "collected_amount": 140000.0,
                "pending_amount": 35000.0
            }
        }


class PayChallanRequest(BaseModel):
    """Request to pay a challan"""
    challan_id: str


class IssueChallanRequest(BaseModel):
    """Request to manually issue a challan"""
    violation_id: str
    fine_amount: Optional[float] = None   # Override default fine


# Mock vehicle owners for demo
MOCK_OWNERS = [
    VehicleOwner(
        number_plate="GJ18AB1234",
        owner_name="Rajesh Kumar",
        contact="9876543210",
        wallet_balance=15000.0
    ),
    VehicleOwner(
        number_plate="GJ18CD5678",
        owner_name="Priya Sharma",
        contact="9876543211",
        wallet_balance=8000.0
    ),
    VehicleOwner(
        number_plate="GJ18EF9012",
        owner_name="Amit Patel",
        contact="9876543212",
        wallet_balance=25000.0
    ),
    VehicleOwner(
        number_plate="GJ18GH3456",
        owner_name="Sneha Desai",
        contact="9876543213",
        wallet_balance=12000.0
    ),
    VehicleOwner(
        number_plate="GJ18IJ7890",
        owner_name="Vikram Singh",
        contact="9876543214",
        wallet_balance=5000.0
    )
]

