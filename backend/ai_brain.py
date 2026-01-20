"""
AI Brain Module - Entry and Guardian Logic
Uses Groq (free) or Deepseek for trading analysis
"""
import httpx
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
from config import AIConfig, TradingConfig
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AIBrain:
    """AI module for trading decisions"""
    
    GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
    DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
    HISTORY_FILE = "reasoning_history.json"  # File to persist history
    
    def __init__(self, ai_config: AIConfig):
        self.config = ai_config
        self.provider = ai_config.primary_provider
        self.reasoning_history: List[Dict] = self._load_history()
        
        # API Key Rotation support (comma-separated keys)
        self._groq_keys = [k.strip() for k in (ai_config.groq_api_key or "").split(",") if k.strip()]
        self._deepseek_keys = [k.strip() for k in (ai_config.deepseek_api_key or "").split(",") if k.strip()]
        self._current_groq_index = 0
        self._current_deepseek_index = 0
        
        logger.info(f"Loaded {len(self._groq_keys)} Groq API key(s), {len(self._deepseek_keys)} Deepseek key(s)")
    
    def _get_history_path(self) -> str:
        """Get path to history file"""
        import os
        return os.path.join(os.path.dirname(__file__), self.HISTORY_FILE)
    
    def _load_history(self) -> List[Dict]:
        """Load reasoning history from file"""
        try:
            import os
            path = self._get_history_path()
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    logger.info(f"Loaded {len(data)} reasoning entries from file")
                    return data[-100:]  # Keep last 100
        except Exception as e:
            logger.warning(f"Could not load history: {e}")
        return []
    
    def _save_history(self):
        """Save reasoning history to file"""
        try:
            path = self._get_history_path()
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(self.reasoning_history[-100:], f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"Could not save history: {e}")
        
    def _get_api_config(self) -> tuple[str, str, str]:
        """Get API URL, key, and model based on provider (with key rotation)"""
        if self.provider == "groq":
            key = self._groq_keys[self._current_groq_index] if self._groq_keys else None
            return (
                self.GROQ_API_URL,
                key,
                "llama-3.3-70b-versatile"
            )
        else:
            key = self._deepseek_keys[self._current_deepseek_index] if self._deepseek_keys else None
            return (
                self.DEEPSEEK_API_URL,
                key,
                "deepseek-chat"
            )
    
    def _rotate_api_key(self):
        """Rotate to next API key after rate limit"""
        if self.provider == "groq" and len(self._groq_keys) > 1:
            self._current_groq_index = (self._current_groq_index + 1) % len(self._groq_keys)
            logger.info(f"Rotated to Groq key #{self._current_groq_index + 1}/{len(self._groq_keys)}")
        elif self.provider == "deepseek" and len(self._deepseek_keys) > 1:
            self._current_deepseek_index = (self._current_deepseek_index + 1) % len(self._deepseek_keys)
            logger.info(f"Rotated to Deepseek key #{self._current_deepseek_index + 1}/{len(self._deepseek_keys)}")
    
    async def _call_ai(self, messages: List[Dict], temperature: float = 0.3) -> Dict:
        """Call AI API and get response"""
        url, api_key, model = self._get_api_config()
        
        if not api_key:
            return {"error": f"No API key configured for {self.provider}"}
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": 1024,
            "response_format": {"type": "json_object"}
        }
        
        # Retry with exponential backoff for rate limits
        max_retries = 3
        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(url, headers=headers, json=payload)
                    
                    # Handle rate limit - rotate key and retry
                    if response.status_code == 429:
                        self._rotate_api_key()
                        # Get new key config after rotation
                        url, api_key, model = self._get_api_config()
                        headers["Authorization"] = f"Bearer {api_key}"
                        logger.warning(f"Rate limited, rotated to new key, retrying...")
                        import asyncio
                        await asyncio.sleep(2)  # Brief delay before retry with new key
                        continue
                    
                    response.raise_for_status()
                    
                    data = response.json()
                    content = data["choices"][0]["message"]["content"]
                    
                    # Parse JSON response
                    try:
                        return json.loads(content)
                    except json.JSONDecodeError:
                        return {"error": "Failed to parse AI response", "raw": content}
                        
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429 and attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 30
                    logger.warning(f"Rate limited, waiting {wait_time}s before retry...")
                    import asyncio
                    await asyncio.sleep(wait_time)
                    continue
                logger.error(f"AI API error: {e}")
                return {"error": f"API error: {e.response.status_code}"}
            except Exception as e:
                logger.error(f"AI call failed: {e}")
                return {"error": str(e)}
        
        return {"error": "Max retries exceeded due to rate limiting"}
    
    def _build_entry_prompt(
        self,
        symbol: str,
        current_price: Dict,
        candles_h1: List[Dict],
        candles_m15: List[Dict],
        trading_config: TradingConfig
    ) -> List[Dict]:
        """Build prompt for entry analysis"""
        
        # Format candle data
        h1_summary = self._summarize_candles(candles_h1[-20:]) if candles_h1 else "No data"
        m15_summary = self._summarize_candles(candles_m15[-20:]) if candles_m15 else "No data"
        
        # Get current price for entry reference
        current_bid = current_price.get('bid', 0)
        current_ask = current_price.get('ask', 0)
        
        system_prompt = f"""Anda adalah trader agresif XAUUSD. SELALU ENTRY setiap analisa, jangan terlalu sering WAIT.

ATURAN ENTRY (AKTIF):
1. SELALU pilih BUY atau SELL, hindari WAIT kecuali benar-benar tidak ada signal
2. Jika candle terakhir bullish -> BUY
3. Jika candle terakhir bearish -> SELL
4. Jika harga di HIGH (resistance) -> SELL
5. Jika harga di LOW (support) -> BUY

ANTI BIAS - SANGAT PENTING:
- JANGAN selalu BUY! Lihat market structure
- Jika 2+ candle turun berturut -> kemungkinan besar SELL, BUKAN BUY
- Jika 2+ candle naik berturut -> kemungkinan besar BUY, BUKAN SELL
- Ikuti ARAH candle terakhir, jangan melawan

SL/TP:
- SL: 80 pips = 8 point
- TP: 50 pips = 5 point

BUY di {current_ask:.2f}: SL={current_ask - 8:.2f}, TP={current_ask + 5:.2f}
SELL di {current_bid:.2f}: SL={current_bid + 8:.2f}, TP={current_bid - 5:.2f}

OUTPUT (JSON):
{{
    "decision": "BUY" | "SELL" | "WAIT",
    "entry_price": float,
    "SL": float,
    "TP": float,
    "sl_pips": 80,
    "tp_pips": 50,
    "rr_ratio": float,
    "confidence": 0-100,
    "reason": "alasan"
}}"""

        user_prompt = f"""ANALISA {symbol} - HARUS ENTRY!

HARGA: Bid={current_bid:.2f}, Ask={current_ask:.2f}

H1 CANDLES:
{h1_summary}

M15 CANDLES:
{m15_summary}

PILIH SATU - BUY atau SELL:
- Jika candle terakhir HIJAU/bullish -> BUY
- Jika candle terakhir MERAH/bearish -> SELL
- Jangan WAIT kecuali signal sangat conflicting"""

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    
    def _build_guardian_prompt(
        self,
        position: Dict,
        current_price: Dict,
        candles_m15: List[Dict],
        trading_config: TradingConfig
    ) -> List[Dict]:
        """Build prompt for guardian (position monitoring) analysis"""
        
        m15_summary = self._summarize_candles(candles_m15[-10:]) if candles_m15 else "No data"
        
        # Calculate current P/L in pips
        if position['type'] == 'BUY':
            pips_pl = (current_price.get('bid', position['open_price']) - position['open_price']) * 10
        else:
            pips_pl = (position['open_price'] - current_price.get('ask', position['open_price'])) * 10
        
        system_prompt = f"""Anda adalah Supervisor Risiko (Risk Manager AI) dengan mentalitas "STRATEGIC HOLDER".
Tugas: Mengelola posisi trading dengan kesabaran dan disiplin.

ATURAN GUARDIAN:
1. Auto-BEP: Jika profit >= {trading_config.auto_bep_pips} pips, pindahkan SL ke Break Even
2. Trailing Stop: Jika enabled, trail SL setiap {trading_config.trailing_stop_pips} pips
3. CLOSE hanya jika ada reversal pattern yang JELAS atau target tercapai
4. JANGAN close terlalu cepat - biarkan profit berjalan
5. ADD_DCA: Jika ada sinyal KUAT searah posisi (momentum candle besar + volume tinggi)

KRITERIA ADD_DCA (Momentum DCA):
- Candle M15 terakhir BULLISH BESAR (body > 80% range) untuk posisi BUY
- Candle M15 terakhir BEARISH BESAR (body > 80% range) untuk posisi SELL
- Minimal 2-3 candle terakhir searah (momentum kuat)
- HANYA jika masih ada slot posisi tersedia

OUTPUT FORMAT (JSON):
{{
    "action": "HOLD" | "MODIFY_SL" | "MODIFY_TP" | "CLOSE" | "ADD_DCA",
    "new_sl": float atau null,
    "new_tp": float atau null,
    "dca_reason": "alasan DCA jika action ADD_DCA" atau null,
    "momentum_strength": "WEAK" | "MEDIUM" | "STRONG" (wajib jika ADD_DCA),
    "reason": "Penjelasan singkat dalam Bahasa Indonesia"
}}"""

        user_prompt = f"""MONITOR POSISI

DETAIL POSISI:
- Ticket: {position['ticket']}
- Symbol: {position['symbol']}
- Type: {position['type']}
- Volume: {position['volume']}
- Open Price: {position['open_price']}
- Current SL: {position['sl']}
- Current TP: {position['tp']}
- Current Profit: ${position['profit']} ({pips_pl:.1f} pips)
- Open Time: {position['time']}

HARGA SAAT INI:
- Bid: {current_price.get('bid', 'N/A')}
- Ask: {current_price.get('ask', 'N/A')}

DATA CANDLE M15 (10 terakhir) - ANALISA MOMENTUM:
{m15_summary}

KONFIGURASI:
- Auto-BEP Enabled: {trading_config.auto_bep_enabled}
- Auto-BEP Trigger: {trading_config.auto_bep_pips} pips
- Trailing Stop: {trading_config.trailing_stop_enabled}

INSTRUKSI:
1. Evaluasi posisi
2. Jika candle terakhir menunjukkan MOMENTUM KUAT searah posisi → ADD_DCA
3. Jika tidak ada momentum kuat → HOLD atau kelola SL/TP biasa"""

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    
    def _summarize_candles(self, candles: List[Dict]) -> str:
        """Create a summary of candle data"""
        if not candles:
            return "No data available"
        
        lines = []
        for c in candles[-10:]:  # Last 10 candles
            time_str = c.get('time', 'N/A')
            if hasattr(time_str, 'strftime'):
                time_str = time_str.strftime('%Y-%m-%d %H:%M')
            
            o, h, l, close = c.get('open', 0), c.get('high', 0), c.get('low', 0), c.get('close', 0)
            direction = "▲" if close > o else "▼" if close < o else "─"
            lines.append(f"{time_str}: O={o:.2f} H={h:.2f} L={l:.2f} C={close:.2f} {direction}")
        
        return "\n".join(lines)
    
    async def analyze_entry(
        self,
        symbol: str,
        current_price: Dict,
        candles_h1: List[Dict],
        candles_m15: List[Dict],
        trading_config: TradingConfig
    ) -> Dict[str, Any]:
        """Analyze market and decide on entry"""
        
        messages = self._build_entry_prompt(
            symbol, current_price, candles_h1, candles_m15, trading_config
        )
        
        result = await self._call_ai(messages)
        
        # Log reasoning
        entry = {
            "timestamp": datetime.now().isoformat(),
            "symbol": symbol,
            "type": "ENTRY",
            "provider": self.provider,
            "result": result
        }
        self.reasoning_history.append(entry)
        
        # Keep only last 100 entries and save to file
        if len(self.reasoning_history) > 100:
            self.reasoning_history = self.reasoning_history[-100:]
        self._save_history()
        
        return result
    
    async def guardian_check(
        self,
        position: Dict,
        current_price: Dict,
        candles_m15: List[Dict],
        trading_config: TradingConfig
    ) -> Dict[str, Any]:
        """Check and manage existing position"""
        
        messages = self._build_guardian_prompt(
            position, current_price, candles_m15, trading_config
        )
        
        result = await self._call_ai(messages)
        
        # Log reasoning
        entry = {
            "timestamp": datetime.now().isoformat(),
            "symbol": position['symbol'],
            "ticket": position['ticket'],
            "type": "GUARDIAN",
            "provider": self.provider,
            "result": result
        }
        self.reasoning_history.append(entry)
        
        # Keep only last 100 entries and save to file
        if len(self.reasoning_history) > 100:
            self.reasoning_history = self.reasoning_history[-100:]
        self._save_history()
        
        return result
    
    def get_reasoning_history(self, limit: int = 20) -> List[Dict]:
        """Get recent AI reasoning history"""
        return self.reasoning_history[-limit:]
    
    def switch_provider(self, provider: str):
        """Switch AI provider"""
        if provider in ['groq', 'deepseek']:
            self.provider = provider
            logger.info(f"Switched AI provider to: {provider}")


# Singleton instance
_brain: Optional[AIBrain] = None

def get_ai_brain(config: Optional[AIConfig] = None) -> AIBrain:
    """Get or create AI brain instance"""
    global _brain
    if _brain is None and config:
        _brain = AIBrain(config)
    return _brain
