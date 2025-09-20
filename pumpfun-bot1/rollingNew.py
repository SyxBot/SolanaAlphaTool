"""
Rolling stats module for tracking per-mint activity over 10-minute windows.
Uses dict + deque for efficient time-based pruning without external dependencies.
"""

from collections import deque, defaultdict
import statistics
import time


class RollingStats:
    def __init__(self, window_ms=600000):  # 10 minutes default
        self.window_ms = window_ms
        self.mint_data = defaultdict(lambda: {
            'swaps': deque(),
            'lp_additions': deque()
        })
    
    def _prune_old_entries(self, mint):
        """Remove entries older than window_ms"""
        current_time = int(time.time() * 1000)
        cutoff_time = current_time - self.window_ms
        
        # Prune swaps
        while (self.mint_data[mint]['swaps'] and 
               self.mint_data[mint]['swaps'][0]['ms'] < cutoff_time):
            self.mint_data[mint]['swaps'].popleft()
        
        # Prune LP additions
        while (self.mint_data[mint]['lp_additions'] and 
               self.mint_data[mint]['lp_additions'][0]['ms'] < cutoff_time):
            self.mint_data[mint]['lp_additions'].popleft()
    
    def record_swap(self, mint, wallet, usd, is_buy, ms, is_mev=False):
        """Record a swap transaction"""
        self._prune_old_entries(mint)
        
        swap_data = {
            'wallet': wallet,
            'usd': usd,
            'is_buy': is_buy,
            'ms': ms,
            'is_mev': is_mev
        }
        
        self.mint_data[mint]['swaps'].append(swap_data)
    
    def record_lp(self, mint, usd, ms):
        """Record a liquidity provision"""
        self._prune_old_entries(mint)
        
        lp_data = {
            'usd': usd,
            'ms': ms
        }
        
        self.mint_data[mint]['lp_additions'].append(lp_data)
    
    def get_stats(self, mint):
        """Get comprehensive stats for a mint over the rolling window"""
        self._prune_old_entries(mint)
        
        swaps = list(self.mint_data[mint]['swaps'])
        lp_additions = list(self.mint_data[mint]['lp_additions'])
        
        if not swaps and not lp_additions:
            return {
                'unique_buyers': 0,
                'tx_per_min': 0.0,
                'median_trade_usd': 0.0,
                'net_buy_usd': 0.0,
                'lp_usd': 0.0,
                'mev_share': 0.0
            }
        
        # Calculate unique buyers (only buy transactions)
        unique_buyers = len(set(swap['wallet'] for swap in swaps if swap['is_buy']))
        
        # Calculate transactions per minute
        total_txs = len(swaps) + len(lp_additions)
        window_minutes = self.window_ms / 60000
        tx_per_min = total_txs / window_minutes if window_minutes > 0 else 0.0
        
        # Calculate median trade USD (swaps only)
        trade_amounts = [swap['usd'] for swap in swaps]
        median_trade_usd = statistics.median(trade_amounts) if trade_amounts else 0.0
        
        # Calculate net buy USD
        buy_usd = sum(swap['usd'] for swap in swaps if swap['is_buy'])
        sell_usd = sum(swap['usd'] for swap in swaps if not swap['is_buy'])
        net_buy_usd = buy_usd - sell_usd
        
        # Calculate total LP USD
        lp_usd = sum(lp['usd'] for lp in lp_additions)
        
        # Calculate MEV share
        total_swap_usd = sum(swap['usd'] for swap in swaps)
        mev_usd = sum(swap['usd'] for swap in swaps if swap['is_mev'])
        mev_share = (mev_usd / total_swap_usd) if total_swap_usd > 0 else 0.0
        
        return {
            'unique_buyers': unique_buyers,
            'tx_per_min': round(tx_per_min, 2),
            'median_trade_usd': round(median_trade_usd, 2),
            'net_buy_usd': round(net_buy_usd, 2),
            'lp_usd': round(lp_usd, 2),
            'mev_share': round(mev_share, 3)
        }


# Global instance for easy access
rolling_stats = RollingStats()

def record_swap(mint, wallet, usd, is_buy, ms, is_mev=False):
    """Global function for recording swaps"""
    return rolling_stats.record_swap(mint, wallet, usd, is_buy, ms, is_mev)

def record_lp(mint, usd, ms):
    """Global function for recording LP additions"""
    return rolling_stats.record_lp(mint, usd, ms)

def get_stats(mint):
    """Global function for getting stats"""
    return rolling_stats.get_stats(mint)