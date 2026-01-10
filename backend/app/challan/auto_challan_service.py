"""
Auto-Challan Workflow Service (FRD-09)

Automated challan processing service that:
1. Monitors for new violations
2. Generates challans automatically
3. Attempts auto-payment from wallet
4. Tracks statistics and broadcasts updates

Integrates violation detection, challan generation, and payment
into a seamless automated workflow.
"""

import asyncio
from typing import Optional, List
import time

from .violation_detector import ViolationDetector, ViolationEvent
from .challan_manager import ChallanManager


class AutoChallanService:
    """
    Automated challan processing service
    
    Workflow:
    1. Check for new violations from detector
    2. Generate challans for each violation
    3. Attempt auto-payment from owner wallet
    4. Emit real-time notifications
    5. Track statistics
    
    Runs as background task during simulation.
    """
    
    def __init__(
        self,
        violation_detector: ViolationDetector,
        challan_manager: ChallanManager,
        config: dict = None
    ):
        """
        Initialize auto-challan service
        
        Args:
            violation_detector: ViolationDetector instance
            challan_manager: ChallanManager instance
            config: Optional configuration
        """
        self.violation_detector = violation_detector
        self.challan_manager = challan_manager
        self.config = config or {}
        
        # Processing state
        self.last_processed_index = 0
        self.running = False
        self._task: Optional[asyncio.Task] = None
        
        # Configuration
        self.processing_interval = self.config.get('processingInterval', 5)  # seconds
        self.auto_payment_enabled = self.config.get('autoPayment', {}).get('enabled', True)
        
        # Statistics
        self.total_processed = 0
        self.total_paid = 0
        self.total_failed = 0
        
        # WebSocket emitter
        self._ws_emitter = None
        
        print("✅ Auto-Challan Service initialized")
    
    def set_ws_emitter(self, emitter):
        """Set WebSocket emitter for notifications"""
        self._ws_emitter = emitter
        self.violation_detector.set_ws_emitter(emitter)
        self.challan_manager.set_ws_emitter(emitter)
    
    async def start(self):
        """Start automated challan processing"""
        if self.running:
            print("⚠️ Auto-challan service already running")
            return
        
        self.running = True
        print("🚀 Auto-Challan service started")
        
        # Start processing loop
        self._task = asyncio.create_task(self._processing_loop())
    
    async def stop(self):
        """Stop automated processing"""
        self.running = False
        
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        
        print("🛑 Auto-Challan service stopped")
    
    async def _processing_loop(self):
        """Main processing loop"""
        while self.running:
            try:
                await self._process_violations()
                
                # Wait for next interval
                await asyncio.sleep(self.processing_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"❌ Auto-challan processing error: {e}")
                await asyncio.sleep(1)
    
    async def _process_violations(self):
        """Process new violations"""
        # Get all violations
        violations = self.violation_detector.violations
        
        # Process new violations only
        new_violations = violations[self.last_processed_index:]
        
        if not new_violations:
            return
        
        print(f"📋 Processing {len(new_violations)} new violations...")
        
        for violation in new_violations:
            await self._process_single_violation(violation)
        
        # Update last processed index
        self.last_processed_index = len(violations)
    
    async def _process_single_violation(self, violation: ViolationEvent):
        """Process a single violation"""
        try:
            # Generate challan
            challan_id = self.challan_manager.generate_challan(violation)
            
            if not challan_id:
                print(f"⚠️ Could not generate challan for {violation.violation_id}")
                return
            
            self.total_processed += 1
            
            # Small delay between operations
            await asyncio.sleep(0.1)
            
            # Attempt auto-payment if enabled
            if self.auto_payment_enabled:
                success, error = self.challan_manager.process_auto_payment(challan_id)
                
                if success:
                    self.total_paid += 1
                else:
                    self.total_failed += 1
        
        except Exception as e:
            print(f"❌ Error processing violation {violation.violation_id}: {e}")
    
    def process_violation_sync(self, violation: ViolationEvent) -> Optional[str]:
        """
        Process a violation synchronously (for immediate processing)
        
        Args:
            violation: ViolationEvent to process
        
        Returns:
            challan_id if successful
        """
        # Generate challan
        challan_id = self.challan_manager.generate_challan(violation)
        
        if not challan_id:
            return None
        
        self.total_processed += 1
        
        # Attempt auto-payment if enabled
        if self.auto_payment_enabled:
            success, _ = self.challan_manager.process_auto_payment(challan_id)
            if success:
                self.total_paid += 1
            else:
                self.total_failed += 1
        
        return challan_id
    
    def get_statistics(self) -> dict:
        """Get service statistics"""
        return {
            'running': self.running,
            'processingInterval': self.processing_interval,
            'autoPaymentEnabled': self.auto_payment_enabled,
            'totalProcessed': self.total_processed,
            'totalPaid': self.total_paid,
            'totalFailed': self.total_failed,
            'pendingViolations': len(self.violation_detector.violations) - self.last_processed_index,
            'violationStats': self.violation_detector.get_statistics(),
            'challanStats': self.challan_manager.get_statistics()
        }
    
    def force_process_all(self):
        """Force process all pending violations (sync)"""
        violations = self.violation_detector.violations[self.last_processed_index:]
        
        for violation in violations:
            self.process_violation_sync(violation)
        
        self.last_processed_index = len(self.violation_detector.violations)
        
        print(f"✅ Force processed {len(violations)} violations")


# Global instance
_auto_challan_service: Optional[AutoChallanService] = None


def init_auto_challan_service(
    violation_detector: ViolationDetector,
    challan_manager: ChallanManager,
    config: dict = None
) -> AutoChallanService:
    """Initialize global auto-challan service"""
    global _auto_challan_service
    _auto_challan_service = AutoChallanService(
        violation_detector=violation_detector,
        challan_manager=challan_manager,
        config=config
    )
    return _auto_challan_service


def get_auto_challan_service() -> Optional[AutoChallanService]:
    """Get global auto-challan service instance"""
    return _auto_challan_service

