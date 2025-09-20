"""
Complete Token Filter for Pump.fun Signal Alert Bot
Combines wallet analysis, symbol validation, and liquidity filtering.
"""

import asyncio
import os
from typing import Dict, Any, Optional
from solana.rpc.async_api import AsyncClient
from wallet_analyzer import is_wallet_suspicious_async, get_wallet_details
from symbol_validator import is_symbol_valid, validate_symbol_with_details
from liquidity_analyzer import get_initial_liquidity_async, get_detailed_liquidity_info
from pump_monitor import TokenInfo
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TokenFilterConfig:
    """Configuration for token filtering criteria."""
    
    def __init__(
        self,
        min_wallet_age_minutes: int = 15,
        min_wallet_transactions: int = 3,
        require_valid_symbol: bool = True,
        min_liquidity_sol: float = 0.5,
        max_liquidity_sol: float = 100.0,
        enable_wallet_filter: bool = True,
        enable_symbol_filter: bool = True,
        enable_liquidity_filter: bool = True
    ):
        self.min_wallet_age_minutes = min_wallet_age_minutes
        self.min_wallet_transactions = min_wallet_transactions
        self.require_valid_symbol = require_valid_symbol
        self.min_liquidity_sol = min_liquidity_sol
        self.max_liquidity_sol = max_liquidity_sol
        self.enable_wallet_filter = enable_wallet_filter
        self.enable_symbol_filter = enable_symbol_filter
        self.enable_liquidity_filter = enable_liquidity_filter


class TokenFilterResult:
    """Result of token filtering with detailed information."""
    
    def __init__(self, token_info: TokenInfo):
        self.token_info = token_info
        self.passed_filters = False
        self.rejection_reasons = []
        
        # Individual filter results
        self.symbol_validation = None
        self.wallet_analysis = None
        self.liquidity_analysis = None
        
        # Overall assessment
        self.quality_score = 0.0
        self.recommendation = "REJECT"


async def complete_token_filter(
    token_info: TokenInfo, 
    config: TokenFilterConfig = None
) -> TokenFilterResult:
    """
    Apply complete token filtering with wallet, symbol, and liquidity analysis.
    
    Args:
        token_info: Token information from pump.fun detection
        config: Filtering configuration (uses defaults if None)
        
    Returns:
        TokenFilterResult: Comprehensive filtering results
    """
    if config is None:
        config = TokenFilterConfig()
        
    result = TokenFilterResult(token_info)
    
    logger.info(f"🔍 Complete filtering: {token_info.name} ({token_info.symbol})")
    
    try:
        # Step 1: Symbol Validation
        if config.enable_symbol_filter:
            result.symbol_validation = validate_symbol_with_details(token_info.symbol)
            
            if config.require_valid_symbol and not result.symbol_validation["is_valid"]:
                result.rejection_reasons.append(f"Invalid symbol: {result.symbol_validation['reason']}")
                logger.warning(f"❌ Symbol filter failed: {result.symbol_validation['reason']}")
            else:
                logger.info(f"✅ Symbol filter passed: {token_info.symbol}")
        
        # Step 2: Wallet Analysis
        if config.enable_wallet_filter:
            helius_key = os.getenv("HELIUS_API_KEY")
            if helius_key:
                rpc_url = f"https://mainnet.helius-rpc.com/?api-key={helius_key}"
            else:
                rpc_url = "https://api.mainnet-beta.solana.com"
                
            client = AsyncClient(rpc_url)
            
            try:
                creator_address = str(token_info.creator)
                result.wallet_analysis = await get_wallet_details(creator_address, client)
                
                if result.wallet_analysis["is_suspicious"]:
                    result.rejection_reasons.append(f"Suspicious wallet: {result.wallet_analysis['reason']}")
                    logger.warning(f"❌ Wallet filter failed: {result.wallet_analysis['reason']}")
                else:
                    logger.info(f"✅ Wallet filter passed: {result.wallet_analysis['age_minutes']:.1f}min, {result.wallet_analysis['transaction_count']}txs")
                    
            finally:
                await client.close()
        
        # Step 3: Liquidity Analysis
        if config.enable_liquidity_filter:
            token_mint = str(token_info.mint)
            result.liquidity_analysis = await get_detailed_liquidity_info(token_mint)
            
            liquidity_sol = result.liquidity_analysis["liquidity_sol"]
            
            if liquidity_sol < config.min_liquidity_sol:
                result.rejection_reasons.append(f"Low liquidity: {liquidity_sol:.4f} SOL < {config.min_liquidity_sol} SOL minimum")
                logger.warning(f"❌ Liquidity filter failed: {liquidity_sol:.4f} SOL too low")
            elif liquidity_sol > config.max_liquidity_sol:
                result.rejection_reasons.append(f"High liquidity: {liquidity_sol:.4f} SOL > {config.max_liquidity_sol} SOL maximum")
                logger.warning(f"❌ Liquidity filter failed: {liquidity_sol:.4f} SOL too high")
            else:
                logger.info(f"✅ Liquidity filter passed: {liquidity_sol:.4f} SOL")
        
        # Calculate overall result
        result.passed_filters = len(result.rejection_reasons) == 0
        
        if result.passed_filters:
            result.recommendation = "APPROVE"
            result.quality_score = _calculate_quality_score(result)
            logger.info(f"🎯 Token {token_info.name} APPROVED (Quality: {result.quality_score:.1f}/10)")
        else:
            result.recommendation = "REJECT"
            logger.warning(f"🚫 Token {token_info.name} REJECTED: {'; '.join(result.rejection_reasons)}")
            
    except Exception as e:
        logger.error(f"Error in complete_token_filter for {token_info.name}: {e}")
        result.rejection_reasons.append(f"Filter error: {str(e)}")
        result.recommendation = "REJECT"
        
    return result


def _calculate_quality_score(result: TokenFilterResult) -> float:
    """
    Calculate a quality score (0-10) based on filtering results.
    Higher score indicates better quality token.
    """
    score = 0.0
    
    # Symbol quality (0-2 points)
    if result.symbol_validation and result.symbol_validation["is_valid"]:
        symbol_len = result.symbol_validation["length"]
        if 3 <= symbol_len <= 5:  # Optimal length
            score += 2.0
        elif symbol_len == 2 or symbol_len == 6:  # Acceptable length
            score += 1.5
        else:
            score += 1.0
    
    # Wallet quality (0-4 points)
    if result.wallet_analysis and not result.wallet_analysis["is_suspicious"]:
        age_hours = result.wallet_analysis["age_hours"]
        tx_count = result.wallet_analysis["transaction_count"]
        
        # Age scoring
        if age_hours >= 24:  # 1+ day old
            score += 2.0
        elif age_hours >= 1:  # 1+ hour old
            score += 1.5
        elif age_hours >= 0.5:  # 30+ minutes old
            score += 1.0
        else:
            score += 0.5
        
        # Transaction count scoring
        if tx_count >= 20:
            score += 2.0
        elif tx_count >= 10:
            score += 1.5
        elif tx_count >= 5:
            score += 1.0
        else:
            score += 0.5
    
    # Liquidity quality (0-4 points)
    if result.liquidity_analysis:
        liquidity = result.liquidity_analysis["liquidity_sol"]
        
        if 5.0 <= liquidity <= 20.0:  # Optimal range
            score += 4.0
        elif 2.0 <= liquidity <= 50.0:  # Good range
            score += 3.0
        elif 1.0 <= liquidity <= 100.0:  # Acceptable range
            score += 2.0
        elif 0.5 <= liquidity < 1.0:  # Low but acceptable
            score += 1.0
        else:
            score += 0.5
    
    return min(score, 10.0)  # Cap at 10


async def filter_and_rank_tokens(
    token_list: list[TokenInfo], 
    config: TokenFilterConfig = None
) -> tuple[list[TokenFilterResult], list[TokenFilterResult]]:
    """
    Filter and rank a list of tokens.
    
    Args:
        token_list: List of tokens to filter
        config: Filtering configuration
        
    Returns:
        tuple: (approved_tokens, rejected_tokens) sorted by quality score
    """
    if config is None:
        config = TokenFilterConfig()
    
    results = []
    
    # Process all tokens
    for token_info in token_list:
        result = await complete_token_filter(token_info, config)
        results.append(result)
    
    # Separate approved and rejected
    approved = [r for r in results if r.passed_filters]
    rejected = [r for r in results if not r.passed_filters]
    
    # Sort by quality score (highest first)
    approved.sort(key=lambda x: x.quality_score, reverse=True)
    rejected.sort(key=lambda x: len(x.rejection_reasons))  # Least rejections first
    
    return approved, rejected


def print_filter_summary(approved: list[TokenFilterResult], rejected: list[TokenFilterResult]):
    """Print a summary of filtering results."""
    
    total = len(approved) + len(rejected)
    approval_rate = (len(approved) / total * 100) if total > 0 else 0
    
    print(f"\n📊 TOKEN FILTERING SUMMARY")
    print("=" * 50)
    print(f"Total Processed: {total}")
    print(f"Approved: {len(approved)} ({approval_rate:.1f}%)")
    print(f"Rejected: {len(rejected)} ({100-approval_rate:.1f}%)")
    
    if approved:
        print(f"\n🎉 TOP APPROVED TOKENS:")
        for i, result in enumerate(approved[:5], 1):
            token = result.token_info
            print(f"  {i}. {token.name} ({token.symbol}) - Quality: {result.quality_score:.1f}/10")
            if result.liquidity_analysis:
                print(f"     Liquidity: {result.liquidity_analysis['liquidity_sol']:.4f} SOL")
            if result.wallet_analysis:
                print(f"     Wallet: {result.wallet_analysis['age_hours']:.1f}h old, {result.wallet_analysis['transaction_count']} txs")
    
    if rejected:
        print(f"\n🚫 COMMON REJECTION REASONS:")
        reason_counts = {}
        for result in rejected:
            for reason in result.rejection_reasons:
                reason_counts[reason] = reason_counts.get(reason, 0) + 1
        
        for reason, count in sorted(reason_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"  • {reason} ({count} tokens)")


# Test function
async def test_complete_filtering():
    """Test the complete filtering system with recent tokens."""
    from solders.pubkey import Pubkey
    
    # Recent tokens from your bot logs with mix of good and bad examples
    test_tokens_data = [
        # Should be good quality
        {"name": "EDGE", "symbol": "EDGE", "mint": "7emaTkEHPpiEFvpcWF5KFBSK2zy8Uo7tcKHERmJzpump", "creator": "62N1K57D37AUDGp68tnDYKPjGDsaAAtmo357nBtEtuR"},
        {"name": "LABUBU", "symbol": "LABUBU", "mint": "5FGXdHPuTUHsu8U4wa9q9hKZXF59Ftt55JDHoVu5pump", "creator": "3hah6imdTCJd63DwiykNQdotRTcnxsRe3oH8cupjLSPc"},
        {"name": "goon", "symbol": "GOON", "mint": "75SCMp36zXvLfAcN1NN7CoWsXpmcpDxs95Jh15uAKHRJ", "creator": "5JzRjmLSy5YR4ReFRpCK9k3WuToUpc7vkBhWPyy89kQ4"},
        
        # Should be rejected for various reasons
        {"name": "Ape Now, Understand Soon", "symbol": "ANUS", "mint": "HBFXSZR1sL5yifiRvYTnXjd3NXmJzQjZzHSuGaeNpump", "creator": "FnuDUsd8iiTVvVjVnRzyttpCbG6T9DoT7kcTwsWTuDFJ"},
        {"name": "kool gay bros", "symbol": "kgb", "mint": "3GnVUYHz79Q5GGHPoC2u51xK77nK5t68AqpH38T3pump", "creator": "BButLtHYHTCbEUaA1qFGKLzHJHVBZgiEUoza8mcQyTZK"},
        {"name": "wordart.fun", "symbol": "wordart", "mint": "DEPMCr7T7gvuxMRP8SDs3rnUVyNg3ABYdUhJfGezpump", "creator": "2CweXxdeD6BD6rZfWJXXXUxm7yhX57eCkQtceG9qfb45"},
    ]
    
    # Convert to TokenInfo objects
    test_tokens = []
    for data in test_tokens_data:
        token_info = TokenInfo(
            name=data["name"],
            symbol=data["symbol"],
            uri="https://example.com/metadata.json",
            mint=Pubkey.from_string(data["mint"]),
            bonding_curve=Pubkey.from_string("11111111111111111111111111111111"),
            associated_bonding_curve=Pubkey.from_string("11111111111111111111111111111111"),
            user=Pubkey.from_string(data["creator"]),
            creator=Pubkey.from_string(data["creator"]),
            creator_vault=Pubkey.from_string("11111111111111111111111111111111"),
            signature="dummy_signature"
        )
        test_tokens.append(token_info)
    
    print("🧪 Complete Token Filtering Test")
    print("=" * 60)
    
    # Configure filtering (relaxed settings for demo)
    config = TokenFilterConfig(
        min_wallet_age_minutes=5,  # Relaxed for demo
        min_wallet_transactions=3,
        min_liquidity_sol=0.1,  # Lower threshold for demo
        max_liquidity_sol=50.0
    )
    
    # Filter and rank tokens
    approved, rejected = await filter_and_rank_tokens(test_tokens, config)
    
    # Print summary
    print_filter_summary(approved, rejected)


if __name__ == "__main__":
    asyncio.run(test_complete_filtering())