"""
Trading Engine - Core trading loop
"""
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any, List
from mt5_client import MT5Client, get_mt5_client
from ai_brain import AIBrain, get_ai_brain
from websocket_manager import get_ws_manager
from config import get_config, AppConfig
from discord_notifier import get_discord_notifier
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TradingEngine:
    """Core trading engine that runs the main loop"""
    
    def __init__(self):
        self.config = get_config()
        self.mt5_client: Optional[MT5Client] = None
        self.ai_brain: Optional[AIBrain] = None
        self.ws_manager = get_ws_manager()
        
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._loop_interval = 30  # seconds between checks (increased from 5)
        self._last_entry_check = None
        self._last_guardian_check = None  # Track guardian checks
        self._guardian_interval = 5  # minutes between guardian AI checks
        self._entry_interval = 15  # minutes between entry AI checks
        self._previous_positions: Dict[int, Dict] = {}  # Track positions for close detection
        
        # SL Cooldown - prevent revenge trading
        self._last_sl_hit: Optional[datetime] = None
        self._sl_cooldown_minutes = 5  # Wait 5 mins after SL before new entry
    
    async def initialize(self) -> Dict[str, Any]:
        """Initialize MT5 connection and AI brain"""
        try:
            # Initialize MT5 client
            self.mt5_client = get_mt5_client(self.config.mt5)
            result = self.mt5_client.connect()
            
            if not result.get("success"):
                return {"success": False, "error": f"MT5: {result.get('error')}"}
            
            # Initialize AI brain
            self.ai_brain = get_ai_brain(self.config.ai)
            
            logger.info("Trading engine initialized successfully")
            return {"success": True, "message": "Engine initialized"}
            
        except Exception as e:
            logger.error(f"Initialization failed: {e}")
            return {"success": False, "error": str(e)}
    
    def _get_dynamic_lot(self) -> float:
        """Calculate dynamic lot size based on account growth.
        Formula: lot = base_lot * (1.3 ^ times_doubled)
        Where times_doubled = floor(log2(current_balance / initial_balance))
        This gives +30% lot increase for every time balance doubles.
        """
        try:
            import math
            from profit_tracker import get_profit_tracker
            tracker = get_profit_tracker()
            
            base_lot = self.config.trading.lot_size
            initial_balance = tracker.initial_balance
            
            if initial_balance <= 0:
                return base_lot
            
            # Get current balance
            account = self.mt5_client.get_account_info()
            current_balance = account.get('balance', initial_balance)
            
            # Calculate how many times balance has doubled
            if current_balance >= initial_balance:
                ratio = current_balance / initial_balance
                times_doubled = int(math.log2(ratio)) if ratio >= 1 else 0
            else:
                times_doubled = 0
            
            # Apply +30% per double (1.3^times_doubled)
            growth_multiplier = 1.3 ** times_doubled
            
            # Calculate new lot
            dynamic_lot = base_lot * growth_multiplier
            
            # Round to 2 decimals (standard lot precision)
            dynamic_lot = round(dynamic_lot, 2)
            
            if times_doubled > 0:
                logger.info(f"Dynamic lot: {base_lot} x 1.3^{times_doubled} = {dynamic_lot} (Balance: ${current_balance:.2f})")
            
            return dynamic_lot
            
        except Exception as e:
            logger.error(f"Dynamic lot calculation error: {e}")
            return self.config.trading.lot_size
    
    async def start(self) -> Dict[str, Any]:
        """Start the trading loop"""
        if self._running:
            return {"success": False, "error": "Engine already running"}
        
        # Use existing MT5 client if available, don't reinitialize
        if not self.mt5_client:
            self.mt5_client = get_mt5_client()
        
        if not self.mt5_client or not self.mt5_client.connected:
            return {"success": False, "error": "MT5 not connected. Please connect first."}
        
        # Initialize AI brain if not already
        if not self.ai_brain:
            self.ai_brain = get_ai_brain(self.config.ai)
        
        self._running = True
        self.config.is_running = True
        self._task = asyncio.create_task(self._main_loop())
        
        await self.ws_manager.broadcast_status({
            "running": True,
            "mt5_connected": True,
            "message": "Trading engine started"
        })
        
        logger.info("Trading engine started")
        return {"success": True, "message": "Engine started"}
    
    async def stop(self) -> Dict[str, Any]:
        """Stop the trading loop"""
        if not self._running:
            return {"success": False, "error": "Engine not running"}
        
        self._running = False
        self.config.is_running = False
        
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        
        await self.ws_manager.broadcast_status({
            "running": False,
            "message": "Trading engine stopped"
        })
        
        logger.info("Trading engine stopped")
        return {"success": True, "message": "Engine stopped"}
    
    async def _main_loop(self):
        """Main trading loop"""
        logger.info("Main trading loop started")
        
        while self._running:
            try:
                await self._tick()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                await self.ws_manager.broadcast_error(str(e))
            
            await asyncio.sleep(self._loop_interval)
        
        logger.info("Main trading loop ended")
    
    async def _tick(self):
        """Single tick of the trading loop"""
        symbol = self.config.trading.symbol
        
        # 1. Get current market data
        price = self.mt5_client.get_symbol_price(symbol)
        if "error" in price:
            logger.warning(f"Failed to get price: {price['error']}")
            return
        
        # Broadcast price update
        await self.ws_manager.broadcast_price(price)
        
        # 2. Get account info
        account = self.mt5_client.get_account_info()
        if "error" not in account:
            await self.ws_manager.broadcast_account(account)
        
        # 3. Get current positions
        positions = self.mt5_client.get_positions(symbol)
        await self.ws_manager.broadcast_positions(positions)
        
        # 3.5 Detect closed positions (SL/TP hits)
        await self._check_closed_positions(positions)
        
        # 4. Check if market is open
        if not self.mt5_client.is_market_open(symbol):
            logger.debug("Market is closed")
            return
        
        # 5. Apply session filter if enabled
        if self.config.trading.session_filter_enabled:
            if not self._is_allowed_session():
                logger.debug("Current session not allowed")
                return
        
        # 6. Auto-BEP Check (runs EVERY tick, independent from AI)
        if len(positions) > 0 and self.config.trading.auto_bep_enabled:
            await self._check_auto_bep(positions, price)
        
        # 7. Run Guardian Logic for existing positions (with interval check)
        if len(positions) > 0 and self._should_check_guardian():
            for position in positions:
                await self._run_guardian(position, price)
            self._last_guardian_check = datetime.now()
        
        # 7. DCA Averaging - Add positions every 20 pips against the trade
        if len(positions) > 0 and len(positions) < self.config.trading.max_positions:
            await self._check_dca_averaging(positions, price, symbol)
        
        # 8. Run Entry Logic if no positions exist
        if len(positions) == 0:
            # Add delay to prevent too frequent entry checks
            if self._should_check_entry():
                await self._run_entry(symbol, price)
    
    async def _run_entry(self, symbol: str, current_price: Dict):
        """Run AI entry logic"""
        try:
            # Check SL cooldown - prevent revenge trading
            if self._last_sl_hit:
                elapsed = (datetime.now() - self._last_sl_hit).total_seconds()
                cooldown_seconds = self._sl_cooldown_minutes * 60
                if elapsed < cooldown_seconds:
                    remaining = int((cooldown_seconds - elapsed) / 60)
                    logger.info(f"🕐 SL Cooldown active - {remaining} mins remaining, skipping entry")
                    return
                else:
                    # Cooldown expired
                    logger.info("✅ SL Cooldown expired, resuming normal trading")
                    self._last_sl_hit = None
            
            # Get candle data
            candles_h1 = self.mt5_client.get_candles(symbol, "H1", 50)
            candles_m15 = self.mt5_client.get_candles(symbol, "M15", 50)
            
            h1_data = candles_h1.to_dict('records') if not candles_h1.empty else []
            m15_data = candles_m15.to_dict('records') if not candles_m15.empty else []
            
            # Call AI for entry analysis
            result = await self.ai_brain.analyze_entry(
                symbol,
                current_price,
                h1_data,
                m15_data,
                self.config.trading
            )
            
            # Broadcast reasoning
            await self.ws_manager.broadcast_reasoning({
                "timestamp": datetime.now().isoformat(),
                "symbol": symbol,
                "type": "ENTRY",
                "result": result
            })
            
            # Check if AI wants to enter
            if "error" in result:
                logger.warning(f"AI entry error: {result['error']}")
                return
            
            decision = result.get("decision", "WAIT").upper()
            
            if decision in ["BUY", "SELL"]:
                sl = result.get("SL")
                tp = result.get("TP")
                confidence = result.get("confidence", 0)
                
                # Only execute if confidence is high enough
                if confidence >= 60:
                    # Use dynamic lot sizing based on account growth
                    dynamic_lot = self._get_dynamic_lot()
                    
                    # Validate and enforce max SL of 60 pips (6 points)
                    current_price_val = self.mt5_client.get_price(symbol)
                    if decision == "BUY":
                        entry_price = current_price_val.get('ask', 0)
                        max_sl = entry_price - 6  # 60 pips = 6 points
                        if sl is None or sl < max_sl:
                            sl = max_sl
                            logger.info(f"SL adjusted to max 60 pips: {sl}")
                    else:  # SELL
                        entry_price = current_price_val.get('bid', 0)
                        max_sl = entry_price + 6  # 60 pips = 6 points
                        if sl is None or sl > max_sl:
                            sl = max_sl
                            logger.info(f"SL adjusted to max 60 pips: {sl}")
                    
                    order_result = self.mt5_client.place_order(
                        symbol=symbol,
                        order_type=decision,
                        volume=dynamic_lot,
                        sl=sl,
                        tp=tp,
                        comment=f"AI_{confidence}"
                    )
                    
                    if order_result.get("success"):
                        trade_data = {
                            "action": "OPEN",
                            "type": decision,
                            "symbol": symbol,
                            "volume": dynamic_lot,
                            "sl": sl,
                            "tp": tp,
                            "result": order_result
                        }
                        await self.ws_manager.broadcast_trade(trade_data)
                        logger.info(f"Trade opened: {decision} {symbol} @ {dynamic_lot} lot")
                        
                        # Send Discord notification
                        discord = get_discord_notifier()
                        await discord.notify_trade_open(trade_data)
                        
                        # Broadcast updated positions immediately
                        positions = self.mt5_client.get_positions(symbol)
                        await self.ws_manager.broadcast_positions(positions)
                    else:
                        logger.error(f"Failed to open trade: {order_result.get('error')}")
            
            self._last_entry_check = datetime.now()
            
        except Exception as e:
            logger.error(f"Entry logic error: {e}")
    
    async def _run_guardian(self, position: Dict, current_price: Dict):
        """Run AI guardian logic for a position"""
        try:
            symbol = position['symbol']
            
            # Get M15 candles for analysis
            candles_m15 = self.mt5_client.get_candles(symbol, "M15", 20)
            m15_data = candles_m15.to_dict('records') if not candles_m15.empty else []
            
            # Call AI for guardian analysis
            result = await self.ai_brain.guardian_check(
                position,
                current_price,
                m15_data,
                self.config.trading
            )
            
            # Broadcast reasoning
            await self.ws_manager.broadcast_reasoning({
                "timestamp": datetime.now().isoformat(),
                "symbol": symbol,
                "ticket": position['ticket'],
                "type": "GUARDIAN",
                "result": result
            })
            
            if "error" in result:
                logger.warning(f"AI guardian error: {result['error']}")
                return
            
            action = result.get("action", "HOLD").upper()
            
            if action == "MODIFY_SL" or action == "MODIFY_TP":
                new_sl = result.get("new_sl")
                new_tp = result.get("new_tp")
                
                modify_result = self.mt5_client.modify_position(
                    ticket=position['ticket'],
                    sl=new_sl,
                    tp=new_tp
                )
                
                if modify_result.get("success"):
                    await self.ws_manager.broadcast_trade({
                        "action": "MODIFY",
                        "ticket": position['ticket'],
                        "new_sl": new_sl,
                        "new_tp": new_tp
                    })
                    logger.info(f"Position {position['ticket']} modified")
                    
            elif action == "CLOSE":
                close_result = self.mt5_client.close_position(position['ticket'])
                
                if close_result.get("success"):
                    await self.ws_manager.broadcast_trade({
                        "action": "CLOSE",
                        "ticket": position['ticket'],
                        "profit": close_result.get("profit")
                    })
                    logger.info(f"Position {position['ticket']} closed")
            
            elif action == "ADD_DCA":
                # Momentum DCA - add position when strong momentum detected
                symbol = position['symbol']
                current_positions = self.mt5_client.get_positions(symbol)
                
                if len(current_positions) < self.config.trading.max_positions:
                    momentum_strength = result.get("momentum_strength", "WEAK")
                    dca_reason = result.get("dca_reason", "Strong momentum detected")
                    
                    logger.info(f"Momentum DCA triggered: {momentum_strength} - {dca_reason}")
                    
                    order_result = self.mt5_client.place_order(
                        symbol=symbol,
                        order_type=position['type'],  # Same direction as existing position
                        volume=self.config.trading.lot_size,
                        sl=position['sl'],
                        tp=position['tp'],
                        comment=f"MOMENTUM_DCA_{momentum_strength}"
                    )
                    
                    if order_result.get("success"):
                        dca_data = {
                            "action": "MOMENTUM_DCA",
                            "type": position['type'],
                            "symbol": symbol,
                            "volume": self.config.trading.lot_size,
                            "momentum": momentum_strength,
                            "reason": dca_reason,
                            "result": order_result
                        }
                        await self.ws_manager.broadcast_trade(dca_data)
                        
                        # Send Discord notification
                        discord = get_discord_notifier()
                        await discord.notify_dca(dca_data)
                        
                        logger.info(f"Momentum DCA opened: {position['type']} {symbol}")
                    else:
                        logger.error(f"Momentum DCA failed: {order_result.get('error')}")
                else:
                    logger.info(f"Momentum DCA skipped: max positions ({self.config.trading.max_positions}) reached")
        except Exception as e:
            logger.error(f"Guardian logic error: {e}")
    
    async def _check_dca_averaging(self, positions: List[Dict], current_price: Dict, symbol: str):
        """Check if we should add a DCA position (both directions - losing AND winning)"""
        try:
            DCA_PIPS = 20  # Add position every 20 pips
            DCA_LOT = self._get_dynamic_lot()  # Use dynamic lot based on account growth
            
            # Get the first/original position to determine direction
            first_position = positions[0]
            position_type = first_position['type']
            entry_price = first_position['open_price']
            
            # Get current market price
            if position_type == "BUY":
                current = current_price.get('bid', 0)
                pips_profit = (current - entry_price) * 10  # Positive = profit
            else:
                current = current_price.get('ask', 0)
                pips_profit = (entry_price - current) * 10  # Positive = profit
            
            # Calculate pips moved (absolute - both directions)
            pips_moved = abs(pips_profit)
            
            # Calculate how many positions we should have based on pips moved
            # DCA both when losing AND when winning for balance
            expected_positions = 1 + int(pips_moved / DCA_PIPS) if pips_moved >= DCA_PIPS else 1
            
            # Cap at max_positions
            expected_positions = min(expected_positions, self.config.trading.max_positions)
            
            # If we need more positions, add one
            if len(positions) < expected_positions:
                direction = "profit" if pips_profit > 0 else "against"
                logger.info(f"DCA: Price moved {pips_moved:.1f} pips ({direction}), adding position #{len(positions)+1}")
                
                # Place DCA order (same direction as original)
                order_result = self.mt5_client.place_order(
                    symbol=symbol,
                    order_type=position_type,
                    volume=DCA_LOT,
                    sl=first_position['sl'],
                    tp=first_position['tp'],
                    comment=f"DCA_{len(positions)+1}"
                )
                
                if order_result.get("success"):
                    dca_data = {
                        "action": "DCA",
                        "type": position_type,
                        "symbol": symbol,
                        "volume": DCA_LOT,
                        "position_count": len(positions) + 1,
                        "pips_moved": round(pips_moved, 1),
                        "direction": direction,
                        "result": order_result
                    }
                    await self.ws_manager.broadcast_trade(dca_data)
                    
                    # Send Discord notification
                    discord = get_discord_notifier()
                    await discord.notify_dca(dca_data)
                    
                    logger.info(f"DCA position opened ({direction}): {position_type} {DCA_LOT} {symbol}")
                else:
                    logger.error(f"DCA order failed: {order_result.get('error')}")
                    
        except Exception as e:
            logger.error(f"DCA averaging error: {e}")
    
    async def _check_auto_bep(self, positions: List[Dict], current_price: Dict):
        """Auto Break-Even: Move SL to entry price when profit exceeds threshold"""
        try:
            bep_pips = self.config.trading.auto_bep_pips  # Trigger pips (e.g., 20)
            
            for position in positions:
                entry_price = position['open_price']
                current_sl = position['sl']
                position_type = position['type']
                
                # Get current price
                if position_type == "BUY":
                    current = current_price.get('bid', entry_price)
                    profit_pips = (current - entry_price) * 10  # Convert to pips
                    # For BUY, SL should be moved UP to entry
                    sl_needs_update = current_sl < entry_price
                else:  # SELL
                    current = current_price.get('ask', entry_price)
                    profit_pips = (entry_price - current) * 10
                    # For SELL, SL should be moved DOWN to entry
                    sl_needs_update = current_sl > entry_price
                
                # Check if we should move SL to Break Even
                if profit_pips >= bep_pips and sl_needs_update:
                    logger.info(f"Auto-BEP triggered for ticket {position['ticket']}: {profit_pips:.1f} pips profit, moving SL to {entry_price}")
                    
                    modify_result = self.mt5_client.modify_position(
                        ticket=position['ticket'],
                        sl=entry_price,
                        tp=position['tp']  # Keep TP same
                    )
                    
                    if modify_result.get("success"):
                        bep_data = {
                            "action": "AUTO_BEP",
                            "ticket": position['ticket'],
                            "new_sl": entry_price,
                            "profit_pips": round(profit_pips, 1),
                            "message": f"SL moved to Break Even ({entry_price})"
                        }
                        await self.ws_manager.broadcast_trade(bep_data)
                        
                        # Send Discord notification
                        discord = get_discord_notifier()
                        await discord.notify_auto_bep(bep_data)
                        
                        # Broadcast updated positions
                        updated_positions = self.mt5_client.get_positions()
                        await self.ws_manager.broadcast_positions(updated_positions)
                        
                        logger.info(f"Auto-BEP: Position {position['ticket']} SL moved to {entry_price}")
                    else:
                        logger.error(f"Auto-BEP modify failed: {modify_result.get('error')}")
                        
        except Exception as e:
            logger.error(f"Auto-BEP error: {e}")
    
    async def _check_closed_positions(self, current_positions: List[Dict]):
        """Detect positions that were closed (SL/TP hit) and send notifications"""
        try:
            # Get current position tickets
            current_tickets = {pos['ticket'] for pos in current_positions}
            
            # Check if any previously tracked position is now gone
            for ticket, prev_pos in list(self._previous_positions.items()):
                if ticket not in current_tickets:
                    # Position was closed! Determine if TP or SL hit
                    entry_price = prev_pos.get('open_price', 0)
                    sl = prev_pos.get('sl', 0)
                    tp = prev_pos.get('tp', 0)
                    position_type = prev_pos.get('type', 'BUY')
                    symbol = prev_pos.get('symbol', 'XAUUSD')
                    
                    # Get last known profit (estimate based on SL/TP)
                    # We don't have exact close price, so we estimate
                    profit = prev_pos.get('profit', 0)  # Use last known profit
                    
                    # Determine close type (rough estimate)
                    if profit >= 0:
                        close_type = 'TP_HIT'
                    else:
                        close_type = 'SL_HIT'
                    
                    logger.info(f"Position {ticket} closed ({close_type}): profit ${profit:.2f}")
                    
                    # Set cooldown if SL was hit (prevent revenge trading)
                    if close_type == 'SL_HIT':
                        self._last_sl_hit = datetime.now()
                        logger.warning(f"⚠️ SL HIT! Cooldown activated for {self._sl_cooldown_minutes} minutes")
                    
                    # Send Discord notification
                    discord = get_discord_notifier()
                    await discord.notify_trade_close({
                        'ticket': ticket,
                        'profit': profit,
                        'close_type': close_type,
                        'symbol': symbol,
                        'type': position_type
                    })
                    
                    # Broadcast to frontend
                    await self.ws_manager.broadcast_trade({
                        "action": "CLOSE",
                        "ticket": ticket,
                        "profit": profit,
                        "close_type": close_type
                    })
                    
                    # Remove from tracking
                    del self._previous_positions[ticket]
            
            # Update tracking with current positions
            for pos in current_positions:
                self._previous_positions[pos['ticket']] = pos
                
        except Exception as e:
            logger.error(f"Closed position check error: {e}")
    
    def _should_check_entry(self) -> bool:
        """Check if enough time has passed since last entry check"""
        if self._last_entry_check is None:
            return True
        
        elapsed = (datetime.now() - self._last_entry_check).total_seconds()
        return elapsed >= (self._entry_interval * 60)  # Convert minutes to seconds
    
    def _should_check_guardian(self) -> bool:
        """Check if enough time has passed since last guardian check"""
        if self._last_guardian_check is None:
            return True
        
        elapsed = (datetime.now() - self._last_guardian_check).total_seconds()
        return elapsed >= (self._guardian_interval * 60)  # Convert minutes to seconds
    
    def _is_allowed_session(self) -> bool:
        """Check if current time is in allowed trading sessions"""
        now = datetime.utcnow()
        hour = now.hour
        
        allowed = self.config.trading.allowed_sessions
        
        # Define session hours (UTC)
        sessions = {
            'sydney': (21, 6),      # 21:00 - 06:00 UTC
            'asia': (0, 9),          # 00:00 - 09:00 UTC (Tokyo)
            'london': (7, 16),       # 07:00 - 16:00 UTC
            'newyork': (12, 21)      # 12:00 - 21:00 UTC
        }
        
        for session_name in allowed:
            if session_name.lower() in sessions:
                start, end = sessions[session_name.lower()]
                if start <= hour < end or (start > end and (hour >= start or hour < end)):
                    return True
        
        return False
    
    def get_status(self) -> Dict[str, Any]:
        """Get current engine status"""
        return {
            "running": self._running,
            "connected": self.mt5_client.connected if self.mt5_client else False,
            "symbol": self.config.trading.symbol,
            "lot_size": self.config.trading.lot_size,
            "max_positions": self.config.trading.max_positions
        }


# Singleton instance
_engine: Optional[TradingEngine] = None

def get_trading_engine() -> TradingEngine:
    """Get or create trading engine instance"""
    global _engine
    if _engine is None:
        _engine = TradingEngine()
    return _engine
