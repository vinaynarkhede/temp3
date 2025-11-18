"""Dashboard API endpoints."""

from aiohttp import web
from typing import Dict, Any, List
import time
from pytunnel.common.traffic import get_traffic_inspector
from pytunnel.common.subdomains import get_subdomain_manager


class DashboardAPI:
    """API handler for dashboard data."""

    def __init__(self, server):
        self.server = server
        self.traffic_inspector = get_traffic_inspector()
        self.subdomain_manager = get_subdomain_manager()

    async def get_stats(self, request: web.Request) -> web.Response:
        """Get overall statistics."""
        # Get active tunnels count
        active_tunnels = len(self.server.clients)

        # Get traffic stats
        all_stats = self.traffic_inspector.get_stats()

        total_requests = sum(
            stats.get('total_requests', 0)
            for stats in all_stats.values()
        )

        total_bandwidth = sum(
            stats.get('total_bytes_in', 0) + stats.get('total_bytes_out', 0)
            for stats in all_stats.values()
        )

        avg_response = 0
        if all_stats:
            avg_response = sum(
                stats.get('avg_response_time', 0)
                for stats in all_stats.values()
            ) / len(all_stats)

        # Get tunnel details
        tunnels = []
        for client_id, ws in self.server.clients.items():
            stats = all_stats.get(client_id, {})
            subdomain = self.subdomain_manager.get_subdomain_for_client(client_id)

            tunnels.append({
                'client_id': client_id,
                'subdomain': subdomain,
                'status': 'active',
                'requests': stats.get('total_requests', 0),
                'bandwidth': stats.get('total_bytes_in', 0) + stats.get('total_bytes_out', 0),
                'connected_at': int((stats.get('first_seen', time.time()) * 1000)),
                'avg_response_time': stats.get('avg_response_time', 0)
            })

        # Get recent logs
        logs = self.traffic_inspector.get_logs(limit=50)
        log_data = [
            {
                'timestamp': int(log.timestamp * 1000),
                'client_id': log.client_id,
                'method': log.method,
                'path': log.path,
                'status': log.status,
                'duration': log.duration_ms,
                'request_size': log.request_size,
                'response_size': log.response_size
            }
            for log in logs
        ]

        return web.json_response({
            'active_tunnels': active_tunnels,
            'total_requests': total_requests,
            'bandwidth_used': total_bandwidth,
            'avg_response': avg_response,
            'tunnels': tunnels,
            'logs': log_data
        })

    async def get_tunnel_stats(self, request: web.Request) -> web.Response:
        """Get statistics for a specific tunnel."""
        client_id = request.match_info.get('client_id')

        if client_id not in self.server.clients:
            return web.json_response({'error': 'Tunnel not found'}, status=404)

        stats = self.traffic_inspector.get_stats(client_id)
        logs = self.traffic_inspector.get_logs(client_id=client_id, limit=100)

        log_data = [
            {
                'timestamp': int(log.timestamp * 1000),
                'method': log.method,
                'path': log.path,
                'status': log.status,
                'duration': log.duration_ms,
                'request_size': log.request_size,
                'response_size': log.response_size
            }
            for log in logs
        ]

        return web.json_response({
            'client_id': client_id,
            'stats': stats,
            'logs': log_data
        })

    async def serve_dashboard(self, request: web.Request) -> web.Response:
        """Serve the dashboard HTML."""
        import os
        from pathlib import Path

        # Get path to dashboard HTML
        dashboard_path = Path(__file__).parent / 'static' / 'dashboard.html'

        if not dashboard_path.exists():
            return web.Response(text='Dashboard not found', status=404)

        with open(dashboard_path, 'r') as f:
            content = f.read()

        return web.Response(text=content, content_type='text/html')
