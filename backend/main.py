"""
FastAPI Main Application - AI Trading Bot API
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import asyncio

from config import get_config, update_trading_config
from mt5_client import get_mt5_client, MT5Client
from ai_brain import get_ai_brain
from trading_engine import get_trading_engine, TradingEngine
from websocket_manager import get_ws_manager
from profit_tracker import get_profit_tracker

# Initialize FastAPI app
app = FastAPI(
    title="AI Trading Bot",
    description="Automated trading system with AI-powered entry and guardian logic",
    version="1.0.0"
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Get instances
config = get_config()
ws_manager = get_ws_manager()


# ============= Pydantic Models =============

class ConfigUpdate(BaseModel):
    lot_size: Optional[float] = None
    max_positions: Optional[int] = None
    risk_percent: Optional[float] = None
    auto_bep_enabled: Optional[bool] = None
    auto_bep_pips: Optional[float] = None
    min_rr_ratio: Optional[float] = None
    session_filter_enabled: Optional[bool] = None
    allowed_sessions: Optional[List[str]] = None
    trailing_stop_enabled: Optional[bool] = None
    trailing_stop_pips: Optional[float] = None
    guardian_delay_minutes: Optional[int] = None

class OrderRequest(BaseModel):
    order_type: str  # BUY or SELL
    volume: Optional[float] = None
    sl: Optional[float] = None
    tp: Optional[float] = None

class ModifyRequest(BaseModel):
    sl: Optional[float] = None
    tp: Optional[float] = None

class MT5ConnectRequest(BaseModel):
    login: int
    password: str
    server: str


# ============= REST Endpoints =============

@app.get("/")
async def root():
    """API root endpoint"""
    return {
        "name": "AI Trading Bot",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/api/status")
async def get_status():
    """Get bot and MT5 connection status"""
    engine = get_trading_engine()
    mt5 = get_mt5_client()
    
    return {
        "bot_running": engine._running if engine else False,
        "mt5_connected": mt5.connected if mt5 else False,
        "symbol": config.trading.symbol,
        "market_open": mt5.is_market_open(config.trading.symbol) if mt5 and mt5.connected else False
    }


@app.post("/api/connect")
async def connect_mt5(request: MT5ConnectRequest):
    """Connect to MT5 with provided credentials"""
    from config import MT5Config
    from mt5_client import MT5Client
    import os
    
    mt5_config = MT5Config(
        login=request.login,
        password=request.password,
        server=request.server
    )
    
    # Update global config
    config.mt5 = mt5_config
    
    # Create new MT5 client with these credentials
    client = MT5Client(mt5_config)
    result = client.connect()
    
    if result.get("success"):
        # Store the client globally and in engine
        import mt5_client as mt5_module
        mt5_module._client = client
        
        # Also set it on the trading engine
        engine = get_trading_engine()
        engine.mt5_client = client
        
        # Save credentials to .env file for auto-connect on restart
        try:
            env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
            if os.path.exists(env_path):
                with open(env_path, 'r') as f:
                    lines = f.readlines()
                
                # Update or add credentials
                new_lines = []
                updated = {'MT5_LOGIN': False, 'MT5_PASSWORD': False, 'MT5_SERVER': False}
                for line in lines:
                    if line.startswith('MT5_LOGIN='):
                        new_lines.append(f'MT5_LOGIN={request.login}\n')
                        updated['MT5_LOGIN'] = True
                    elif line.startswith('MT5_PASSWORD='):
                        new_lines.append(f'MT5_PASSWORD={request.password}\n')
                        updated['MT5_PASSWORD'] = True
                    elif line.startswith('MT5_SERVER='):
                        new_lines.append(f'MT5_SERVER={request.server}\n')
                        updated['MT5_SERVER'] = True
                    else:
                        new_lines.append(line)
                
                with open(env_path, 'w') as f:
                    f.writelines(new_lines)
                    
                print(f"✅ Credentials saved to .env for auto-connect")
        except Exception as e:
            print(f"⚠️ Could not save credentials: {e}")
        
        return {"success": True, "message": "Connected to MT5 successfully"}
    
    return result


@app.post("/api/disconnect")
async def disconnect_mt5():
    """Disconnect from MT5"""
    mt5 = get_mt5_client()
    if mt5:
        return mt5.disconnect()
    return {"success": False, "error": "Not connected"}


@app.get("/api/account")
async def get_account():
    """Get MT5 account information"""
    mt5 = get_mt5_client()
    if not mt5 or not mt5.connected:
        raise HTTPException(status_code=503, detail="MT5 not connected")
    
    return mt5.get_account_info()


@app.get("/api/positions")
async def get_positions():
    """Get all open positions"""
    mt5 = get_mt5_client()
    if not mt5 or not mt5.connected:
        raise HTTPException(status_code=503, detail="MT5 not connected")
    
    return mt5.get_positions(config.trading.symbol)


@app.get("/api/price")
async def get_price():
    """Get current price for trading symbol"""
    mt5 = get_mt5_client()
    if not mt5 or not mt5.connected:
        raise HTTPException(status_code=503, detail="MT5 not connected")
    
    return mt5.get_symbol_price(config.trading.symbol)


@app.get("/api/config")
async def get_trading_config():
    """Get current trading configuration"""
    return config.trading.model_dump()


@app.post("/api/config")
async def update_config(update: ConfigUpdate):
    """Update trading configuration and save to .env"""
    import os
    
    updates = {k: v for k, v in update.model_dump().items() if v is not None}
    updated = update_trading_config(**updates)
    
    # Save to .env file for persistence
    try:
        env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
        if os.path.exists(env_path):
            with open(env_path, 'r') as f:
                lines = f.readlines()
            
            # Map config keys to .env keys
            env_mapping = {
                'lot_size': 'LOT_SIZE',
                'max_positions': 'MAX_POSITIONS',
                'risk_percent': 'RISK_PERCENT',
                'symbol': 'SYMBOL',
                'auto_bep_enabled': 'AUTO_BEP_ENABLED',
                'auto_bep_pips': 'AUTO_BEP_PIPS',
                'min_rr_ratio': 'MIN_RR_RATIO',
                'guardian_delay_minutes': 'GUARDIAN_DELAY',
                'session_filter_enabled': 'SESSION_FILTER_ENABLED',
                'allowed_sessions': 'ALLOWED_SESSIONS',
                'trailing_stop_enabled': 'TRAILING_STOP_ENABLED',
                'trailing_stop_pips': 'TRAILING_STOP_PIPS',
            }
            
            # Handle special types (bool -> string, list -> comma-separated)
            def format_value(key, value):
                if isinstance(value, bool):
                    return 'true' if value else 'false'
                elif isinstance(value, list):
                    return ','.join(value)
                return str(value)
            
            new_lines = []
            for line in lines:
                updated_line = False
                for config_key, env_key in env_mapping.items():
                    if line.startswith(f'{env_key}=') and config_key in updates:
                        formatted = format_value(config_key, updates[config_key])
                        new_lines.append(f'{env_key}={formatted}\n')
                        updated_line = True
                        break
                if not updated_line:
                    new_lines.append(line)
            
            with open(env_path, 'w') as f:
                f.writelines(new_lines)
            
            print(f"✅ Config saved to .env")
    except Exception as e:
        print(f"⚠️ Could not save config: {e}")
    
    return updated.model_dump()


@app.post("/api/start")
async def start_bot():
    """Start the trading bot"""
    engine = get_trading_engine()
    return await engine.start()


@app.post("/api/stop")
async def stop_bot():
    """Stop the trading bot"""
    engine = get_trading_engine()
    return await engine.stop()


@app.post("/api/order")
async def place_order(request: OrderRequest):
    """Manually place an order"""
    mt5 = get_mt5_client()
    if not mt5 or not mt5.connected:
        raise HTTPException(status_code=503, detail="MT5 not connected")
    
    volume = request.volume or config.trading.lot_size
    
    return mt5.place_order(
        symbol=config.trading.symbol,
        order_type=request.order_type,
        volume=volume,
        sl=request.sl,
        tp=request.tp,
        comment="MANUAL_TRADE"
    )


@app.post("/api/positions/{ticket}/modify")
async def modify_position(ticket: int, request: ModifyRequest):
    """Modify SL/TP of a position"""
    mt5 = get_mt5_client()
    if not mt5 or not mt5.connected:
        raise HTTPException(status_code=503, detail="MT5 not connected")
    
    return mt5.modify_position(ticket, request.sl, request.tp)


@app.post("/api/positions/{ticket}/close")
async def close_position(ticket: int):
    """Close a position"""
    mt5 = get_mt5_client()
    if not mt5 or not mt5.connected:
        raise HTTPException(status_code=503, detail="MT5 not connected")
    
    return mt5.close_position(ticket)


@app.post("/api/positions/close-all")
async def close_all_positions():
    """Close all positions"""
    mt5 = get_mt5_client()
    if not mt5 or not mt5.connected:
        raise HTTPException(status_code=503, detail="MT5 not connected")
    
    return mt5.close_all_positions(config.trading.symbol)


@app.get("/api/reasoning")
async def get_reasoning():
    """Get AI reasoning history"""
    brain = get_ai_brain()
    if brain:
        return brain.get_reasoning_history(limit=50)
    return []


@app.post("/api/ai/provider/{provider}")
async def switch_ai_provider(provider: str):
    """Switch AI provider (groq or deepseek)"""
    if provider not in ['groq', 'deepseek']:
        raise HTTPException(status_code=400, detail="Invalid provider. Use 'groq' or 'deepseek'")
    
    brain = get_ai_brain()
    if brain:
        brain.switch_provider(provider)
        return {"success": True, "provider": provider}
    
    return {"success": False, "error": "AI brain not initialized"}


# ============= Profit Tracker Endpoints =============

@app.get("/api/profit/stats")
async def get_profit_stats():
    """Get profit statistics and growth data"""
    tracker = get_profit_tracker()
    
    # Update with current account balance
    mt5 = get_mt5_client()
    if mt5 and mt5.connected:
        account = mt5.get_account_info()
        if not account.get("error"):
            tracker.set_initial_balance(account.get('balance', 0))
            tracker.update_balance(
                balance=account.get('balance', 0),
                equity=account.get('equity', 0)
            )
        
        # Always sync win rate from MT5 for accurate data
        history = mt5.get_trade_history(days=365)
        if not history.get("error") and history.get("total_trades", 0) > 0:
            tracker.total_wins = history.get('wins', 0)
            tracker.total_losses = history.get('losses', 0)
            tracker.total_trades = history.get('total_trades', 0)
            tracker._save_history()
    
    return tracker.get_stats()


@app.get("/api/profit/chart")
async def get_profit_chart(days: int = 30):
    """Get profit history for chart display"""
    tracker = get_profit_tracker()
    return tracker.get_chart_data(days=days)


@app.post("/api/profit/record")
async def record_trade_profit(profit: float):
    """Record a completed trade profit/loss"""
    tracker = get_profit_tracker()
    tracker.record_trade(profit)
    return {"success": True, "recorded": profit}


@app.get("/api/trade/history")
async def get_trade_history(days: int = 30, symbol: Optional[str] = None):
    """Get trade history from MT5"""
    mt5 = get_mt5_client()
    if not mt5 or not mt5.connected:
        return {"error": "MT5 not connected"}
    
    return mt5.get_trade_history(days=days, symbol=symbol)


@app.post("/api/profit/sync")
async def sync_win_rate_from_mt5(days: int = 365):
    """Sync win rate from MT5 trade history"""
    mt5 = get_mt5_client()
    if not mt5 or not mt5.connected:
        return {"error": "MT5 not connected"}
    
    # Get trade history from MT5
    history = mt5.get_trade_history(days=days)
    
    if history.get("error"):
        return history
    
    # Update profit tracker with MT5 data
    tracker = get_profit_tracker()
    tracker.total_wins = history.get('wins', 0)
    tracker.total_losses = history.get('losses', 0)
    tracker.total_trades = history.get('total_trades', 0)
    tracker._save_history()
    
    return {
        "success": True,
        "synced": True,
        "from_days": days,
        "total_trades": tracker.total_trades,
        "wins": tracker.total_wins,
        "losses": tracker.total_losses,
        "win_rate": round((tracker.total_wins / tracker.total_trades * 100) if tracker.total_trades > 0 else 0, 1)
    }


# ============= WebSocket Endpoint =============

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    await ws_manager.connect(websocket)
    
    try:
        # Send initial status
        mt5 = get_mt5_client()
        engine = get_trading_engine()
        await ws_manager.send_personal(websocket, "status", {
            "bot_running": engine._running if engine else False,
            "mt5_connected": mt5.connected if mt5 else False
        })
        
        # Keep connection alive and handle incoming messages
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                # Handle ping/pong or other client messages if needed
                if data == "ping":
                    await websocket.send_text("pong")
            except asyncio.TimeoutError:
                # Send heartbeat
                await websocket.send_text("heartbeat")
                
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket)
    except Exception as e:
        await ws_manager.disconnect(websocket)


# ============= Startup/Shutdown Events =============

@app.on_event("startup")
async def startup_event():
    """Initialize on startup"""
    print("=" * 50)
    print("🤖 AI Trading Bot API Starting...")
    print(f"📊 Symbol: {config.trading.symbol}")
    print(f"💰 Lot Size: {config.trading.lot_size}")
    print("=" * 50)
    
    # Auto-connect to MT5 if credentials are available
    if config.mt5.login and config.mt5.password and config.mt5.server:
        if str(config.mt5.login) != "your_account_number":  # Skip placeholder
            print("🔄 Auto-connecting to MT5...")
            try:
                from mt5_client import MT5Client
                import mt5_client as mt5_module
                
                client = MT5Client(config.mt5)
                result = client.connect()
                
                if result.get("success"):
                    mt5_module._client = client
                    engine = get_trading_engine()
                    engine.mt5_client = client
                    
                    # Also initialize AI brain
                    engine.ai_brain = get_ai_brain(config.ai)
                    
                    print(f"✅ Auto-connected to MT5 account {config.mt5.login}")
                    
                    # Auto-start the trading bot
                    print("🚀 Auto-starting trading bot...")
                    start_result = await engine.start()
                    if start_result.get("success"):
                        print("✅ Trading bot started automatically!")
                    else:
                        print(f"⚠️ Auto-start failed: {start_result.get('error')}")
                else:
                    print(f"⚠️ Auto-connect failed: {result.get('error')}")
                    print("   👉 Connect manually via dashboard")
            except Exception as e:
                print(f"⚠️ Auto-connect error: {e}")
                print("   👉 Connect manually via dashboard")
    else:
        print("ℹ️ No saved credentials, please connect via dashboard")
    
    # Always initialize AI brain at startup (for reasoning history)
    if not get_ai_brain():
        from ai_brain import AIBrain
        import ai_brain as ai_module
        ai_module._brain = AIBrain(config.ai)
        print("🧠 AI Brain initialized")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    engine = get_trading_engine()
    if engine._running:
        await engine.stop()
    
    mt5 = get_mt5_client()
    if mt5 and mt5.connected:
        mt5.disconnect()
    
    print("AI Trading Bot API shutdown complete")


# Run with: uvicorn main:app --reload --port 8000
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
