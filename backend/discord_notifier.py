"""
Discord Webhook Notifier - Send trade alerts to Discord
"""
import httpx
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional
import logging
import os

logger = logging.getLogger(__name__)


class DiscordNotifier:
    """Send trading alerts to Discord via webhook"""
    
    def __init__(self, webhook_url: str = None):
        self.webhook_url = webhook_url or os.getenv('DISCORD_WEBHOOK_URL', '')
        self.enabled = bool(self.webhook_url)
        
        if self.enabled:
            logger.info("Discord notifications enabled")
        else:
            logger.info("Discord notifications disabled (no webhook URL)")
    
    async def send_message(self, content: str = None, embed: Dict = None) -> bool:
        """Send a message to Discord webhook"""
        if not self.enabled:
            return False
        
        try:
            payload = {}
            if content:
                payload["content"] = content
            if embed:
                payload["embeds"] = [embed]
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.webhook_url,
                    json=payload,
                    timeout=10
                )
                
                if response.status_code in [200, 204]:
                    logger.info("Discord notification sent")
                    return True
                else:
                    logger.warning(f"Discord webhook failed: {response.status_code}")
                    return False
                    
        except Exception as e:
            logger.error(f"Discord notification error: {e}")
            return False
    
    async def notify_trade_open(self, trade_data: Dict[str, Any]):
        """Notify when a new trade is opened"""
        trade_type = trade_data.get('type', 'UNKNOWN')
        symbol = trade_data.get('symbol', 'UNKNOWN')
        volume = trade_data.get('volume', 0)
        sl = trade_data.get('sl', 0)
        tp = trade_data.get('tp', 0)
        result = trade_data.get('result', {})
        entry_price = result.get('price', 0)
        
        # Color based on trade type
        color = 0x00FF00 if trade_type == 'BUY' else 0xFF0000  # Green for BUY, Red for SELL
        
        embed = {
            "title": f"🚀 New Trade Opened",
            "description": f"**{trade_type}** {volume} lot {symbol}",
            "color": color,
            "fields": [
                {"name": "📍 Entry Price", "value": f"`{entry_price}`", "inline": True},
                {"name": "🛑 Stop Loss", "value": f"`{sl}`", "inline": True},
                {"name": "🎯 Take Profit", "value": f"`{tp}`", "inline": True},
            ],
            "footer": {"text": f"AI Trading Bot • {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"},
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self.send_message(embed=embed)
    
    async def notify_trade_close(self, close_data: Dict[str, Any]):
        """Notify when a trade is closed (TP, SL, or manual)"""
        ticket = close_data.get('ticket', 'N/A')
        profit = close_data.get('profit', 0)
        close_type = close_data.get('close_type', 'CLOSED')  # TP_HIT, SL_HIT, MANUAL
        symbol = close_data.get('symbol', 'XAUUSD')
        
        # Determine emoji and color
        if profit >= 0:
            emoji = "💰"
            color = 0x00FF00  # Green
            title = "Take Profit Hit!" if close_type == 'TP_HIT' else "Trade Closed (Profit)"
        else:
            emoji = "😢"
            color = 0xFF0000  # Red
            title = "Stop Loss Hit!" if close_type == 'SL_HIT' else "Trade Closed (Loss)"
        
        embed = {
            "title": f"{emoji} {title}",
            "description": f"Position #{ticket} closed",
            "color": color,
            "fields": [
                {"name": "💵 Profit/Loss", "value": f"`${profit:+.2f}`", "inline": True},
                {"name": "📊 Symbol", "value": f"`{symbol}`", "inline": True},
                {"name": "📋 Type", "value": f"`{close_type}`", "inline": True},
            ],
            "footer": {"text": f"AI Trading Bot • {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"},
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self.send_message(embed=embed)
    
    async def notify_auto_bep(self, bep_data: Dict[str, Any]):
        """Notify when Auto Break-Even is triggered"""
        ticket = bep_data.get('ticket', 'N/A')
        new_sl = bep_data.get('new_sl', 0)
        profit_pips = bep_data.get('profit_pips', 0)
        
        embed = {
            "title": "🔒 Auto Break-Even Triggered",
            "description": f"Position #{ticket} is now risk-free!",
            "color": 0x0099FF,  # Blue
            "fields": [
                {"name": "📍 New SL (Entry)", "value": f"`{new_sl}`", "inline": True},
                {"name": "📈 Profit", "value": f"`{profit_pips} pips`", "inline": True},
            ],
            "footer": {"text": f"AI Trading Bot • {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"},
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self.send_message(embed=embed)
    
    async def notify_dca(self, dca_data: Dict[str, Any]):
        """Notify when DCA position is added"""
        trade_type = dca_data.get('type', 'UNKNOWN')
        symbol = dca_data.get('symbol', 'UNKNOWN')
        volume = dca_data.get('volume', 0)
        position_count = dca_data.get('position_count', 0)
        pips_against = dca_data.get('pips_against', 0)
        
        embed = {
            "title": "📊 DCA Position Added",
            "description": f"Averaging down on {symbol}",
            "color": 0xFFAA00,  # Orange
            "fields": [
                {"name": "📋 Type", "value": f"`{trade_type}`", "inline": True},
                {"name": "📦 Volume", "value": f"`{volume}`", "inline": True},
                {"name": "🔢 Position #", "value": f"`{position_count}`", "inline": True},
                {"name": "📉 Pips Against", "value": f"`{pips_against}`", "inline": True},
            ],
            "footer": {"text": f"AI Trading Bot • {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"},
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self.send_message(embed=embed)
    
    async def notify_daily_summary(self, stats: Dict[str, Any]):
        """Send daily profit summary"""
        total_profit = stats.get('total_profit', 0)
        today_profit = stats.get('today_profit', 0)
        total_trades = stats.get('total_trades', 0)
        current_balance = stats.get('current_balance', 0)
        
        color = 0x00FF00 if today_profit >= 0 else 0xFF0000
        emoji = "📈" if today_profit >= 0 else "📉"
        
        embed = {
            "title": f"{emoji} Daily Summary",
            "description": f"Trading report for {datetime.now().strftime('%Y-%m-%d')}",
            "color": color,
            "fields": [
                {"name": "💵 Today's P/L", "value": f"`${today_profit:+.2f}`", "inline": True},
                {"name": "📊 Total P/L", "value": f"`${total_profit:+.2f}`", "inline": True},
                {"name": "💰 Balance", "value": f"`${current_balance:.2f}`", "inline": True},
                {"name": "🔢 Total Trades", "value": f"`{total_trades}`", "inline": True},
            ],
            "footer": {"text": f"AI Trading Bot • Daily Report"},
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self.send_message(embed=embed)


# Singleton instance
_notifier: Optional[DiscordNotifier] = None

def get_discord_notifier() -> DiscordNotifier:
    """Get or create Discord notifier instance"""
    global _notifier
    if _notifier is None:
        _notifier = DiscordNotifier()
    return _notifier
