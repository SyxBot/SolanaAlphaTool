"""
Shared Memory Reporter for Bot 1
Reports token intelligence and wallet reputation to shared memory system.
"""

import json
import time
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict

from utils import (
    post_to_memory, 
    get_from_memory, 
    ping_memory_server,
    log_event,
    format_token_data,
    format_wallet_intel,
    get_config
)

logger = logging.getLogger(__name__)


@dataclass
class TokenData:
    """Token data structure for memory reporting."""
    mint: str
    symbol: str
    creator: str
    name: Optional[str] = None
    alerted_by: str = "bot1"
    alerted_at: float = None
    status: str = "untracked"
    liquidity_sol: Optional[float] = None
    quality_score: Optional[float] = None
    filter_reasons: Optional[List[str]] = None
    
    def __post_init__(self):
        if self.alerted_at is None:
            self.alerted_at = time.time()


@dataclass
class WalletIntel:
    """Wallet intelligence data structure."""
    address: str
    reputation: str  # "trusted", "blocked", "suspicious"
    reason: str
    reported_by: str = "bot1"
    reported_at: float = None
    token_count: Optional[int] = None
    success_rate: Optional[float] = None
    
    def __post_init__(self):
        if self.reported_at is None:
            self.reported_at = time.time()


class MemoryReporter:
    """Reporter for shared memory system."""
    
    def __init__(self):
        """Initialize memory reporter with environment configuration."""
        log_event("Initializing memory reporter")
    
    def report_token_to_memory(self, token_data: Dict[str, Any]) -> bool:
        """
        Report token data to shared memory.
        
        Args:
            token_data: Dictionary containing token information
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Ensure required fields
            if not all(field in token_data for field in ['mint', 'symbol', 'creator']):
                log_event(f"Missing required fields in token data: {token_data}", 'error')
                return False
            
            # Create structured token data
            token_obj = TokenData(
                mint=token_data['mint'],
                symbol=token_data['symbol'],
                creator=token_data['creator'],
                name=token_data.get('name'),
                alerted_by=get_config('BOT_IDENTIFIER', 'BOT1'),
                liquidity_sol=token_data.get('liquidity_sol'),
                quality_score=token_data.get('quality_score'),
                filter_reasons=token_data.get('filter_reasons', [])
            )
            
            # Send to memory server using utils function
            success = post_to_memory('/memory/append_token', asdict(token_obj))
            
            if success:
                log_event(f"Reported token {token_obj.symbol} to memory server")
            
            return success
                
        except Exception as e:
            log_event(f"Error reporting token to memory: {e}", 'error')
            return False
    
    def report_trusted_wallet(self, address: str, reason: str, success_rate: float = None) -> bool:
        """
        Report a wallet as trusted (launched successful tokens).
        
        Args:
            address: Wallet address
            reason: Reason for trust (e.g., "launched successful token PEPE")
            success_rate: Optional success rate (0.0-1.0)
            
        Returns:
            bool: True if successful, False otherwise
        """
        wallet_intel = format_wallet_intel(
            address=address,
            reputation="trusted",
            reason=reason,
            success_rate=success_rate
        )
        
        return self._report_wallet_intel(wallet_intel)
    
    def report_blocked_wallet(self, address: str, reason: str) -> bool:
        """
        Report a wallet as blocked (known scammer/rugger).
        
        Args:
            address: Wallet address
            reason: Reason for blocking (e.g., "rug pulled SCAM token")
            
        Returns:
            bool: True if successful, False otherwise
        """
        wallet_intel = format_wallet_intel(
            address=address,
            reputation="blocked",
            reason=reason
        )
        
        return self._report_wallet_intel(wallet_intel)
    
    def report_suspicious_wallet(self, address: str, reason: str) -> bool:
        """
        Report a wallet as suspicious (potential risk).
        
        Args:
            address: Wallet address
            reason: Reason for suspicion (e.g., "new wallet with multiple failed tokens")
            
        Returns:
            bool: True if successful, False otherwise
        """
        wallet_intel = format_wallet_intel(
            address=address,
            reputation="suspicious", 
            reason=reason
        )
        
        return self._report_wallet_intel(wallet_intel)
    
    def _report_wallet_intel(self, wallet_intel: Dict[str, Any]) -> bool:
        """
        Internal method to report wallet intelligence.
        
        Args:
            wallet_intel: Formatted wallet intel dictionary
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            success = post_to_memory('/memory/update_wallet', wallet_intel)
            
            if success:
                log_event(f"Reported {wallet_intel['reputation']} wallet {wallet_intel['address'][:8]}... to memory")
            
            return success
                
        except Exception as e:
            log_event(f"Error reporting wallet intel: {e}", 'error')
            return False
    
    def get_wallet_reputation(self, address: str) -> Optional[Dict[str, Any]]:
        """
        Get wallet reputation from memory server.
        
        Args:
            address: Wallet address to check
            
        Returns:
            dict: Wallet reputation data or None if not found/error
        """
        try:
            return get_from_memory(f'/memory/wallet_reputation/{address}')
                
        except Exception as e:
            log_event(f"Error getting wallet reputation: {e}", 'error')
            return None
    
    def ping_memory_server(self) -> bool:
        """
        Test connection to memory server.
        
        Returns:
            bool: True if server is reachable, False otherwise
        """
        return ping_memory_server()


# Global memory reporter instance
memory_reporter = MemoryReporter()


def report_token_to_memory(token_data: Dict[str, Any]) -> bool:
    """
    Convenience function to report token data to shared memory.
    
    Args:
        token_data: Dictionary containing token information
        
    Returns:
        bool: True if successful, False otherwise
    """
    return memory_reporter.report_token_to_memory(token_data)


def report_trusted_wallet(address: str, reason: str, success_rate: float = None) -> bool:
    """
    Convenience function to report a trusted wallet.
    
    Args:
        address: Wallet address
        reason: Reason for trust
        success_rate: Optional success rate
        
    Returns:
        bool: True if successful, False otherwise
    """
    return memory_reporter.report_trusted_wallet(address, reason, success_rate)


def report_blocked_wallet(address: str, reason: str) -> bool:
    """
    Convenience function to report a blocked wallet.
    
    Args:
        address: Wallet address
        reason: Reason for blocking
        
    Returns:
        bool: True if successful, False otherwise
    """
    return memory_reporter.report_blocked_wallet(address, reason)


def report_suspicious_wallet(address: str, reason: str) -> bool:
    """
    Convenience function to report a suspicious wallet.
    
    Args:
        address: Wallet address
        reason: Reason for suspicion
        
    Returns:
        bool: True if successful, False otherwise
    """
    return memory_reporter.report_suspicious_wallet(address, reason)


def get_wallet_reputation(address: str) -> Optional[Dict[str, Any]]:
    """
    Convenience function to get wallet reputation.
    
    Args:
        address: Wallet address
        
    Returns:
        dict: Wallet reputation or None
    """
    return memory_reporter.get_wallet_reputation(address)


# Example usage for integration with webhook alert bot
def enhanced_token_handler_with_memory(token_info, should_alert_result: bool, filter_details: Dict[str, Any] = None):
    """
    Enhanced token handler that reports to memory regardless of alert status.
    
    Args:
        token_info: TokenInfo object from pump monitor
        should_alert_result: Result from should_alert() function
        filter_details: Optional detailed filter results
    """
    try:
        # Prepare token data for memory
        token_data = {
            "mint": str(token_info.mint),
            "symbol": token_info.symbol,
            "creator": str(token_info.creator),
            "name": token_info.name,
            "status": "alerted" if should_alert_result else "filtered"
        }
        
        # Add filter details if available
        if filter_details:
            token_data.update({
                "quality_score": filter_details.get("quality_score"),
                "liquidity_sol": filter_details.get("liquidity_sol"),
                "filter_reasons": filter_details.get("rejection_reasons", [])
            })
        
        # Report to memory
        success = report_token_to_memory(token_data)
        
        if success:
            logger.info(f"📝 Reported {token_info.symbol} to shared memory")
        else:
            logger.warning(f"Failed to report {token_info.symbol} to memory")
        
        # Update wallet reputation based on filter results
        if filter_details and filter_details.get("rejection_reasons"):
            reasons = filter_details["rejection_reasons"]
            creator = str(token_info.creator)
            
            # Check for suspicious patterns
            if any("suspicious wallet" in reason.lower() for reason in reasons):
                report_suspicious_wallet(creator, f"Created filtered token {token_info.symbol}: {'; '.join(reasons)}")
            elif any("low liquidity" in reason.lower() for reason in reasons):
                # Don't penalize for low liquidity alone, might be legitimate
                pass
        
    except Exception as e:
        logger.error(f"Error in enhanced token handler with memory: {e}")


def test_memory_reporter():
    """
    Test the memory reporter functionality.
    """
    print("🧪 Memory Reporter Test")
    print("=" * 40)
    
    # Test server connectivity
    print("📡 Testing memory server connectivity...")
    is_reachable = memory_reporter.ping_memory_server()
    print(f"   Server reachable: {is_reachable}")
    
    if not is_reachable:
        print("❌ Cannot reach memory server - using mock data for testing")
        return
    
    # Test token reporting
    print("\n📊 Testing token data reporting...")
    
    test_token = {
        "mint": "TestMint123456789",
        "symbol": "TEST",
        "creator": "TestCreator123456789",
        "name": "Test Token",
        "liquidity_sol": 5.5,
        "quality_score": 7.2
    }
    
    success = report_token_to_memory(test_token)
    print(f"   Token report success: {success}")
    
    # Test wallet reputation reporting
    print("\n👤 Testing wallet reputation reporting...")
    
    test_creator = "TestCreator123456789"
    
    # Report as suspicious
    success = report_suspicious_wallet(test_creator, "Test suspicious wallet")
    print(f"   Suspicious wallet report: {success}")
    
    # Get reputation
    reputation = memory_reporter.get_wallet_reputation(test_creator)
    print(f"   Retrieved reputation: {reputation}")
    
    print("\n✅ Memory reporter test completed")


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Run test
    test_memory_reporter()