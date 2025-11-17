"""Main tunnel client implementation."""

import asyncio
import aiohttp
from typing import Optional
from pytunnel.common.protocol import (
    TunnelMessage, MessageType, create_register_message,
    create_http_response, create_error_message
)
from pytunnel.common.utils import setup_logger, generate_client_id


class TunnelClient:
    """Tunnel client that connects to the server and forwards requests to local services."""

    def __init__(self, server_url: str, local_host: str = "localhost",
                 local_port: int = 3000, client_id: Optional[str] = None):
        self.server_url = server_url
        self.local_host = local_host
        self.local_port = local_port
        self.client_id = client_id or generate_client_id()
        self.tunnel_url: Optional[str] = None
        self.logger = setup_logger("TunnelClient")
        self.ws: Optional[aiohttp.ClientWebSocketResponse] = None

    async def forward_to_local(self, tunnel_msg: TunnelMessage) -> TunnelMessage:
        """Forward HTTP request to local service and return response."""
        try:
            method = tunnel_msg.data.get("method", "GET")
            path = tunnel_msg.data.get("path", "/")
            headers = tunnel_msg.data.get("headers", {})
            body = tunnel_msg.data.get("body", "")

            # Build local URL
            local_url = f"http://{self.local_host}:{self.local_port}{path}"

            self.logger.info(f"Forwarding {method} {path} to {local_url}")

            # Make request to local service
            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method=method,
                    url=local_url,
                    headers=headers,
                    data=body.encode('utf-8') if body else None,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    response_body = await response.read()
                    response_headers = dict(response.headers)

                    # Create response message
                    response_msg = create_http_response(
                        request_id=tunnel_msg.request_id,
                        status=response.status,
                        headers=response_headers,
                        body=response_body
                    )

                    self.logger.info(
                        f"Response from local service: {response.status}"
                    )

                    return response_msg

        except asyncio.TimeoutError:
            self.logger.error("Timeout connecting to local service")
            return create_error_message(
                request_id=tunnel_msg.request_id,
                error="Timeout connecting to local service"
            )

        except aiohttp.ClientError as e:
            self.logger.error(f"Error connecting to local service: {e}")
            return create_error_message(
                request_id=tunnel_msg.request_id,
                error=f"Error connecting to local service: {str(e)}"
            )

        except Exception as e:
            self.logger.error(f"Unexpected error: {e}")
            return create_error_message(
                request_id=tunnel_msg.request_id,
                error=f"Unexpected error: {str(e)}"
            )

    async def handle_message(self, tunnel_msg: TunnelMessage):
        """Handle incoming messages from the tunnel server."""
        if tunnel_msg.msg_type == MessageType.REGISTER_ACK:
            self.tunnel_url = tunnel_msg.data.get("tunnel_url")
            self.logger.info(f"Tunnel established! URL: {self.tunnel_url}")
            print(f"\n{'='*60}")
            print(f"  Tunnel URL: {self.tunnel_url}")
            print(f"  Forwarding to: http://{self.local_host}:{self.local_port}")
            print(f"{'='*60}\n")

        elif tunnel_msg.msg_type == MessageType.HTTP_REQUEST:
            # Forward request to local service
            response_msg = await self.forward_to_local(tunnel_msg)

            # Send response back through tunnel
            if self.ws:
                await self.ws.send_str(response_msg.to_json())

    async def connect(self):
        """Connect to the tunnel server."""
        # Parse server URL to get WebSocket URL
        ws_url = self.server_url.replace('http://', 'ws://').replace('https://', 'wss://')
        if not ws_url.endswith('/tunnel'):
            ws_url = ws_url.rstrip('/') + '/tunnel'

        self.logger.info(f"Connecting to tunnel server: {ws_url}")

        async with aiohttp.ClientSession() as session:
            try:
                async with session.ws_connect(ws_url) as ws:
                    self.ws = ws
                    self.logger.info("Connected to tunnel server")

                    # Send registration message
                    reg_msg = create_register_message(self.client_id)
                    await ws.send_str(reg_msg.to_json())
                    self.logger.info(f"Sent registration for client: {self.client_id}")

                    # Handle incoming messages
                    async for msg in ws:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            try:
                                tunnel_msg = TunnelMessage.from_json(msg.data)
                                await self.handle_message(tunnel_msg)
                            except Exception as e:
                                self.logger.error(f"Error handling message: {e}")

                        elif msg.type == aiohttp.WSMsgType.ERROR:
                            self.logger.error(f"WebSocket error: {ws.exception()}")
                            break

                        elif msg.type == aiohttp.WSMsgType.CLOSED:
                            self.logger.info("WebSocket connection closed")
                            break

            except aiohttp.ClientError as e:
                self.logger.error(f"Connection error: {e}")
                raise

            except Exception as e:
                self.logger.error(f"Unexpected error: {e}")
                raise

    async def start(self):
        """Start the tunnel client with auto-reconnect."""
        while True:
            try:
                await self.connect()
            except KeyboardInterrupt:
                self.logger.info("Client stopped by user")
                break
            except Exception as e:
                self.logger.error(f"Connection lost: {e}")
                self.logger.info("Reconnecting in 5 seconds...")
                await asyncio.sleep(5)
