"""
WebSocket Manager - Real-time communication with frontend
"""
from fastapi import WebSocket
from typing import List, Dict, Any
import json
import asyncio
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WebSocketManager:
    """Manages WebSocket connections and broadcasts"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self._lock = asyncio.Lock()
    
    async def connect(self, websocket: WebSocket):
        """Accept and store new WebSocket connection"""
        await websocket.accept()
        async with self._lock:
            self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Total: {len(self.active_connections)}")
    
    async def disconnect(self, websocket: WebSocket):
        """Remove disconnected WebSocket"""
        async with self._lock:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Total: {len(self.active_connections)}")
    
    async def broadcast(self, message_type: str, data: Any):
        """Broadcast message to all connected clients"""
        if not self.active_connections:
            return
        
        message = json.dumps({
            "type": message_type,
            "data": data
        })
        
        disconnected = []
        
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.warning(f"Failed to send to client: {e}")
                disconnected.append(connection)
        
        # Clean up disconnected clients
        for conn in disconnected:
            await self.disconnect(conn)
    
    async def send_personal(self, websocket: WebSocket, message_type: str, data: Any):
        """Send message to specific client"""
        try:
            message = json.dumps({
                "type": message_type,
                "data": data
            })
            await websocket.send_text(message)
        except Exception as e:
            logger.error(f"Failed to send personal message: {e}")
    
    # Convenience methods for specific message types
    
    async def broadcast_status(self, status: Dict):
        """Broadcast bot status update"""
        await self.broadcast("status", status)
    
    async def broadcast_account(self, account: Dict):
        """Broadcast account info update"""
        await self.broadcast("account", account)
    
    async def broadcast_positions(self, positions: List[Dict]):
        """Broadcast positions update"""
        await self.broadcast("positions", positions)
    
    async def broadcast_price(self, price: Dict):
        """Broadcast price update"""
        await self.broadcast("price", price)
    
    async def broadcast_reasoning(self, reasoning: Dict):
        """Broadcast AI reasoning entry"""
        await self.broadcast("reasoning", reasoning)
    
    async def broadcast_trade(self, trade: Dict):
        """Broadcast trade execution notification"""
        await self.broadcast("trade", trade)
    
    async def broadcast_error(self, error: str):
        """Broadcast error message"""
        await self.broadcast("error", {"message": error})


# Singleton instance
ws_manager = WebSocketManager()

def get_ws_manager() -> WebSocketManager:
    """Get WebSocket manager instance"""
    return ws_manager
