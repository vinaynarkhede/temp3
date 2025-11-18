"""Enhanced CLI utilities with rich terminal UI."""

import time
from typing import Optional, Dict, Any
from contextlib import contextmanager

try:
    from rich.console import Console
    from rich.progress import (
        Progress, SpinnerColumn, TextColumn, BarColumn,
        TaskProgressColumn, TimeRemainingColumn, TimeElapsedColumn,
        DownloadColumn, TransferSpeedColumn
    )
    from rich.table import Table
    from rich.panel import Panel
    from rich.live import Live
    from rich.layout import Layout
    from rich import box
    from rich.text import Text
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    Console = None
    Progress = None


class ProgressTracker:
    """Track and display progress for various operations."""

    def __init__(self):
        self.console = Console() if RICH_AVAILABLE else None
        self.progress = None

    @contextmanager
    def track_download(self, description: str, total: int):
        """Track a download/upload operation with progress bar."""
        if not RICH_AVAILABLE:
            print(f"{description}...")
            yield lambda n: None
            print(f"{description} complete!")
            return

        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            DownloadColumn(),
            TransferSpeedColumn(),
            TimeRemainingColumn(),
            console=self.console
        ) as progress:
            task = progress.add_task(description, total=total)

            def update(completed: int):
                progress.update(task, completed=completed)

            yield update
            progress.update(task, completed=total)

    @contextmanager
    def track_operation(self, description: str, total: Optional[int] = None):
        """Track a general operation with spinner or progress bar."""
        if not RICH_AVAILABLE:
            print(f"{description}...")
            yield lambda: None
            print(f"{description} complete!")
            return

        if total:
            with Progress(
                SpinnerColumn(),
                TextColumn("[bold blue]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                TimeElapsedColumn(),
                console=self.console
            ) as progress:
                task = progress.add_task(description, total=total)

                def advance():
                    progress.advance(task)

                yield advance
                progress.update(task, completed=total)
        else:
            # Spinner for indeterminate operations
            with self.console.status(f"[bold blue]{description}..."):
                yield lambda: None

    def show_success(self, message: str):
        """Show success message."""
        if self.console:
            self.console.print(f"[bold green]✓[/bold green] {message}")
        else:
            print(f"✓ {message}")

    def show_error(self, message: str):
        """Show error message."""
        if self.console:
            self.console.print(f"[bold red]✗[/bold red] {message}")
        else:
            print(f"✗ {message}")

    def show_warning(self, message: str):
        """Show warning message."""
        if self.console:
            self.console.print(f"[bold yellow]⚠[/bold yellow] {message}")
        else:
            print(f"⚠ {message}")

    def show_info(self, message: str):
        """Show info message."""
        if self.console:
            self.console.print(f"[bold cyan]ℹ[/bold cyan] {message}")
        else:
            print(f"ℹ {message}")


class LiveDisplay:
    """Live updating display for tunnel status."""

    def __init__(self):
        self.console = Console() if RICH_AVAILABLE else None
        self.stats = {
            'bytes_sent': 0,
            'bytes_received': 0,
            'requests': 0,
            'errors': 0,
            'connections': 0,
            'uptime': 0
        }
        self.start_time = time.time()

    def update_stats(self, **kwargs):
        """Update statistics."""
        self.stats.update(kwargs)
        self.stats['uptime'] = int(time.time() - self.start_time)

    def _format_bytes(self, bytes: int) -> str:
        """Format bytes to human readable."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes < 1024:
                return f"{bytes:.1f} {unit}"
            bytes /= 1024
        return f"{bytes:.1f} TB"

    def _format_duration(self, seconds: int) -> str:
        """Format duration to human readable."""
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60

        if hours > 0:
            return f"{hours}h {minutes}m {secs}s"
        elif minutes > 0:
            return f"{minutes}m {secs}s"
        else:
            return f"{secs}s"

    def generate_display(self) -> Table:
        """Generate the display table."""
        if not RICH_AVAILABLE:
            return None

        table = Table(title="🚀 PyTunnel Status", box=box.ROUNDED)
        table.add_column("Metric", style="cyan", no_wrap=True)
        table.add_column("Value", style="green")

        table.add_row("Uptime", self._format_duration(self.stats['uptime']))
        table.add_row("Requests", str(self.stats['requests']))
        table.add_row("Errors", str(self.stats['errors']))
        table.add_row("Active Connections", str(self.stats['connections']))
        table.add_row("Bytes Sent", self._format_bytes(self.stats['bytes_sent']))
        table.add_row("Bytes Received", self._format_bytes(self.stats['bytes_received']))

        # Calculate rates
        if self.stats['uptime'] > 0:
            req_per_sec = self.stats['requests'] / self.stats['uptime']
            bytes_per_sec = (self.stats['bytes_sent'] + self.stats['bytes_received']) / self.stats['uptime']
            table.add_row("Req/sec", f"{req_per_sec:.2f}")
            table.add_row("Bandwidth", f"{self._format_bytes(bytes_per_sec)}/s")

        return table

    @contextmanager
    def live_display(self):
        """Context manager for live updating display."""
        if not RICH_AVAILABLE:
            print("Live display not available (install rich library)")
            yield
            return

        layout = Layout()
        layout.split(
            Layout(name="header", size=3),
            Layout(name="body")
        )

        with Live(layout, console=self.console, refresh_per_second=2) as live:
            def update_display():
                layout["header"].update(
                    Panel(
                        Text("PyTunnel - Live Monitoring", justify="center", style="bold cyan"),
                        style="cyan"
                    )
                )
                layout["body"].update(self.generate_display())
                live.refresh()

            yield update_display


class StatusDisplay:
    """Display tunnel status and statistics."""

    def __init__(self):
        self.console = Console() if RICH_AVAILABLE else None

    def show_tunnel_status(self, tunnels: list):
        """Show status of all active tunnels."""
        if not RICH_AVAILABLE:
            print("\nActive Tunnels:")
            print("=" * 60)
            for tunnel in tunnels:
                print(f"  {tunnel['id']}: {tunnel['url']}")
                print(f"    Status: {tunnel['status']}")
                print(f"    Requests: {tunnel.get('requests', 0)}")
            return

        if not tunnels:
            self.console.print(Panel(
                "[yellow]No active tunnels[/yellow]",
                title="Tunnel Status",
                border_style="yellow"
            ))
            return

        table = Table(title="🚇 Active Tunnels", box=box.ROUNDED, show_header=True)
        table.add_column("ID", style="cyan", no_wrap=True)
        table.add_column("URL", style="blue")
        table.add_column("Status", style="green")
        table.add_column("Requests", justify="right", style="yellow")
        table.add_column("Bandwidth", justify="right", style="magenta")

        for tunnel in tunnels:
            status_emoji = "🟢" if tunnel['status'] == 'active' else "🔴"
            table.add_row(
                tunnel['id'],
                tunnel['url'],
                f"{status_emoji} {tunnel['status']}",
                str(tunnel.get('requests', 0)),
                self._format_bytes(tunnel.get('bandwidth', 0))
            )

        self.console.print(table)

    def show_security_status(self, stats: Dict[str, Any]):
        """Show security status."""
        if not RICH_AVAILABLE:
            print("\nSecurity Status:")
            print("=" * 60)
            print(f"  Security Score: {stats.get('security_score', 0)}/100")
            print(f"  Active Connections: {stats.get('connections', 0)}")
            print(f"  Blocked IPs: {stats.get('blocked_ips', 0)}")
            return

        score = stats.get('security_score', 0)
        score_color = "green" if score >= 80 else "yellow" if score >= 60 else "red"

        table = Table(title="🛡️  Security Status", box=box.ROUNDED)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Security Score", f"[{score_color}]{score}/100[/{score_color}]")
        table.add_row("Active Connections", str(stats.get('connections', {}).get('total_connections', 0)))
        table.add_row("Blocked IPs", str(len(stats.get('blocked_ips', []))))
        table.add_row("IP Whitelist", "✓" if stats.get('config', {}).get('has_whitelist') else "✗")
        table.add_row("IP Blacklist", "✓" if stats.get('config', {}).get('has_blacklist') else "✗")

        self.console.print(table)

    def show_compliance_status(self, status: Dict[str, Any]):
        """Show compliance status."""
        if not RICH_AVAILABLE:
            print("\nCompliance Status:")
            print("=" * 60)
            print(f"  Audit Log Integrity: {'OK' if status.get('audit_log_integrity') else 'FAILED'}")
            print(f"  Total Audit Entries: {status.get('total_audit_entries', 0)}")
            print(f"  GDPR Ready: {'Yes' if status.get('gdpr_ready') else 'No'}")
            return

        table = Table(title="📋 Compliance Status", box=box.ROUNDED)
        table.add_column("Check", style="cyan")
        table.add_column("Status", style="green")

        integrity = status.get('audit_log_integrity', False)
        integrity_status = "[green]✓ OK[/green]" if integrity else "[red]✗ FAILED[/red]"

        table.add_row("Audit Log Integrity", integrity_status)
        table.add_row("Total Audit Entries", str(status.get('total_audit_entries', 0)))
        table.add_row("GDPR Ready", "✓" if status.get('gdpr_ready') else "✗")
        table.add_row("Auto Cleanup", "✓" if status.get('retention_policy', {}).get('auto_cleanup_enabled') else "✗")
        table.add_row("Log Retention", f"{status.get('retention_policy', {}).get('log_retention_days', 0)} days")

        self.console.print(table)

    def _format_bytes(self, bytes: int) -> str:
        """Format bytes to human readable."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes < 1024:
                return f"{bytes:.1f} {unit}"
            bytes /= 1024
        return f"{bytes:.1f} TB"

    def show_summary(self, tunnels: list, security: Dict, compliance: Dict):
        """Show complete summary."""
        if not RICH_AVAILABLE:
            self.show_tunnel_status(tunnels)
            self.show_security_status(security)
            self.show_compliance_status(compliance)
            return

        self.console.print()
        self.console.print(Panel.fit(
            "[bold cyan]PyTunnel Status Dashboard[/bold cyan]",
            border_style="cyan"
        ))
        self.console.print()

        self.show_tunnel_status(tunnels)
        self.console.print()
        self.show_security_status(security)
        self.console.print()
        self.show_compliance_status(compliance)
        self.console.print()


# Global instances
_progress_tracker = None
_live_display = None
_status_display = None


def get_progress_tracker() -> ProgressTracker:
    """Get global progress tracker."""
    global _progress_tracker
    if _progress_tracker is None:
        _progress_tracker = ProgressTracker()
    return _progress_tracker


def get_live_display() -> LiveDisplay:
    """Get global live display."""
    global _live_display
    if _live_display is None:
        _live_display = LiveDisplay()
    return _live_display


def get_status_display() -> StatusDisplay:
    """Get global status display."""
    global _status_display
    if _status_display is None:
        _status_display = StatusDisplay()
    return _status_display
