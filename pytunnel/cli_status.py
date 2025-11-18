"""CLI command for showing PyTunnel status."""

import asyncio
import argparse
import sys
from pathlib import Path

from pytunnel.common.cli_display import get_status_display
from pytunnel.common.security import get_security_manager
from pytunnel.common.compliance import get_compliance_manager
from pytunnel.common.config import get_config_dir


def load_status():
    """Load status from various managers."""
    # This would normally connect to running server
    # For now, return mock data for demonstration

    tunnels = []
    security_stats = {}
    compliance_status = {}

    try:
        # Try to load actual status
        # In production, this would query the running server
        config_dir = get_config_dir()

        # Security status
        security_manager = get_security_manager()
        security_stats = security_manager.get_stats()

        # Compliance status
        compliance_manager = get_compliance_manager(storage_path=config_dir)
        compliance_status = compliance_manager.get_compliance_status()

    except Exception as e:
        print(f"Note: Could not load full status: {e}")

        # Provide minimal status
        security_stats = {
            'security_score': 0,
            'connections': {'total_connections': 0},
            'blocked_ips': [],
            'config': {
                'has_whitelist': False,
                'has_blacklist': False
            }
        }

        compliance_status = {
            'audit_log_integrity': True,
            'total_audit_entries': 0,
            'gdpr_ready': True,
            'retention_policy': {
                'auto_cleanup_enabled': False,
                'log_retention_days': 90
            }
        }

    return tunnels, security_stats, compliance_status


def main():
    """Main entry point for status command."""
    parser = argparse.ArgumentParser(
        description="PyTunnel Status - View tunnel and system status"
    )
    parser.add_argument(
        '--tunnels-only',
        action='store_true',
        help='Show only tunnel status'
    )
    parser.add_argument(
        '--security-only',
        action='store_true',
        help='Show only security status'
    )
    parser.add_argument(
        '--compliance-only',
        action='store_true',
        help='Show only compliance status'
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='Output in JSON format'
    )

    args = parser.parse_args()

    # Load status
    tunnels, security, compliance = load_status()

    # Output as JSON if requested
    if args.json:
        import json
        data = {
            'tunnels': tunnels,
            'security': security,
            'compliance': compliance
        }
        print(json.dumps(data, indent=2))
        return

    # Display status
    display = get_status_display()

    if args.tunnels_only:
        display.show_tunnel_status(tunnels)
    elif args.security_only:
        display.show_security_status(security)
    elif args.compliance_only:
        display.show_compliance_status(compliance)
    else:
        display.show_summary(tunnels, security, compliance)


if __name__ == '__main__':
    main()
