import asyncio
import json
import logging
import websockets

logger = logging.getLogger(__name__)

class WSServer:
    """
    Reusable WebSocket server used across multiple projects.
    Manages:
      - connected clients
      - broadcast
      - lifecycle of WS server
    """

    def __init__(self, host="0.0.0.0", port=6106):
        self.host = host
        self.port = port
        self.clients = set()

    # ----------------------------------------------------
    # Connection Handler
    # ----------------------------------------------------
    async def handler(self, ws):
        """Handle new websocket clients."""
        self.clients.add(ws)
        logger.info(f"[handler] WS client connected. Total clients: {len(self.clients)}")

        try:
            async for _ in ws:
                pass  # WS is one-way for now (server → client)

        except Exception as e:
            logger.error(f"[handler] @@@ WS handler error: {e}")

        finally:
            self.clients.discard(ws)
            logger.info(f"[handler] WS client disconnected. Total clients: {len(self.clients)}")

    # ----------------------------------------------------
    # Broadcast
    # ----------------------------------------------------
    async def broadcast(self, message: dict):
        """Send a JSON message to all connected clients."""
        if not self.clients:
            logger.info("[broadcast] No WS clients — skipping broadcast.")
            return

        payload = json.dumps(message)
        await asyncio.gather(*[
            ws.send(payload) for ws in list(self.clients)
        ], return_exceptions=True)

        logger.info(f"[broadcast] Broadcasted to {len(self.clients)} clients")

    # ----------------------------------------------------
    # Start WS Server
    # ----------------------------------------------------
    async def start(self):
        """Start WebSocket server."""
        logger.info(f"Starting WebSocket server on ws://{self.host}:{self.port}")
        return websockets.serve(self.handler, self.host, self.port)
