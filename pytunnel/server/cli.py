"""CLI interface for the tunnel server."""

import asyncio
import argparse
from pytunnel.server.server import TunnelServer


def main():
    """Main entry point for the server CLI."""
    parser = argparse.ArgumentParser(
        description="PyTunnel Server - Expose local servers to the internet"
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind to (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="Port for HTTP proxy (default: 8080)"
    )

    args = parser.parse_args()

    server = TunnelServer(host=args.host, port=args.port)

    try:
        asyncio.run(server.start())
    except KeyboardInterrupt:
        print("\nServer stopped by user")


if __name__ == "__main__":
    main()
