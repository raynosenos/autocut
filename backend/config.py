"""
Configuration management for AI Trading Bot
"""
import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic import BaseModel
from typing import Optional, List

# Load environment variables
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

class MT5Config(BaseModel):
    """MetaTrader 5 connection configuration"""
    login: int = int(os.getenv('MT5_LOGIN', '0'))
    password: str = os.getenv('MT5_PASSWORD', '')
    server: str = os.getenv('MT5_SERVER', 'MetaQuotes-Demo')

class AIConfig(BaseModel):
    """AI provider configuration"""
    groq_api_key: str = os.getenv('GROQ_API_KEY', '')
    deepseek_api_key: str = os.getenv('DEEPSEEK_API_KEY', '')
    primary_provider: str = 'groq'  # 'groq' or 'deepseek'
    
class TradingConfig(BaseModel):
    """Trading parameters configuration"""
    symbol: str = os.getenv('SYMBOL', 'XAUUSD')
    lot_size: float = float(os.getenv('LOT_SIZE', '0.01'))
    max_positions: int = int(os.getenv('MAX_POSITIONS', '3'))
    risk_percent: float = float(os.getenv('RISK_PERCENT', '1.0'))
    
    # Advanced features
    auto_bep_enabled: bool = os.getenv('AUTO_BEP_ENABLED', 'true').lower() == 'true'
    auto_bep_pips: float = float(os.getenv('AUTO_BEP_PIPS', '5.0'))
    min_rr_ratio: float = float(os.getenv('MIN_RR_RATIO', '1.5'))
    max_candles: int = 250
    guardian_delay_minutes: int = int(os.getenv('GUARDIAN_DELAY', '15'))
    
    # Session filter
    session_filter_enabled: bool = os.getenv('SESSION_FILTER_ENABLED', 'false').lower() == 'true'
    allowed_sessions: List[str] = os.getenv('ALLOWED_SESSIONS', 'london,newyork,asia,sydney').split(',')
    
    # Trailing stop
    trailing_stop_enabled: bool = os.getenv('TRAILING_STOP_ENABLED', 'false').lower() == 'true'
    trailing_stop_pips: float = float(os.getenv('TRAILING_STOP_PIPS', '10.0'))

class AppConfig(BaseModel):
    """Main application configuration"""
    mt5: MT5Config = MT5Config()
    ai: AIConfig = AIConfig()
    trading: TradingConfig = TradingConfig()
    
    api_port: int = int(os.getenv('API_PORT', '8000'))
    frontend_port: int = int(os.getenv('FRONTEND_PORT', '5173'))
    
    # Bot state
    is_running: bool = False

# Global config instance
config = AppConfig()

def update_trading_config(**kwargs) -> TradingConfig:
    """Update trading configuration"""
    for key, value in kwargs.items():
        if hasattr(config.trading, key):
            setattr(config.trading, key, value)
    return config.trading

def get_config() -> AppConfig:
    """Get current configuration"""
    return config
