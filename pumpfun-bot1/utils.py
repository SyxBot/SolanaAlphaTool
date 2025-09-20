"""
Utilities Module for Pump.fun Signal Alert Bot
Centralized helper functions for logging, API calls, and configuration management.
"""

import os
import time
import json
import logging
import requests
from datetime import datetime
from typing import Any, Dict, Optional, List, Union
from functools import wraps
import asyncio

# Configure logging format from environment
def setup_logging():
    """Setup standardized logging configuration."""
    log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
    bot_id = os.getenv('BOT_IDENTIFIER', 'BOT1')
    
    # Create custom formatter
    class BotFormatter(logging.Formatter):
        def format(self, record):
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            return f"[{timestamp}] {bot_id}: {record.getMessage()}"
    
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('pump_bot.log', mode='a')
        ]
    )
    
    # Apply custom formatter to all handlers
    for handler in logging.getLogger().handlers:
        handler.setFormatter(BotFormatter())


def log_event(msg: str, level: str = 'info') -> None:
    """
    Log messages with standardized format and optional memory API reporting.
    
    Args:
        msg: Message to log
        level: Log level ('info', 'warning', 'error', 'debug')
    """
    logger = logging.getLogger(__name__)
    
    # Log locally
    log_func = getattr(logger, level.lower(), logger.info)
    log_func(msg)
    
    # Optionally log to memory API
    if os.getenv('LOG_TO_MEMORY_API', 'false').lower() == 'true':
        try:
            log_data = {
                'timestamp': time.time(),
                'bot_id': os.getenv('BOT_IDENTIFIER', 'BOT1'),
                'level': level.upper(),
                'message': msg
            }
            
            base_url = os.getenv('MEMORY_API_BASE_URL', 'https://pump-memory-server.replit.app')
            endpoint = os.getenv('MEMORY_LOGS_ENDPOINT', '/logs')
            
            # Use fire-and-forget for log posting to avoid blocking
            asyncio.create_task(_post_log_async(f"{base_url}{endpoint}", log_data))
            
        except Exception as e:
            # Don't let log posting failures break the main flow
            pass


async def _post_log_async(url: str, data: Dict[str, Any]) -> None:
    """Async helper to post logs to memory API without blocking."""
    try:
        timeout = int(os.getenv('DEFAULT_REQUEST_TIMEOUT', '5'))
        async with asyncio.timeout(timeout):
            # Use aiohttp if available, otherwise skip
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data) as response:
                    pass  # Fire and forget
    except Exception:
        pass  # Silent failure for logging


def get_config(key: str, default: Any = None, cast_type: type = str) -> Any:
    """
    Get configuration value from environment with type casting.
    
    Args:
        key: Environment variable key
        default: Default value if key not found
        cast_type: Type to cast the value to (str, int, float, bool)
        
    Returns:
        Configuration value cast to specified type
    """
    value = os.getenv(key, default)
    
    if value is None:
        return None
    
    if cast_type == bool:
        return str(value).lower() in ('true', '1', 'yes', 'on')
    elif cast_type in (int, float):
        try:
            return cast_type(value)
        except (ValueError, TypeError):
            return default
    else:
        return cast_type(value)


def get_blocked_creators() -> set:
    """Get blocked creator addresses from environment configuration."""
    blocked_str = os.getenv('BLOCKED_CREATORS', '')
    if not blocked_str.strip():
        return set()
    
    # Split by comma and clean whitespace
    addresses = [addr.strip() for addr in blocked_str.split(',') if addr.strip()]
    return set(addresses)


def get_filtering_config() -> Dict[str, Any]:
    """Get all filtering configuration from environment."""
    return {
        'min_liquidity_sol': get_config('MIN_LIQUIDITY_SOL', 0.1, float),
        'min_wallet_age_minutes': get_config('MIN_WALLET_AGE_MINUTES', 15, int),
        'min_wallet_transactions': get_config('MIN_WALLET_TRANSACTIONS', 3, int),
        'wallet_analysis_timeout': get_config('WALLET_ANALYSIS_TIMEOUT', 5, int),
        'min_symbol_length': get_config('MIN_SYMBOL_LENGTH', 2, int),
        'max_symbol_length': get_config('MAX_SYMBOL_LENGTH', 6, int),
        'require_uppercase_symbols': get_config('REQUIRE_UPPERCASE_SYMBOLS', True, bool),
        'enable_wallet_filter': get_config('ENABLE_WALLET_FILTER', True, bool),
        'enable_symbol_filter': get_config('ENABLE_SYMBOL_FILTER', True, bool),
        'enable_liquidity_filter': get_config('ENABLE_LIQUIDITY_FILTER', True, bool),
        'enable_blocked_creator_filter': get_config('ENABLE_BLOCKED_CREATOR_FILTER', True, bool),
        'blocked_creators': get_blocked_creators()
    }


def get_quality_scoring_config() -> Dict[str, float]:
    """Get quality scoring configuration from environment."""
    return {
        'max_score': get_config('MAX_QUALITY_SCORE', 10.0, float),
        'low_liquidity_penalty': get_config('LOW_LIQUIDITY_PENALTY', 2.0, float),
        'medium_liquidity_penalty': get_config('MEDIUM_LIQUIDITY_PENALTY', 1.0, float),
        'medium_liquidity_threshold': get_config('MEDIUM_LIQUIDITY_THRESHOLD', 5.0, float)
    }


def retry_on_failure(max_retries: int = None, delay: float = None, backoff_multiplier: float = None):
    """
    Decorator for retrying functions on failure with exponential backoff.
    
    Args:
        max_retries: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        backoff_multiplier: Multiplier for exponential backoff
    """
    if max_retries is None:
        max_retries = get_config('MAX_RETRIES', 3, int)
    if delay is None:
        delay = get_config('RETRY_DELAY_SECONDS', 1.0, float)
    if backoff_multiplier is None:
        backoff_multiplier = get_config('BACKOFF_MULTIPLIER', 2.0, float)
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    
                    if attempt < max_retries:
                        log_event(f"Attempt {attempt + 1} failed for {func.__name__}: {e}. Retrying in {current_delay}s...", 'warning')
                        time.sleep(current_delay)
                        current_delay *= backoff_multiplier
                    else:
                        log_event(f"All {max_retries + 1} attempts failed for {func.__name__}: {e}", 'error')
            
            raise last_exception
        
        return wrapper
    return decorator


@retry_on_failure()
def post_to_memory(endpoint: str, data: Dict[str, Any], retries: int = None) -> bool:
    """
    Post data to the shared memory API with retries and standardized error handling.
    
    Args:
        endpoint: API endpoint path (e.g., '/memory/append_token')
        data: Data to post as JSON
        retries: Number of retries (uses config default if None)
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        base_url = get_config('MEMORY_API_BASE_URL', 'https://pump-memory-server.replit.app')
        timeout = get_config('MEMORY_API_TIMEOUT', 10, int)
        user_agent = get_config('MEMORY_API_USER_AGENT', 'PumpBot-Reporter/1.0')
        
        url = f"{base_url}{endpoint}"
        
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': user_agent
        }
        
        log_event(f"Posting to memory API: {endpoint}", 'debug')
        
        response = requests.post(
            url,
            json=data,
            headers=headers,
            timeout=timeout
        )
        
        if response.status_code == 200:
            log_event(f"Successfully posted to {endpoint}")
            return True
        else:
            log_event(f"Memory API returned status {response.status_code} for {endpoint}: {response.text}", 'warning')
            return False
            
    except requests.exceptions.RequestException as e:
        log_event(f"Network error posting to {endpoint}: {e}", 'error')
        raise
    except Exception as e:
        log_event(f"Error posting to {endpoint}: {e}", 'error')
        raise


@retry_on_failure()
def get_from_memory(endpoint: str) -> Optional[Dict[str, Any]]:
    """
    Get data from the shared memory API with retries.
    
    Args:
        endpoint: API endpoint path (e.g., '/memory/wallet_reputation/address')
        
    Returns:
        dict: Response data or None if not found/error
    """
    try:
        base_url = get_config('MEMORY_API_BASE_URL', 'https://pump-memory-server.replit.app')
        timeout = get_config('MEMORY_API_TIMEOUT', 10, int)
        user_agent = get_config('MEMORY_API_USER_AGENT', 'PumpBot-Reporter/1.0')
        
        url = f"{base_url}{endpoint}"
        
        headers = {
            'User-Agent': user_agent
        }
        
        log_event(f"Getting from memory API: {endpoint}", 'debug')
        
        response = requests.get(
            url,
            headers=headers,
            timeout=timeout
        )
        
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            log_event(f"Data not found at {endpoint}", 'debug')
            return None
        else:
            log_event(f"Memory API returned status {response.status_code} for {endpoint}", 'warning')
            return None
            
    except requests.exceptions.RequestException as e:
        log_event(f"Network error getting from {endpoint}: {e}", 'error')
        raise
    except Exception as e:
        log_event(f"Error getting from {endpoint}: {e}", 'error')
        raise


def ping_memory_server() -> bool:
    """
    Test connection to memory server.
    
    Returns:
        bool: True if server is reachable, False otherwise
    """
    try:
        base_url = get_config('MEMORY_API_BASE_URL', 'https://pump-memory-server.replit.app')
        timeout = get_config('DEFAULT_REQUEST_TIMEOUT', 5, int)
        
        response = requests.get(f"{base_url}/health", timeout=timeout)
        
        if response.status_code == 200:
            log_event("Memory server is reachable")
            return True
        else:
            log_event(f"Memory server health check failed: {response.status_code}", 'warning')
            return False
            
    except requests.exceptions.RequestException as e:
        log_event(f"Cannot reach memory server: {e}", 'warning')
        return False
    except Exception as e:
        log_event(f"Error pinging memory server: {e}", 'error')
        return False


def calculate_quality_score(filter_results: Dict[str, Any], liquidity_sol: float = None) -> float:
    """
    Calculate quality score based on filter results and liquidity.
    
    Args:
        filter_results: Results from filtering checks
        liquidity_sol: Token liquidity in SOL
        
    Returns:
        float: Quality score (0-10)
    """
    config = get_quality_scoring_config()
    
    if not filter_results.get('should_alert', False):
        return 0.0
    
    score = config['max_score']  # Start with perfect score
    
    # Apply liquidity penalties
    if liquidity_sol is not None:
        if liquidity_sol < 1.0:
            score -= config['low_liquidity_penalty']
        elif liquidity_sol < config['medium_liquidity_threshold']:
            score -= config['medium_liquidity_penalty']
    
    return max(0.0, min(config['max_score'], score))


def format_token_data(token_info, should_alert: bool, filter_details: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Format token data for memory reporting with standardized structure.
    
    Args:
        token_info: TokenInfo object from pump monitor
        should_alert: Whether token should trigger alert
        filter_details: Detailed filter results
        
    Returns:
        dict: Formatted token data for memory API
    """
    liquidity_sol = None
    quality_score = 0.0
    filter_reasons = []
    
    if filter_details:
        liquidity_sol = filter_details.get('details', {}).get('liquidity_sol')
        filter_reasons = filter_details.get('rejection_reasons', [])
        quality_score = calculate_quality_score(filter_details, liquidity_sol)
    
    return {
        'mint': str(token_info.mint),
        'symbol': token_info.symbol,
        'creator': str(token_info.creator),
        'name': token_info.name,
        'alerted_by': get_config('BOT_IDENTIFIER', 'BOT1'),
        'alerted_at': time.time(),
        'status': 'alerted' if should_alert else 'filtered',
        'liquidity_sol': liquidity_sol,
        'quality_score': quality_score,
        'filter_reasons': filter_reasons
    }


def format_wallet_intel(address: str, reputation: str, reason: str, **kwargs) -> Dict[str, Any]:
    """
    Format wallet intelligence data for memory reporting.
    
    Args:
        address: Wallet address
        reputation: Reputation level ('trusted', 'blocked', 'suspicious')
        reason: Reason for reputation
        **kwargs: Additional metadata
        
    Returns:
        dict: Formatted wallet intel for memory API
    """
    return {
        'address': address,
        'reputation': reputation,
        'reason': reason,
        'reported_by': get_config('BOT_IDENTIFIER', 'BOT1'),
        'reported_at': time.time(),
        'token_count': kwargs.get('token_count'),
        'success_rate': kwargs.get('success_rate')
    }


def get_rpc_endpoints() -> Dict[str, str]:
    """Get RPC endpoints from environment configuration."""
    helius_key = os.getenv("HELIUS_API_KEY")
    
    if helius_key:
        return {
            'http': f"https://mainnet.helius-rpc.com/?api-key={helius_key}",
            'ws': f"wss://mainnet.helius-rpc.com/?api-key={helius_key}"
        }
    else:
        return {
            'http': "https://api.mainnet-beta.solana.com",
            'ws': "wss://api.mainnet-beta.solana.com"
        }


def validate_environment() -> bool:
    """
    Validate that all required environment variables are set.
    
    Returns:
        bool: True if environment is valid, False otherwise
    """
    required_vars = []
    optional_vars = [
        'HELIUS_API_KEY',
        'MEMORY_API_BASE_URL',
        'TELEGRAM_BOT_TOKEN',
        'DISCORD_WEBHOOK_URL'
    ]
    
    missing_required = []
    for var in required_vars:
        if not os.getenv(var):
            missing_required.append(var)
    
    if missing_required:
        log_event(f"Missing required environment variables: {', '.join(missing_required)}", 'error')
        return False
    
    log_event("Environment validation passed")
    return True


def get_bot_info() -> Dict[str, str]:
    """Get bot identification information from environment."""
    return {
        'identifier': get_config('BOT_IDENTIFIER', 'BOT1'),
        'version': get_config('BOT_VERSION', '1.0'),
        'user_agent': get_config('MEMORY_API_USER_AGENT', 'PumpBot-Reporter/1.0')
    }


# Initialize logging when module is imported
setup_logging()

# Log startup
bot_info = get_bot_info()
log_event(f"Utils module initialized - {bot_info['identifier']} v{bot_info['version']}")


if __name__ == "__main__":
    # Test utilities
    print("🧪 Testing Utils Module")
    print("=" * 40)
    
    # Test configuration loading
    print("📋 Configuration Test:")
    config = get_filtering_config()
    print(f"  Min liquidity: {config['min_liquidity_sol']} SOL")
    print(f"  Blocked creators: {len(config['blocked_creators'])}")
    
    # Test memory server connection
    print("\n📡 Memory Server Test:")
    is_reachable = ping_memory_server()
    print(f"  Server reachable: {is_reachable}")
    
    # Test logging
    print("\n📝 Logging Test:")
    log_event("Test info message", 'info')
    log_event("Test warning message", 'warning')
    
    print("\n✅ Utils module test completed")