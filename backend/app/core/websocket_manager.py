"""
WebSocket connection manager for real-time chat.
Handles WebSocket connections, disconnections, and message broadcasting.
"""
import json
import logging
from typing import Dict, Set, Optional, Any
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect
import asyncio

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Manages WebSocket connections for real-time chat functionality.
    Supports multiple connections per user and room-based messaging.
    """

    def __init__(self):
        """Initialize the connection manager."""
        # Maps user_id to set of active WebSocket connections
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        # Maps WebSocket to user info for quick lookup
        self.connection_info: Dict[WebSocket, Dict[str, Any]] = {}
        # Lock for thread-safe operations
        self._lock = asyncio.Lock()

    async def connect(
        self,
        websocket: WebSocket,
        user_id: str,
        user_phase: str = "goal_setting",
    ) -> bool:
        """
        Accept a new WebSocket connection.

        Args:
            websocket: The WebSocket connection
            user_id: The user's ID
            user_phase: The user's current phase

        Returns:
            True if connection successful, False otherwise
        """
        try:
            await websocket.accept()

            async with self._lock:
                # Add to user's connections
                if user_id not in self.active_connections:
                    self.active_connections[user_id] = set()
                self.active_connections[user_id].add(websocket)

                # Store connection info
                self.connection_info[websocket] = {
                    "user_id": user_id,
                    "user_phase": user_phase,
                    "connected_at": datetime.utcnow().isoformat(),
                }

            logger.info(f"WebSocket connected for user {user_id}")
            return True

        except Exception as e:
            logger.error(f"Error connecting WebSocket for user {user_id}: {e}")
            return False

    async def disconnect(self, websocket: WebSocket) -> Optional[str]:
        """
        Handle WebSocket disconnection.

        Args:
            websocket: The WebSocket connection to remove

        Returns:
            The user_id of the disconnected user, or None if not found
        """
        async with self._lock:
            # Get user info before removing
            info = self.connection_info.pop(websocket, None)
            if not info:
                return None

            user_id = info["user_id"]

            # Remove from user's connections
            if user_id in self.active_connections:
                self.active_connections[user_id].discard(websocket)

                # Clean up empty sets
                if not self.active_connections[user_id]:
                    del self.active_connections[user_id]

            logger.info(f"WebSocket disconnected for user {user_id}")
            return user_id

    async def send_personal_message(
        self,
        message: Dict[str, Any],
        websocket: WebSocket,
    ) -> bool:
        """
        Send a message to a specific WebSocket connection.

        Args:
            message: The message dict to send
            websocket: The target WebSocket connection

        Returns:
            True if message sent successfully, False otherwise
        """
        try:
            await websocket.send_json(message)
            return True
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
            return False

    async def send_to_user(
        self,
        message: Dict[str, Any],
        user_id: str,
    ) -> int:
        """
        Send a message to all connections for a specific user.

        Args:
            message: The message dict to send
            user_id: The target user's ID

        Returns:
            Number of successful sends
        """
        if user_id not in self.active_connections:
            return 0

        sent_count = 0
        disconnected = []

        for websocket in self.active_connections[user_id].copy():
            try:
                await websocket.send_json(message)
                sent_count += 1
            except Exception as e:
                logger.warning(f"Failed to send to user {user_id}: {e}")
                disconnected.append(websocket)

        # Clean up failed connections
        for ws in disconnected:
            await self.disconnect(ws)

        return sent_count

    async def broadcast(
        self,
        message: Dict[str, Any],
        exclude_user: Optional[str] = None,
    ) -> int:
        """
        Broadcast a message to all connected users.

        Args:
            message: The message dict to send
            exclude_user: Optional user_id to exclude from broadcast

        Returns:
            Number of successful sends
        """
        sent_count = 0

        for user_id, connections in list(self.active_connections.items()):
            if exclude_user and user_id == exclude_user:
                continue

            for websocket in connections.copy():
                try:
                    await websocket.send_json(message)
                    sent_count += 1
                except Exception:
                    await self.disconnect(websocket)

        return sent_count

    def is_user_connected(self, user_id: str) -> bool:
        """Check if a user has any active connections."""
        return user_id in self.active_connections and len(self.active_connections[user_id]) > 0

    def get_user_connection_count(self, user_id: str) -> int:
        """Get the number of active connections for a user."""
        if user_id not in self.active_connections:
            return 0
        return len(self.active_connections[user_id])

    def get_total_connections(self) -> int:
        """Get the total number of active connections."""
        return sum(len(conns) for conns in self.active_connections.values())

    def get_connection_info(self, websocket: WebSocket) -> Optional[Dict[str, Any]]:
        """Get info about a specific connection."""
        return self.connection_info.get(websocket)

    async def update_user_phase(self, user_id: str, new_phase: str) -> None:
        """
        Update the phase for all connections of a user.

        Args:
            user_id: The user's ID
            new_phase: The new phase to set
        """
        async with self._lock:
            if user_id in self.active_connections:
                for websocket in self.active_connections[user_id]:
                    if websocket in self.connection_info:
                        self.connection_info[websocket]["user_phase"] = new_phase


# Global connection manager instance
connection_manager = ConnectionManager()


def get_connection_manager() -> ConnectionManager:
    """Get the global connection manager instance."""
    return connection_manager
