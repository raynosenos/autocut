"""
Profit Tracker Module - Track daily P&L and growth
"""
import json
import os
from datetime import datetime, date
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)

class ProfitTracker:
    """Track profit/loss history for growth analysis"""
    
    HISTORY_FILE = "profit_history.json"
    
    def __init__(self):
        self.history: List[Dict] = []
        self.initial_balance: float = 0
        self.current_balance: float = 0
        # Win rate tracking
        self.total_wins: int = 0
        self.total_losses: int = 0
        self.total_trades: int = 0
        self._load_history()
    
    def _get_history_path(self) -> str:
        """Get path to history file"""
        return os.path.join(os.path.dirname(__file__), self.HISTORY_FILE)
    
    def _load_history(self):
        """Load profit history from file"""
        try:
            path = self._get_history_path()
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.history = data.get('history', [])
                    self.initial_balance = data.get('initial_balance', 0)
                    # Load win rate data
                    self.total_wins = data.get('total_wins', 0)
                    self.total_losses = data.get('total_losses', 0)
                    self.total_trades = data.get('total_trades', 0)
                    logger.info(f"Loaded {len(self.history)} profit entries, {self.total_trades} trades")
        except Exception as e:
            logger.warning(f"Could not load profit history: {e}")
            self.history = []
    
    def _save_history(self):
        """Save profit history to file"""
        try:
            path = self._get_history_path()
            data = {
                'initial_balance': self.initial_balance,
                'history': self.history[-365:],  # Keep last year
                'total_wins': self.total_wins,
                'total_losses': self.total_losses,
                'total_trades': self.total_trades
            }
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning(f"Could not save profit history: {e}")
    
    def set_initial_balance(self, balance: float):
        """Set initial balance for growth calculation"""
        if self.initial_balance == 0:
            self.initial_balance = balance
            self._save_history()
            logger.info(f"Initial balance set to: ${balance}")
    
    def update_balance(self, balance: float, equity: float = None):
        """Update current balance and record daily snapshot"""
        self.current_balance = balance
        today = date.today().isoformat()
        
        # Check if we already have an entry for today
        today_entry = next((e for e in self.history if e['date'] == today), None)
        
        if today_entry:
            # Update existing entry
            today_entry['balance'] = balance
            today_entry['equity'] = equity or balance
            today_entry['updated_at'] = datetime.now().isoformat()
        else:
            # Create new entry
            self.history.append({
                'date': today,
                'balance': balance,
                'equity': equity or balance,
                'profit_day': 0,  # Will be calculated
                'trades_count': 0,
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            })
        
        # Calculate daily profit
        self._calculate_daily_profits()
        self._save_history()
    
    def record_trade(self, profit: float):
        """Record a completed trade profit/loss"""
        today = date.today().isoformat()
        
        # Track win/loss for win rate
        self.total_trades += 1
        if profit >= 0:
            self.total_wins += 1
        else:
            self.total_losses += 1
        
        # Find or create today's entry
        today_entry = next((e for e in self.history if e['date'] == today), None)
        
        if today_entry:
            today_entry['profit_day'] = today_entry.get('profit_day', 0) + profit
            today_entry['trades_count'] = today_entry.get('trades_count', 0) + 1
            today_entry['wins'] = today_entry.get('wins', 0) + (1 if profit >= 0 else 0)
            today_entry['losses'] = today_entry.get('losses', 0) + (1 if profit < 0 else 0)
            today_entry['updated_at'] = datetime.now().isoformat()
        else:
            self.history.append({
                'date': today,
                'balance': self.current_balance,
                'equity': self.current_balance,
                'profit_day': profit,
                'trades_count': 1,
                'wins': 1 if profit >= 0 else 0,
                'losses': 1 if profit < 0 else 0,
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            })
        
        win_rate = (self.total_wins / self.total_trades * 100) if self.total_trades > 0 else 0
        self._save_history()
        logger.info(f"Recorded trade: ${profit:.2f} | Win Rate: {win_rate:.1f}% ({self.total_wins}W/{self.total_losses}L)")
    
    def _calculate_daily_profits(self):
        """Calculate daily profit from balance changes"""
        sorted_history = sorted(self.history, key=lambda x: x['date'])
        
        for i, entry in enumerate(sorted_history):
            if i == 0:
                # First day - profit is from initial balance
                if self.initial_balance > 0:
                    entry['profit_day'] = entry['balance'] - self.initial_balance
            else:
                # Subsequent days - profit from previous day's balance
                prev_balance = sorted_history[i-1]['balance']
                entry['profit_day'] = entry['balance'] - prev_balance
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive profit statistics"""
        if not self.history:
            return {
                'initial_balance': self.initial_balance,
                'current_balance': self.current_balance,
                'total_profit': 0,
                'total_profit_percent': 0,
                'today_profit': 0,
                'yesterday_profit': 0,
                'week_profit': 0,
                'month_profit': 0,
                'total_trades': 0,
                'winning_days': 0,
                'losing_days': 0,
                'history': []
            }
        
        today = date.today().isoformat()
        sorted_history = sorted(self.history, key=lambda x: x['date'], reverse=True)
        
        # Today's profit
        today_entry = next((e for e in sorted_history if e['date'] == today), None)
        today_profit = today_entry['profit_day'] if today_entry else 0
        
        # Yesterday's profit
        yesterday_entry = sorted_history[1] if len(sorted_history) > 1 else None
        yesterday_profit = yesterday_entry['profit_day'] if yesterday_entry else 0
        
        # Week profit (last 7 days)
        week_profit = sum(e.get('profit_day', 0) for e in sorted_history[:7])
        
        # Month profit (last 30 days)
        month_profit = sum(e.get('profit_day', 0) for e in sorted_history[:30])
        
        # Total profit
        total_profit = self.current_balance - self.initial_balance if self.initial_balance > 0 else 0
        total_profit_percent = (total_profit / self.initial_balance * 100) if self.initial_balance > 0 else 0
        
        # Total trades
        total_trades = sum(e.get('trades_count', 0) for e in self.history)
        
        # Winning/losing days
        winning_days = len([e for e in self.history if e.get('profit_day', 0) > 0])
        losing_days = len([e for e in self.history if e.get('profit_day', 0) < 0])
        
        # Calculate win rate
        win_rate = (self.total_wins / self.total_trades * 100) if self.total_trades > 0 else 0
        
        return {
            'initial_balance': self.initial_balance,
            'current_balance': self.current_balance,
            'total_profit': round(total_profit, 2),
            'total_profit_percent': round(total_profit_percent, 2),
            'today_profit': round(today_profit, 2),
            'yesterday_profit': round(yesterday_profit, 2),
            'week_profit': round(week_profit, 2),
            'month_profit': round(month_profit, 2),
            'total_trades': self.total_trades,
            'total_wins': self.total_wins,
            'total_losses': self.total_losses,
            'win_rate': round(win_rate, 1),
            'winning_days': winning_days,
            'losing_days': losing_days,
            'history': sorted_history[:30]  # Last 30 days for chart
        }
    
    def get_chart_data(self, days: int = 30) -> List[Dict]:
        """Get data formatted for chart display"""
        sorted_history = sorted(self.history, key=lambda x: x['date'])
        return sorted_history[-days:]


# Singleton instance
_tracker: Optional[ProfitTracker] = None

def get_profit_tracker() -> ProfitTracker:
    """Get or create profit tracker instance"""
    global _tracker
    if _tracker is None:
        _tracker = ProfitTracker()
    return _tracker
