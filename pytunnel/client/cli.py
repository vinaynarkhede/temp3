"""CLI interface for the tunnel client."""

import asyncio
import argparse
from pytunnel.client.client import TunnelClient


def main():
    """Main entry point for the client CLI."""
    parser = argparse.ArgumentParser(
        description="PyTunnel Client - Connect to tunnel server and expose local services"
    )
    parser.add_argument(
        "local_port",
        type=int,
        help="Local port to forward requests to"
    )
    parser.add_argument(
        "--server",
        default="http://localhost:8080",
        help="Tunnel server URL (default: http://localhost:8080)"
    )
    parser.add_argument(
        "--local-host",
        default="localhost",
        help="Local host to forward to (default: localhost)"
    )
    parser.add_argument(
        "--client-id",
        help="Custom client ID (default: auto-generated)"
    )

    args = parser.parse_args()

    client = TunnelClient(
        server_url=args.server,
        local_host=args.local_host,
        local_port=args.local_port,
        client_id=args.client_id
    )

    print("PyTunnel Client")
    print(f"Connecting to server: {args.server}")
    print(f"Local service: http://{args.local_host}:{args.local_port}")
    print("")

    try:
        asyncio.run(client.start())
    except KeyboardInterrupt:
        print("\n\nClient stopped by user")


if __name__ == "__main__":
    main()
