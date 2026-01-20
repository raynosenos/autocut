"""
MetaTrader 5 Client - Connection and trading operations
"""
import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime
from typing import Optional, Dict, List, Any
from config import MT5Config
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MT5Client:
    """MetaTrader 5 client for trading operations"""
    
    def __init__(self, config: MT5Config):
        self.config = config
        self.connected = False
        
    def connect(self) -> Dict[str, Any]:
        """Connect to MetaTrader 5 terminal"""
        try:
            # Initialize MT5
            if not mt5.initialize():
                error = mt5.last_error()
                return {
                    "success": False,
                    "error": f"MT5 initialization failed: {error}"
                }
            
            # Login to account
            authorized = mt5.login(
                login=self.config.login,
                password=self.config.password,
                server=self.config.server
            )
            
            if not authorized:
                error = mt5.last_error()
                mt5.shutdown()
                return {
                    "success": False, 
                    "error": f"MT5 login failed: {error}"
                }
            
            self.connected = True
            logger.info(f"Connected to MT5 account {self.config.login}")
            return {"success": True, "message": "Connected successfully"}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def disconnect(self) -> Dict[str, Any]:
        """Disconnect from MetaTrader 5"""
        try:
            mt5.shutdown()
            self.connected = False
            logger.info("Disconnected from MT5")
            return {"success": True, "message": "Disconnected successfully"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_account_info(self) -> Dict[str, Any]:
        """Get account information"""
        if not self.connected:
            return {"error": "Not connected to MT5"}
        
        try:
            info = mt5.account_info()
            if info is None:
                return {"error": "Failed to get account info"}
            
            return {
                "login": info.login,
                "balance": round(info.balance, 2),
                "equity": round(info.equity, 2),
                "profit": round(info.profit, 2),
                "margin": round(info.margin, 2),
                "margin_free": round(info.margin_free, 2),
                "margin_level": round(info.margin_level, 2) if info.margin_level else 0,
                "leverage": info.leverage,
                "currency": info.currency,
                "server": info.server,
                "trade_allowed": info.trade_allowed
            }
        except Exception as e:
            return {"error": str(e)}
    
    def get_symbol_price(self, symbol: str) -> Dict[str, Any]:
        """Get current price for a symbol"""
        if not self.connected:
            return {"error": "Not connected to MT5"}
        
        try:
            tick = mt5.symbol_info_tick(symbol)
            if tick is None:
                return {"error": f"Failed to get price for {symbol}"}
            
            symbol_info = mt5.symbol_info(symbol)
            
            return {
                "symbol": symbol,
                "bid": tick.bid,
                "ask": tick.ask,
                "spread": round((tick.ask - tick.bid) / symbol_info.point, 1) if symbol_info else 0,
                "time": datetime.fromtimestamp(tick.time).isoformat()
            }
        except Exception as e:
            return {"error": str(e)}
    
    def get_candles(self, symbol: str, timeframe: str = "H1", count: int = 100) -> pd.DataFrame:
        """Get historical candle data"""
        if not self.connected:
            return pd.DataFrame()
        
        try:
            # Map timeframe string to MT5 constant
            tf_map = {
                "M1": mt5.TIMEFRAME_M1,
                "M5": mt5.TIMEFRAME_M5,
                "M15": mt5.TIMEFRAME_M15,
                "M30": mt5.TIMEFRAME_M30,
                "H1": mt5.TIMEFRAME_H1,
                "H4": mt5.TIMEFRAME_H4,
                "D1": mt5.TIMEFRAME_D1,
            }
            
            tf = tf_map.get(timeframe, mt5.TIMEFRAME_H1)
            rates = mt5.copy_rates_from_pos(symbol, tf, 0, count)
            
            if rates is None or len(rates) == 0:
                return pd.DataFrame()
            
            df = pd.DataFrame(rates)
            df['time'] = pd.to_datetime(df['time'], unit='s')
            return df
            
        except Exception as e:
            logger.error(f"Error getting candles: {e}")
            return pd.DataFrame()
    
    def get_positions(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all open positions"""
        if not self.connected:
            return []
        
        try:
            if symbol:
                positions = mt5.positions_get(symbol=symbol)
            else:
                positions = mt5.positions_get()
            
            if positions is None or len(positions) == 0:
                return []
            
            result = []
            for pos in positions:
                result.append({
                    "ticket": pos.ticket,
                    "symbol": pos.symbol,
                    "type": "BUY" if pos.type == 0 else "SELL",
                    "volume": pos.volume,
                    "open_price": pos.price_open,
                    "current_price": pos.price_current,
                    "sl": pos.sl,
                    "tp": pos.tp,
                    "profit": round(pos.profit, 2),
                    "swap": pos.swap,
                    "time": datetime.fromtimestamp(pos.time).isoformat(),
                    "magic": pos.magic,
                    "comment": pos.comment
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            return []
    
    def place_order(
        self, 
        symbol: str, 
        order_type: str, 
        volume: float,
        sl: Optional[float] = None,
        tp: Optional[float] = None,
        comment: str = "AI_TRADE"
    ) -> Dict[str, Any]:
        """Place a market order"""
        if not self.connected:
            return {"success": False, "error": "Not connected to MT5"}
        
        try:
            # Get symbol info
            symbol_info = mt5.symbol_info(symbol)
            if symbol_info is None:
                return {"success": False, "error": f"Symbol {symbol} not found"}
            
            if not symbol_info.visible:
                mt5.symbol_select(symbol, True)
            
            # Determine filling mode supported by broker
            filling_mode = self._get_filling_mode(symbol_info)
            
            # Get current price
            tick = mt5.symbol_info_tick(symbol)
            if tick is None:
                return {"success": False, "error": "Failed to get price"}
            
            # Determine order type and price
            if order_type.upper() == "BUY":
                trade_type = mt5.ORDER_TYPE_BUY
                price = tick.ask
            else:
                trade_type = mt5.ORDER_TYPE_SELL
                price = tick.bid
            
            # Prepare request
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": volume,
                "type": trade_type,
                "price": price,
                "deviation": 20,
                "magic": 123456,
                "comment": comment,
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": filling_mode,
            }
            
            if sl:
                request["sl"] = sl
            if tp:
                request["tp"] = tp
            
            # Send order
            result = mt5.order_send(request)
            
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                return {
                    "success": False,
                    "error": f"Order failed: {result.comment}",
                    "retcode": result.retcode
                }
            
            logger.info(f"Order placed: {order_type} {volume} {symbol} @ {price}")
            return {
                "success": True,
                "ticket": result.order,
                "price": result.price,
                "volume": result.volume,
                "message": f"{order_type} {volume} {symbol} @ {result.price}"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _get_filling_mode(self, symbol_info):
        """Get supported filling mode for the symbol"""
        filling = symbol_info.filling_mode
        
        # Filling mode flags (raw values)
        # 1 = FOK (Fill or Kill)
        # 2 = IOC (Immediate or Cancel)  
        # 4 = RETURN (Return remaining volume)
        
        if filling & 1:  # FOK supported
            return mt5.ORDER_FILLING_FOK
        elif filling & 2:  # IOC supported
            return mt5.ORDER_FILLING_IOC
        else:
            # RETURN mode (most common for ECN brokers)
            return mt5.ORDER_FILLING_RETURN
    
    def modify_position(
        self,
        ticket: int,
        sl: Optional[float] = None,
        tp: Optional[float] = None
    ) -> Dict[str, Any]:
        """Modify SL/TP of an existing position"""
        if not self.connected:
            return {"success": False, "error": "Not connected to MT5"}
        
        try:
            # Get position info
            positions = mt5.positions_get(ticket=ticket)
            if positions is None or len(positions) == 0:
                return {"success": False, "error": f"Position {ticket} not found"}
            
            position = positions[0]
            
            request = {
                "action": mt5.TRADE_ACTION_SLTP,
                "position": ticket,
                "symbol": position.symbol,
                "sl": sl if sl else position.sl,
                "tp": tp if tp else position.tp,
            }
            
            result = mt5.order_send(request)
            
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                return {
                    "success": False,
                    "error": f"Modify failed: {result.comment}",
                    "retcode": result.retcode
                }
            
            logger.info(f"Position {ticket} modified: SL={sl}, TP={tp}")
            return {
                "success": True,
                "ticket": ticket,
                "sl": sl,
                "tp": tp,
                "message": f"Position {ticket} modified successfully"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def close_position(self, ticket: int) -> Dict[str, Any]:
        """Close a position by ticket"""
        if not self.connected:
            return {"success": False, "error": "Not connected to MT5"}
        
        try:
            # Get position info
            positions = mt5.positions_get(ticket=ticket)
            if positions is None or len(positions) == 0:
                return {"success": False, "error": f"Position {ticket} not found"}
            
            position = positions[0]
            
            # Get symbol info for filling mode
            symbol_info = mt5.symbol_info(position.symbol)
            filling_mode = self._get_filling_mode(symbol_info) if symbol_info else mt5.ORDER_FILLING_RETURN
            
            # Determine close type and price
            tick = mt5.symbol_info_tick(position.symbol)
            if position.type == 0:  # BUY position, close with SELL
                trade_type = mt5.ORDER_TYPE_SELL
                price = tick.bid
            else:  # SELL position, close with BUY
                trade_type = mt5.ORDER_TYPE_BUY
                price = tick.ask
            
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "position": ticket,
                "symbol": position.symbol,
                "volume": position.volume,
                "type": trade_type,
                "price": price,
                "deviation": 20,
                "magic": 123456,
                "comment": "AI_CLOSE",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": filling_mode,
            }
            
            result = mt5.order_send(request)
            
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                return {
                    "success": False,
                    "error": f"Close failed: {result.comment}",
                    "retcode": result.retcode
                }
            
            logger.info(f"Position {ticket} closed @ {price}")
            return {
                "success": True,
                "ticket": ticket,
                "price": result.price,
                "profit": position.profit,
                "message": f"Position {ticket} closed @ {result.price}"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def close_all_positions(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """Close all open positions"""
        positions = self.get_positions(symbol)
        
        if len(positions) == 0:
            return {"success": True, "message": "No positions to close", "closed": 0}
        
        closed = 0
        errors = []
        
        for pos in positions:
            result = self.close_position(pos["ticket"])
            if result.get("success"):
                closed += 1
            else:
                errors.append(result.get("error"))
        
        return {
            "success": len(errors) == 0,
            "closed": closed,
            "errors": errors,
            "message": f"Closed {closed}/{len(positions)} positions"
        }
    
    def is_market_open(self, symbol: str = "XAUUSD") -> bool:
        """Check if market is currently open for trading"""
        if not self.connected:
            return False
        
        try:
            symbol_info = mt5.symbol_info(symbol)
            if symbol_info is None:
                return False
            
            # Check if trading is allowed
            return symbol_info.trade_mode == mt5.SYMBOL_TRADE_MODE_FULL
        except:
            return False
    
    def get_symbol_info(self, symbol: str) -> Dict[str, Any]:
        """Get detailed symbol information"""
        if not self.connected:
            return {"error": "Not connected"}
        
        try:
            info = mt5.symbol_info(symbol)
            if info is None:
                return {"error": f"Symbol {symbol} not found"}
            
            return {
                "symbol": symbol,
                "point": info.point,
                "digits": info.digits,
                "spread": info.spread,
                "min_lot": info.volume_min,
                "max_lot": info.volume_max,
                "lot_step": info.volume_step,
                "contract_size": info.trade_contract_size,
                "trade_mode": info.trade_mode
            }
        except Exception as e:
            return {"error": str(e)}
    
    def get_trade_history(self, days: int = 30, symbol: Optional[str] = None) -> Dict[str, Any]:
        """Get closed trade history and calculate win rate"""
        if not self.connected:
            return {"error": "Not connected"}
        
        try:
            from datetime import timedelta
            
            # Get history for last N days
            end_time = datetime.now()
            start_time = end_time - timedelta(days=days)
            
            # Get all deals (closed trades)
            deals = mt5.history_deals_get(start_time, end_time)
            
            if deals is None or len(deals) == 0:
                return {
                    "success": True,
                    "total_trades": 0,
                    "wins": 0,
                    "losses": 0,
                    "win_rate": 0.0,
                    "total_profit": 0.0,
                    "trades": []
                }
            
            # Filter only closing deals (entry deals have profit=0)
            trades = []
            wins = 0
            losses = 0
            total_profit = 0.0
            
            for deal in deals:
                # Only count deal exits (entry = 0, exit = 1)
                if deal.entry == 1:  # Exit deal
                    # Filter by symbol if specified
                    if symbol and deal.symbol != symbol:
                        continue
                    
                    profit = deal.profit
                    total_profit += profit
                    
                    if profit >= 0:
                        wins += 1
                    else:
                        losses += 1
                    
                    trades.append({
                        "ticket": deal.ticket,
                        "symbol": deal.symbol,
                        "type": "BUY" if deal.type == 0 else "SELL",
                        "volume": deal.volume,
                        "price": deal.price,
                        "profit": profit,
                        "time": datetime.fromtimestamp(deal.time).isoformat(),
                        "comment": deal.comment
                    })
            
            total_trades = wins + losses
            win_rate = (wins / total_trades * 100) if total_trades > 0 else 0.0
            
            return {
                "success": True,
                "days": days,
                "total_trades": total_trades,
                "wins": wins,
                "losses": losses,
                "win_rate": round(win_rate, 1),
                "total_profit": round(total_profit, 2),
                "trades": trades[-50:]  # Last 50 trades
            }
            
        except Exception as e:
            logger.error(f"Failed to get trade history: {e}")
            return {"error": str(e)}


# Singleton instance
_client: Optional[MT5Client] = None

def get_mt5_client(config: Optional[MT5Config] = None) -> MT5Client:
    """Get or create MT5 client instance"""
    global _client
    if _client is None and config:
        _client = MT5Client(config)
    return _client
