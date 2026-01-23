"""
WebSocket connection manager for real-time chat.
Handles WebSocket connections, disconnections, and message broadcasting.
"""
import json
import logging
from typing import Dict, Set, Optional, Any
from datetime import datetime, timedelta
from fastapi import WebSocket, WebSocketDisconnect
import asyncio

logger = logging.getLogger(__name__)


# SECURITY: Configuration for connection rate limiting
MAX_CONNECTIONS_PER_USER = 5  # Maximum concurrent connections per user
MAX_CONNECTION_ATTEMPTS_PER_MINUTE = 10  # Rate limit for connection attempts
CONNECTION_ATTEMPT_WINDOW_SECONDS = 60  # Window for rate limiting


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
        # SECURITY: Track connection attempts for rate limiting (user_id -> list of timestamps)
        self._connection_attempts: Dict[str, list] = {}
        # SECURITY: Track connection attempts by IP for additional protection
        self._ip_connection_attempts: Dict[str, list] = {}

    def _clean_old_attempts(self, attempts: list) -> list:
        """Remove connection attempts older than the rate limit window."""
        cutoff = datetime.utcnow() - timedelta(seconds=CONNECTION_ATTEMPT_WINDOW_SECONDS)
        return [ts for ts in attempts if ts > cutoff]

    def _check_rate_limit(self, identifier: str, attempts_dict: Dict[str, list]) -> bool:
        """
        Check if an identifier (user_id or IP) has exceeded rate limits.

        Returns:
            True if within limits, False if rate limited
        """
        if identifier not in attempts_dict:
            attempts_dict[identifier] = []

        # Clean old attempts
        attempts_dict[identifier] = self._clean_old_attempts(attempts_dict[identifier])

        # Check if under limit
        return len(attempts_dict[identifier]) < MAX_CONNECTION_ATTEMPTS_PER_MINUTE

    def _record_attempt(self, identifier: str, attempts_dict: Dict[str, list]) -> None:
        """Record a connection attempt for rate limiting."""
        if identifier not in attempts_dict:
            attempts_dict[identifier] = []
        attempts_dict[identifier].append(datetime.utcnow())

    async def connect(
        self,
        websocket: WebSocket,
        user_id: str,
        user_phase: str = "goal_setting",
        session_id: Optional[str] = None,
        client_ip: Optional[str] = None,
    ) -> bool:
        """
        Accept a new WebSocket connection with rate limiting.

        SECURITY: Implements rate limiting to prevent connection flooding attacks.

        Args:
            websocket: The WebSocket connection
            user_id: The user's ID
            user_phase: The user's current phase
            session_id: Unique session identifier for context tracking
            client_ip: Client IP address for additional rate limiting

        Returns:
            True if connection successful, False otherwise
        """
        try:
            async with self._lock:
                # SECURITY: Check rate limits before accepting connection
                if not self._check_rate_limit(user_id, self._connection_attempts):
                    logger.warning(f"Rate limit exceeded for user {user_id}")
                    return False

                if client_ip and not self._check_rate_limit(client_ip, self._ip_connection_attempts):
                    logger.warning(f"Rate limit exceeded for IP {client_ip}")
                    return False

                # SECURITY: Check concurrent connection limit per user
                current_count = self.get_user_connection_count(user_id)
                if current_count >= MAX_CONNECTIONS_PER_USER:
                    logger.warning(f"Max connections ({MAX_CONNECTIONS_PER_USER}) exceeded for user {user_id}")
                    return False

                # Record the connection attempt for rate limiting
                self._record_attempt(user_id, self._connection_attempts)
                if client_ip:
                    self._record_attempt(client_ip, self._ip_connection_attempts)

            await websocket.accept()

            async with self._lock:
                # Add to user's connections
                if user_id not in self.active_connections:
                    self.active_connections[user_id] = set()
                self.active_connections[user_id].add(websocket)

                # Store connection info with session tracking
                self.connection_info[websocket] = {
                    "user_id": user_id,
                    "user_phase": user_phase,
                    "session_id": session_id,
                    "client_ip": client_ip,
                    "connected_at": datetime.utcnow().isoformat(),
                    "message_count": 0,  # Track messages for periodic context save
                }

            logger.info(f"WebSocket connected for user {user_id}, session {session_id}")
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

    def increment_message_count(self, websocket: WebSocket) -> int:
        """
        Increment message count for a connection and return the new count.

        Args:
            websocket: The WebSocket connection

        Returns:
            The new message count, or 0 if connection not found
        """
        if websocket in self.connection_info:
            self.connection_info[websocket]["message_count"] = (
                self.connection_info[websocket].get("message_count", 0) + 1
            )
            return self.connection_info[websocket]["message_count"]
        return 0

    def should_save_context(self, websocket: WebSocket, threshold: int = 1000) -> bool:
        """
        Check if the connection has reached the message threshold for periodic context save.

        Args:
            websocket: The WebSocket connection
            threshold: Message count threshold for triggering save

        Returns:
            True if message count is at or exceeds threshold and is a multiple of threshold
        """
        if websocket in self.connection_info:
            count = self.connection_info[websocket].get("message_count", 0)
            # Save at every threshold multiple (1000, 2000, 3000, etc.)
            return count > 0 and count % threshold == 0
        return False

    def reset_message_count(self, websocket: WebSocket) -> None:
        """
        Reset the message count for a connection (after context save).

        Args:
            websocket: The WebSocket connection
        """
        if websocket in self.connection_info:
            self.connection_info[websocket]["message_count"] = 0

    def get_session_id(self, websocket: WebSocket) -> Optional[str]:
        """
        Get the session ID for a connection.

        Args:
            websocket: The WebSocket connection

        Returns:
            The session ID or None if not found
        """
        info = self.connection_info.get(websocket)
        return info.get("session_id") if info else None


# Global connection manager instance
connection_manager = ConnectionManager()


def get_connection_manager() -> ConnectionManager:
    """Get the global connection manager instance."""
    return connection_manager
