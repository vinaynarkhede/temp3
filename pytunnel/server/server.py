"""Main tunnel server implementation."""

import asyncio
from typing import Dict, Optional
from aiohttp import web, WSMsgType
import aiohttp
from pytunnel.common.protocol import (
    TunnelMessage, MessageType, create_register_ack,
    create_http_request, create_error_message
)
from pytunnel.common.utils import setup_logger, generate_request_id


class TunnelServer:
    """Tunnel server that manages client connections and proxies HTTP requests."""

    def __init__(self, host: str = "0.0.0.0", port: int = 8080,
                 tunnel_port: int = 4040):
        self.host = host
        self.port = port  # HTTP proxy port
        self.tunnel_port = tunnel_port  # WebSocket tunnel port
        self.clients: Dict[str, aiohttp.web.WebSocketResponse] = {}
        self.pending_requests: Dict[str, asyncio.Future] = {}
        self.logger = setup_logger("TunnelServer")

    async def handle_websocket(self, request: web.Request) -> web.WebSocketResponse:
        """Handle WebSocket connections from tunnel clients."""
        ws = web.WebSocketResponse()
        await ws.prepare(request)

        client_id = None
        self.logger.info("New WebSocket connection established")

        try:
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    try:
                        tunnel_msg = TunnelMessage.from_json(msg.data)

                        if tunnel_msg.msg_type == MessageType.REGISTER:
                            client_id = tunnel_msg.data.get("client_id")
                            self.clients[client_id] = ws

                            tunnel_url = f"http://{self.host}:{self.port}/{client_id}"
                            ack_msg = create_register_ack(client_id, tunnel_url)
                            await ws.send_str(ack_msg.to_json())

                            self.logger.info(
                                f"Client registered: {client_id} -> {tunnel_url}"
                            )

                        elif tunnel_msg.msg_type == MessageType.HTTP_RESPONSE:
                            request_id = tunnel_msg.request_id
                            if request_id in self.pending_requests:
                                future = self.pending_requests.pop(request_id)
                                if not future.done():
                                    future.set_result(tunnel_msg)

                        elif tunnel_msg.msg_type == MessageType.ERROR:
                            request_id = tunnel_msg.request_id
                            if request_id in self.pending_requests:
                                future = self.pending_requests.pop(request_id)
                                if not future.done():
                                    future.set_exception(
                                        Exception(tunnel_msg.data.get("error"))
                                    )

                    except Exception as e:
                        self.logger.error(f"Error processing message: {e}")

                elif msg.type == WSMsgType.ERROR:
                    self.logger.error(f'WebSocket error: {ws.exception()}')

        finally:
            if client_id and client_id in self.clients:
                del self.clients[client_id]
                self.logger.info(f"Client disconnected: {client_id}")

        return ws

    async def handle_http_request(self, request: web.Request) -> web.Response:
        """Handle incoming HTTP requests and proxy them through the tunnel."""
        # Extract client_id from path
        path = request.path.lstrip('/')
        parts = path.split('/', 1)

        if not parts or not parts[0]:
            return web.Response(
                text="PyTunnel Server - Please specify a tunnel ID in the path",
                status=400
            )

        client_id = parts[0]
        remaining_path = '/' + parts[1] if len(parts) > 1 else '/'

        if client_id not in self.clients:
            return web.Response(
                text=f"Tunnel not found: {client_id}",
                status=404
            )

        ws = self.clients[client_id]
        request_id = generate_request_id()

        # Read request body
        body = await request.read()

        # Convert headers to dict
        headers = dict(request.headers)

        # Create HTTP request message
        req_msg = create_http_request(
            request_id=request_id,
            method=request.method,
            path=remaining_path + ('?' + request.query_string if request.query_string else ''),
            headers=headers,
            body=body
        )

        # Create future for response
        future = asyncio.Future()
        self.pending_requests[request_id] = future

        try:
            # Send request through tunnel
            await ws.send_str(req_msg.to_json())
            self.logger.info(
                f"Forwarded {request.method} request to {client_id}{remaining_path}"
            )

            # Wait for response (with timeout)
            response_msg = await asyncio.wait_for(future, timeout=30.0)

            # Build response
            status = response_msg.data.get("status", 200)
            response_headers = response_msg.data.get("headers", {})
            response_body = response_msg.data.get("body", "")

            return web.Response(
                text=response_body,
                status=status,
                headers=response_headers
            )

        except asyncio.TimeoutError:
            self.logger.error(f"Request timeout for {request_id}")
            if request_id in self.pending_requests:
                del self.pending_requests[request_id]
            return web.Response(
                text="Gateway timeout - no response from tunnel",
                status=504
            )

        except Exception as e:
            self.logger.error(f"Error proxying request: {e}")
            if request_id in self.pending_requests:
                del self.pending_requests[request_id]
            return web.Response(
                text=f"Internal server error: {str(e)}",
                status=500
            )

    async def start(self):
        """Start the tunnel server."""
        app = web.Application()

        # WebSocket endpoint for tunnel connections
        app.router.add_get('/tunnel', self.handle_websocket)

        # HTTP proxy endpoint
        app.router.add_route('*', '/{tail:.*}', self.handle_http_request)

        runner = web.AppRunner(app)
        await runner.setup()

        # Start HTTP proxy server
        site = web.TCPSite(runner, self.host, self.port)
        await site.start()

        self.logger.info(f"HTTP Proxy listening on http://{self.host}:{self.port}")
        self.logger.info(f"WebSocket Tunnel listening on ws://{self.host}:{self.port}/tunnel")
        self.logger.info("Server started successfully!")

        # Keep running
        try:
            await asyncio.Event().wait()
        except KeyboardInterrupt:
            self.logger.info("Shutting down server...")
            await runner.cleanup()
