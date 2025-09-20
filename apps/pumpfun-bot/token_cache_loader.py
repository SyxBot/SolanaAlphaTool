"""
Token Cache Input Module for Bot 2 (Rescanner)
Loads previously alerted tokens from Bot 1 for volume/price/holder tracking.
"""

import json
import os
import time
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def load_alerted_tokens(cache_file: str = "alerted_tokens.json") -> List[Dict[str, Any]]:
    """
    Load tokens previously filtered by Bot 1 that are ready for rescanning.
    
    Filters for:
    - status == "untracked"
    - alerted_at older than 15 minutes
    
    Args:
        cache_file: Path to the JSON file containing alerted tokens
        
    Returns:
        List[Dict]: Tokens ready for rescanning
    """
    try:
        # Check if file exists
        if not os.path.exists(cache_file):
            logger.info(f"Cache file {cache_file} not found - creating empty cache")
            return []
        
        # Load the JSON file
        with open(cache_file, 'r') as f:
            all_tokens = json.load(f)
        
        if not isinstance(all_tokens, list):
            logger.error(f"Invalid cache file format - expected list, got {type(all_tokens)}")
            return []
        
        # Current timestamp for age filtering
        current_time = int(time.time())
        fifteen_minutes_ago = current_time - (15 * 60)  # 15 minutes in seconds
        
        # Filter tokens for rescanning
        tokens_to_rescan = []
        
        for token in all_tokens:
            # Validate required fields
            if not isinstance(token, dict):
                logger.warning(f"Skipping invalid token entry: {token}")
                continue
                
            required_fields = ['mint', 'creator', 'symbol', 'alerted_at', 'status']
            if not all(field in token for field in required_fields):
                missing_fields = [field for field in required_fields if field not in token]
                logger.warning(f"Skipping token with missing fields {missing_fields}: {token.get('symbol', 'Unknown')}")
                continue
            
            # Filter criteria
            status = token.get('status')
            alerted_at = token.get('alerted_at')
            
            # Check status
            if status != "untracked":
                continue
            
            # Check age (must be older than 15 minutes)
            if not isinstance(alerted_at, (int, float)):
                logger.warning(f"Invalid alerted_at timestamp for {token.get('symbol')}: {alerted_at}")
                continue
                
            if alerted_at > fifteen_minutes_ago:
                # Token is too recent, skip
                age_minutes = (current_time - alerted_at) / 60
                logger.debug(f"Token {token.get('symbol')} is only {age_minutes:.1f} minutes old - skipping")
                continue
            
            # Token passes all filters
            tokens_to_rescan.append(token)
        
        logger.info(f"Loaded {len(tokens_to_rescan)} tokens ready for rescanning from {len(all_tokens)} total")
        
        return tokens_to_rescan
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON from {cache_file}: {e}")
        return []
    except Exception as e:
        logger.error(f"Error loading alerted tokens from {cache_file}: {e}")
        return []


def get_token_age_minutes(token: Dict[str, Any]) -> float:
    """
    Get the age of a token in minutes since it was alerted.
    
    Args:
        token: Token dictionary with 'alerted_at' timestamp
        
    Returns:
        float: Age in minutes
    """
    try:
        alerted_at = token.get('alerted_at')
        if not isinstance(alerted_at, (int, float)):
            return 0.0
        
        current_time = int(time.time())
        age_seconds = current_time - alerted_at
        return age_seconds / 60.0
        
    except Exception:
        return 0.0


def update_token_status(cache_file: str, mint: str, new_status: str) -> bool:
    """
    Update the status of a specific token in the cache file.
    
    Args:
        cache_file: Path to the JSON cache file
        mint: Token mint address to update
        new_status: New status value ("tracking", "completed", etc.)
        
    Returns:
        bool: True if update successful, False otherwise
    """
    try:
        # Load current cache
        if not os.path.exists(cache_file):
            logger.warning(f"Cache file {cache_file} not found for status update")
            return False
        
        with open(cache_file, 'r') as f:
            all_tokens = json.load(f)
        
        # Find and update the token
        updated = False
        for token in all_tokens:
            if token.get('mint') == mint:
                old_status = token.get('status')
                token['status'] = new_status
                token['last_updated'] = int(time.time())
                logger.info(f"Updated token {token.get('symbol', mint)} status: {old_status} → {new_status}")
                updated = True
                break
        
        if not updated:
            logger.warning(f"Token with mint {mint} not found in cache for status update")
            return False
        
        # Save updated cache
        with open(cache_file, 'w') as f:
            json.dump(all_tokens, f, indent=2)
        
        return True
        
    except Exception as e:
        logger.error(f"Error updating token status in {cache_file}: {e}")
        return False


def add_alerted_token(cache_file: str, token_data: Dict[str, Any]) -> bool:
    """
    Add a new token to the alerted tokens cache (for Bot 1 integration).
    
    Args:
        cache_file: Path to the JSON cache file
        token_data: Token information to add
        
    Returns:
        bool: True if added successfully, False otherwise
    """
    try:
        # Load existing cache or create empty list
        if os.path.exists(cache_file):
            with open(cache_file, 'r') as f:
                all_tokens = json.load(f)
        else:
            all_tokens = []
        
        # Ensure required fields
        required_fields = ['mint', 'creator', 'symbol']
        if not all(field in token_data for field in required_fields):
            logger.error(f"Missing required fields for token addition: {token_data}")
            return False
        
        # Add metadata
        token_entry = {
            'mint': token_data['mint'],
            'creator': token_data['creator'],
            'symbol': token_data['symbol'],
            'name': token_data.get('name', token_data['symbol']),
            'alerted_at': int(time.time()),
            'status': 'untracked',
            'added_by': 'bot_1'
        }
        
        # Check for duplicates
        for existing_token in all_tokens:
            if existing_token.get('mint') == token_entry['mint']:
                logger.info(f"Token {token_entry['symbol']} already in cache - skipping")
                return True
        
        # Add new token
        all_tokens.append(token_entry)
        
        # Save updated cache
        with open(cache_file, 'w') as f:
            json.dump(all_tokens, f, indent=2)
        
        logger.info(f"Added token {token_entry['symbol']} to alerted tokens cache")
        return True
        
    except Exception as e:
        logger.error(f"Error adding token to cache {cache_file}: {e}")
        return False


def get_cache_statistics(cache_file: str = "alerted_tokens.json") -> Dict[str, Any]:
    """
    Get statistics about the alerted tokens cache.
    
    Args:
        cache_file: Path to the JSON cache file
        
    Returns:
        dict: Statistics about cache contents
    """
    try:
        if not os.path.exists(cache_file):
            return {
                'total_tokens': 0,
                'untracked': 0,
                'tracking': 0,
                'completed': 0,
                'ready_for_rescan': 0,
                'cache_exists': False
            }
        
        with open(cache_file, 'r') as f:
            all_tokens = json.load(f)
        
        # Count by status
        status_counts = {}
        current_time = int(time.time())
        fifteen_minutes_ago = current_time - (15 * 60)
        ready_for_rescan = 0
        
        for token in all_tokens:
            status = token.get('status', 'unknown')
            status_counts[status] = status_counts.get(status, 0) + 1
            
            # Count tokens ready for rescanning
            if (status == 'untracked' and 
                isinstance(token.get('alerted_at'), (int, float)) and 
                token.get('alerted_at') <= fifteen_minutes_ago):
                ready_for_rescan += 1
        
        return {
            'total_tokens': len(all_tokens),
            'untracked': status_counts.get('untracked', 0),
            'tracking': status_counts.get('tracking', 0),
            'completed': status_counts.get('completed', 0),
            'ready_for_rescan': ready_for_rescan,
            'cache_exists': True,
            'status_breakdown': status_counts
        }
        
    except Exception as e:
        logger.error(f"Error getting cache statistics: {e}")
        return {
            'total_tokens': 0,
            'error': str(e),
            'cache_exists': False
        }


# Example usage and testing
def create_sample_cache(cache_file: str = "alerted_tokens.json") -> None:
    """
    Create a sample cache file for testing purposes.
    """
    sample_tokens = [
        {
            "mint": "7emaTkEHPpiEFvpcWF5KFBSK2zy8Uo7tcKHERmJzpump",
            "creator": "62N1K57D37AUDGp68tnDYKPjGDsaAAtmo357nBtEtuR",
            "symbol": "EDGE",
            "name": "EDGE",
            "alerted_at": int(time.time()) - 1200,  # 20 minutes ago
            "status": "untracked"
        },
        {
            "mint": "5FGXdHPuTUHsu8U4wa9q9hKZXF59Ftt55JDHoVu5pump",
            "creator": "3hah6imdTCJd63DwiykNQdotRTcnxsRe3oH8cupjLSPc",
            "symbol": "LABUBU",
            "name": "LABUBU",
            "alerted_at": int(time.time()) - 600,  # 10 minutes ago (too recent)
            "status": "untracked"
        },
        {
            "mint": "9RSu97yfR6bjdLYgz7oSeYxZKqVRJfTgw18sYobpump",
            "creator": "ArEhrpdiHoNJCTiuwHPLdvknoshmhKs25ozpmf2hEUr1",
            "symbol": "WAM",
            "name": "WAM",
            "alerted_at": int(time.time()) - 1800,  # 30 minutes ago
            "status": "tracking"  # Already being tracked
        },
        {
            "mint": "3vF5hcm2kkVns3xiwRwQJTDCPVtd9vVuRd9zoKDmpump",
            "creator": "5E3UKwJBpegcBS45LiLw5T6np34ooKvGg4pviJ4Drsn",
            "symbol": "PRB",
            "name": "PutinRidingBear",
            "alerted_at": int(time.time()) - 2400,  # 40 minutes ago
            "status": "untracked"
        }
    ]
    
    with open(cache_file, 'w') as f:
        json.dump(sample_tokens, f, indent=2)
    
    logger.info(f"Created sample cache file: {cache_file}")


def test_token_cache_loader():
    """
    Test the token cache loading functionality.
    """
    print("🧪 Token Cache Loader Test")
    print("=" * 40)
    
    cache_file = "test_alerted_tokens.json"
    
    # Create sample cache
    create_sample_cache(cache_file)
    
    # Test loading
    tokens_to_rescan = load_alerted_tokens(cache_file)
    
    print(f"\n📊 Results:")
    print(f"Tokens ready for rescanning: {len(tokens_to_rescan)}")
    
    for token in tokens_to_rescan:
        age_minutes = get_token_age_minutes(token)
        print(f"  • {token['symbol']} ({token['name']}) - {age_minutes:.1f} minutes old")
    
    # Test statistics
    stats = get_cache_statistics(cache_file)
    print(f"\n📈 Cache Statistics:")
    print(f"  Total tokens: {stats['total_tokens']}")
    print(f"  Untracked: {stats['untracked']}")
    print(f"  Ready for rescan: {stats['ready_for_rescan']}")
    print(f"  Status breakdown: {stats['status_breakdown']}")
    
    # Test status update
    if tokens_to_rescan:
        test_token = tokens_to_rescan[0]
        print(f"\n🔄 Testing status update for {test_token['symbol']}")
        success = update_token_status(cache_file, test_token['mint'], 'tracking')
        print(f"  Update successful: {success}")
    
    # Clean up
    if os.path.exists(cache_file):
        os.remove(cache_file)
        print(f"\n🧹 Cleaned up test file: {cache_file}")


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Run test
    test_token_cache_loader()