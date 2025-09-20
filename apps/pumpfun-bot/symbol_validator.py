"""
Symbol Validation Module for Pump.fun Signal Alert Bot
Validates token symbols to filter out invalid or suspicious symbols.
"""

import re
from typing import Optional


def is_symbol_valid(symbol: str) -> bool:
    """
    Validate if a token symbol meets strict criteria.
    
    Args:
        symbol: The token symbol to validate
        
    Returns:
        bool: True if symbol is valid (2-6 uppercase letters A-Z only), False otherwise
    
    Validation Rules:
        - Must be 2-6 characters long
        - Must contain only uppercase letters A-Z
        - No numbers, lowercase letters, symbols, or emoji
        - Returns False for None or empty strings
    """
    # Check for None or empty string
    if not symbol:
        return False
    
    # Use regex to validate: exactly 2-6 uppercase letters A-Z only
    pattern = r'^[A-Z]{2,6}$'
    return bool(re.match(pattern, symbol))


def get_symbol_issues(symbol: str) -> list[str]:
    """
    Get a list of issues with a symbol for debugging/logging purposes.
    
    Args:
        symbol: The token symbol to analyze
        
    Returns:
        list[str]: List of issues found with the symbol
    """
    issues = []
    
    if not symbol:
        issues.append("Symbol is None or empty")
        return issues
    
    # Check length
    if len(symbol) < 2:
        issues.append(f"Too short: {len(symbol)} characters (minimum: 2)")
    elif len(symbol) > 6:
        issues.append(f"Too long: {len(symbol)} characters (maximum: 6)")
    
    # Check for non-letter characters
    if not symbol.isalpha():
        non_letters = [char for char in symbol if not char.isalpha()]
        issues.append(f"Contains non-letters: {', '.join(set(non_letters))}")
    
    # Check for lowercase letters
    if any(char.islower() for char in symbol):
        lowercase_chars = [char for char in symbol if char.islower()]
        issues.append(f"Contains lowercase: {', '.join(set(lowercase_chars))}")
    
    # Check if it's not all uppercase letters (catches edge cases)
    if symbol.isalpha() and symbol != symbol.upper():
        issues.append("Not all uppercase letters")
    
    return issues


def validate_symbol_with_details(symbol: str) -> dict:
    """
    Validate symbol and return detailed results for logging.
    
    Args:
        symbol: The token symbol to validate
        
    Returns:
        dict: Validation results with details
    """
    is_valid = is_symbol_valid(symbol)
    issues = get_symbol_issues(symbol) if not is_valid else []
    
    return {
        "symbol": symbol,
        "is_valid": is_valid,
        "length": len(symbol) if symbol else 0,
        "issues": issues,
        "reason": "Valid symbol" if is_valid else "; ".join(issues)
    }


# Test function to demonstrate validation
def test_symbol_validation():
    """Test the symbol validation with various examples."""
    
    # Test cases from your bot logs and edge cases
    test_symbols = [
        # Valid symbols
        "BTC", "ETH", "SOL", "USDC", "DOGE", "PEPE",
        
        # Invalid - too short/long
        "A", "TOOLONG", "VERYLONGSYMBOL",
        
        # Invalid - contains numbers
        "BTC1", "ETH2", "DOGE69", "ABC123",
        
        # Invalid - contains lowercase
        "btc", "Eth", "DoGe", "PePe",
        
        # Invalid - contains symbols/special chars
        "BTC$", "ETH-", "DOGE!", "BTC.USD", "SOL/USDC",
        
        # Invalid - contains emoji or unicode
        "BTC🚀", "DOGE💎", "MOON🌙",
        
        # Edge cases
        "", None, "  ", "AA", "AAAAAA", "AAAAAAA",
        
        # Real examples from your logs
        "Frappucino", "APU", "Hard", "mart", "TDOGE", "MEOW", "THE", "LPO",
        "DOGE2", "WISK", "PUMBA", "EMM", "LOOT", "PSR", "MIT", "PILL",
        "FIN", "CHINAFANS", "URINAL3000", "PUMPKIUS", "MEMENATION",
        "PUMPSTIEN", "PILLBILL"
    ]
    
    print("🧪 Symbol Validation Test Results")
    print("=" * 50)
    
    valid_count = 0
    invalid_count = 0
    
    for symbol in test_symbols:
        result = validate_symbol_with_details(symbol)
        status = "✅ VALID" if result["is_valid"] else "❌ INVALID"
        
        if result["is_valid"]:
            valid_count += 1
            print(f"{status:10} | {symbol or 'None':15} | Length: {result['length']}")
        else:
            invalid_count += 1
            print(f"{status:10} | {symbol or 'None':15} | {result['reason']}")
    
    print("\n" + "=" * 50)
    print(f"📊 Summary: {valid_count} valid, {invalid_count} invalid")
    
    # Test specific examples from your bot
    print("\n🔍 Recent Token Symbols from Your Bot:")
    recent_symbols = ["Frappucino", "APU", "MEOW", "EMM", "PILL", "MIT", "THE", "LPO"]
    
    for symbol in recent_symbols:
        result = validate_symbol_with_details(symbol)
        status = "✅" if result["is_valid"] else "❌"
        print(f"  {status} {symbol:12} | {result['reason']}")


if __name__ == "__main__":
    test_symbol_validation()