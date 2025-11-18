"""Interactive setup wizard for PyTunnel."""

import os
import socket
import subprocess
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import json

try:
    import psutil
    import questionary
    from questionary import Style
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich import print as rprint
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    Console = None

from pytunnel.common.config import (
    ServerConfig, ClientConfig, ConfigManager,
    get_config_dir
)
from pytunnel.common.utils import generate_client_id


# Custom style for questionary
custom_style = Style([
    ('qmark', 'fg:#673ab7 bold'),
    ('question', 'bold'),
    ('answer', 'fg:#f44336 bold'),
    ('pointer', 'fg:#673ab7 bold'),
    ('highlighted', 'fg:#673ab7 bold'),
    ('selected', 'fg:#cc5454'),
    ('separator', 'fg:#cc5454'),
    ('instruction', ''),
    ('text', ''),
])


class SetupWizard:
    """Interactive setup wizard for PyTunnel."""

    def __init__(self):
        self.console = Console() if RICH_AVAILABLE else None
        self.detected_services: List[Dict[str, any]] = []

    def print_welcome(self):
        """Print welcome banner."""
        if self.console:
            self.console.print()
            self.console.print(Panel.fit(
                "[bold cyan]🚀 Welcome to PyTunnel Setup Wizard![/bold cyan]\n\n"
                "Let's get you set up in just a few steps.\n"
                "We'll help you configure your first tunnel.",
                border_style="cyan"
            ))
            self.console.print()
        else:
            print("\n" + "="*60)
            print("  Welcome to PyTunnel Setup Wizard!")
            print("="*60 + "\n")

    def detect_local_services(self) -> List[Dict[str, any]]:
        """Detect local services running on common ports."""
        common_ports = {
            3000: "Node.js/React (Create React App)",
            3001: "Node.js (Alternative)",
            4200: "Angular CLI",
            5000: "Flask/Python",
            5173: "Vite",
            8000: "Django/Python HTTP Server",
            8080: "HTTP Alt Port",
            8081: "HTTP Alt Port",
            8888: "Jupyter Notebook",
            9000: "PHP/Various",
        }

        services = []

        try:
            if not RICH_AVAILABLE:
                print("Scanning for local services...")
            else:
                with self.console.status("[cyan]Scanning for local services...[/cyan]"):
                    for port, description in common_ports.items():
                        if self._is_port_open('localhost', port):
                            services.append({
                                'port': port,
                                'description': description,
                                'host': 'localhost'
                            })
        except Exception as e:
            if self.console:
                self.console.print(f"[yellow]Warning: Could not scan ports: {e}[/yellow]")

        self.detected_services = services
        return services

    def _is_port_open(self, host: str, port: int) -> bool:
        """Check if a port is open."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(0.1)
                result = sock.connect_ex((host, port))
                return result == 0
        except:
            return False

    def detect_project_name(self) -> Optional[str]:
        """Try to detect project name from git or directory."""
        try:
            # Try git remote
            result = subprocess.run(
                ['git', 'config', '--get', 'remote.origin.url'],
                capture_output=True,
                text=True,
                timeout=2
            )
            if result.returncode == 0:
                url = result.stdout.strip()
                # Extract repo name from URL
                if '/' in url:
                    name = url.split('/')[-1].replace('.git', '')
                    return self._sanitize_subdomain(name)
        except:
            pass

        # Fall back to directory name
        cwd = Path.cwd().name
        return self._sanitize_subdomain(cwd)

    def _sanitize_subdomain(self, name: str) -> str:
        """Sanitize string to be a valid subdomain."""
        import re
        # Convert to lowercase, replace invalid chars with hyphens
        name = name.lower()
        name = re.sub(r'[^a-z0-9-]', '-', name)
        name = re.sub(r'-+', '-', name)  # Remove consecutive hyphens
        name = name.strip('-')  # Remove leading/trailing hyphens

        # Ensure length constraints
        if len(name) < 3:
            return 'my-app'
        if len(name) > 63:
            name = name[:63]

        return name

    def show_detected_services(self, services: List[Dict[str, any]]):
        """Display detected services."""
        if not services:
            return

        if self.console:
            table = Table(title="🔍 Detected Local Services", show_header=True)
            table.add_column("Port", style="cyan")
            table.add_column("Description", style="green")

            for service in services:
                table.add_row(str(service['port']), service['description'])

            self.console.print(table)
            self.console.print()
        else:
            print("\nDetected Local Services:")
            print("-" * 50)
            for service in services:
                print(f"  Port {service['port']}: {service['description']}")
            print()

    async def run_client_wizard(self) -> ClientConfig:
        """Run the client setup wizard."""
        if not RICH_AVAILABLE:
            return self._run_simple_client_wizard()

        self.print_welcome()

        # Ask permission to scan
        scan_permission = questionary.confirm(
            "Can I scan localhost for running services?",
            default=True,
            style=custom_style
        ).ask()

        if scan_permission:
            services = self.detect_local_services()
            if services:
                self.show_detected_services(services)

        # Select what to tunnel
        if services:
            choices = [
                f"Port {s['port']} - {s['description']}" for s in services
            ]
            choices.append("Other (specify manually)")

            selected = questionary.select(
                "What would you like to tunnel?",
                choices=choices,
                style=custom_style
            ).ask()

            if selected and "Other" not in selected:
                port = int(selected.split()[1])
            else:
                port = questionary.text(
                    "Enter the local port to tunnel:",
                    default="3000",
                    style=custom_style
                ).ask()
                port = int(port)
        else:
            port = questionary.text(
                "Enter the local port to tunnel:",
                default="3000",
                style=custom_style
            ).ask()
            port = int(port)

        # Server URL
        server_url = questionary.text(
            "Enter tunnel server URL:",
            default="http://localhost:8080",
            style=custom_style
        ).ask()

        # Custom subdomain
        suggested_subdomain = self.detect_project_name()
        use_custom_subdomain = questionary.confirm(
            f"Use custom subdomain? (suggested: {suggested_subdomain})",
            default=True,
            style=custom_style
        ).ask()

        subdomain = None
        if use_custom_subdomain:
            subdomain = questionary.text(
                "Enter subdomain:",
                default=suggested_subdomain,
                style=custom_style
            ).ask()

        # Authentication
        use_auth = questionary.confirm(
            "Do you have an API key for authentication?",
            default=False,
            style=custom_style
        ).ask()

        api_key = None
        if use_auth:
            api_key = questionary.password(
                "Enter your API key:",
                style=custom_style
            ).ask()

        # Create config
        config = ClientConfig(
            server_url=server_url,
            local_host="localhost",
            local_port=port,
            subdomain=subdomain,
            api_key=api_key,
            client_id=generate_client_id()
        )

        # Save config
        save_config = questionary.confirm(
            "Save this configuration?",
            default=True,
            style=custom_style
        ).ask()

        if save_config:
            config_dir = get_config_dir()
            config_file = config_dir / 'client.json'
            ConfigManager.save_client_config(config, str(config_file))

            self.console.print()
            self.console.print(Panel(
                f"[green]✅ Configuration saved to:[/green]\n{config_file}",
                border_style="green"
            ))

        # Show summary
        self.console.print()
        self.console.print(Panel.fit(
            f"[bold cyan]🎉 Setup Complete![/bold cyan]\n\n"
            f"Server: {config.server_url}\n"
            f"Local: http://localhost:{config.local_port}\n"
            f"Subdomain: {config.subdomain or 'auto-generated'}\n\n"
            f"[yellow]Start your tunnel with:[/yellow]\n"
            f"  pytunnel-client {config.local_port} --server {config.server_url}"
            + (f" --subdomain {config.subdomain}" if config.subdomain else ""),
            border_style="green"
        ))

        return config

    def _run_simple_client_wizard(self) -> ClientConfig:
        """Simplified wizard without rich UI."""
        print("\n=== PyTunnel Client Setup ===\n")

        port = input("Local port to tunnel [3000]: ").strip() or "3000"
        server_url = input("Server URL [http://localhost:8080]: ").strip() or "http://localhost:8080"

        subdomain = None
        use_subdomain = input("Use custom subdomain? [y/N]: ").strip().lower()
        if use_subdomain == 'y':
            suggested = self.detect_project_name()
            subdomain = input(f"Subdomain [{suggested}]: ").strip() or suggested

        config = ClientConfig(
            server_url=server_url,
            local_host="localhost",
            local_port=int(port),
            subdomain=subdomain,
            client_id=generate_client_id()
        )

        save = input("Save configuration? [Y/n]: ").strip().lower()
        if save != 'n':
            config_dir = get_config_dir()
            config_file = config_dir / 'client.json'
            ConfigManager.save_client_config(config, str(config_file))
            print(f"\n✅ Configuration saved to: {config_file}")

        print(f"\n🎉 Setup complete!")
        print(f"Start with: pytunnel-client {port} --server {server_url}")

        return config

    async def run_server_wizard(self) -> ServerConfig:
        """Run the server setup wizard."""
        if not RICH_AVAILABLE:
            return self._run_simple_server_wizard()

        self.print_welcome()

        # Basic settings
        host = questionary.text(
            "Host to bind to:",
            default="0.0.0.0",
            style=custom_style
        ).ask()

        port = questionary.text(
            "Port to listen on:",
            default="8080",
            style=custom_style
        ).ask()

        base_domain = questionary.text(
            "Base domain (leave empty for IP-based URLs):",
            default="",
            style=custom_style
        ).ask()

        # Security preset
        security_preset = questionary.select(
            "Choose security preset:",
            choices=[
                "Basic (No auth, HTTP only)",
                "Standard (Auth optional, HTTPS recommended)",
                "Paranoid (Auth required, HTTPS required)",
            ],
            style=custom_style
        ).ask()

        enable_tls = False
        enable_auth = False
        require_api_key = False

        if "Standard" in security_preset:
            enable_auth = questionary.confirm(
                "Enable authentication?",
                default=True,
                style=custom_style
            ).ask()

            enable_tls = questionary.confirm(
                "Enable TLS/HTTPS?",
                default=False,
                style=custom_style
            ).ask()

        elif "Paranoid" in security_preset:
            enable_auth = True
            require_api_key = True
            enable_tls = questionary.confirm(
                "Enable TLS/HTTPS? (Recommended)",
                default=True,
                style=custom_style
            ).ask()

        # Features
        enable_dashboard = questionary.confirm(
            "Enable web dashboard?",
            default=True,
            style=custom_style
        ).ask()

        enable_subdomains = questionary.confirm(
            "Enable custom subdomains?",
            default=True,
            style=custom_style
        ).ask()

        # Create config
        config = ServerConfig(
            host=host,
            port=int(port),
            base_domain=base_domain or None,
            enable_tls=enable_tls,
            enable_auth=enable_auth,
            require_api_key=require_api_key,
            enable_dashboard=enable_dashboard,
            enable_subdomains=enable_subdomains,
            enable_traffic_logging=True
        )

        # Save config
        save_config = questionary.confirm(
            "Save this configuration?",
            default=True,
            style=custom_style
        ).ask()

        if save_config:
            config_dir = get_config_dir()
            config_file = config_dir / 'server.json'
            ConfigManager.save_server_config(config, str(config_file))

            self.console.print()
            self.console.print(Panel(
                f"[green]✅ Configuration saved to:[/green]\n{config_file}",
                border_style="green"
            ))

        # Show security warnings
        if not enable_auth:
            self.console.print()
            self.console.print(Panel(
                "[yellow]⚠️  WARNING: Authentication is disabled!\n"
                "Anyone can create tunnels on your server.[/yellow]",
                border_style="yellow"
            ))

        if not enable_tls:
            self.console.print()
            self.console.print(Panel(
                "[yellow]⚠️  WARNING: TLS is disabled!\n"
                "Traffic will not be encrypted.[/yellow]",
                border_style="yellow"
            ))

        # Show next steps
        self.console.print()
        self.console.print(Panel.fit(
            f"[bold cyan]🎉 Setup Complete![/bold cyan]\n\n"
            f"[yellow]Start your server with:[/yellow]\n"
            f"  pytunnel-server --port {config.port}"
            + (f"\n\n[yellow]Dashboard will be available at:[/yellow]\n  http://{config.host}:{config.port}/dashboard" if enable_dashboard else ""),
            border_style="green"
        ))

        return config

    def _run_simple_server_wizard(self) -> ServerConfig:
        """Simplified server wizard without rich UI."""
        print("\n=== PyTunnel Server Setup ===\n")

        host = input("Host to bind to [0.0.0.0]: ").strip() or "0.0.0.0"
        port = input("Port [8080]: ").strip() or "8080"

        config = ServerConfig(
            host=host,
            port=int(port),
            enable_dashboard=True,
            enable_traffic_logging=True
        )

        save = input("Save configuration? [Y/n]: ").strip().lower()
        if save != 'n':
            config_dir = get_config_dir()
            config_file = config_dir / 'server.json'
            ConfigManager.save_server_config(config, str(config_file))
            print(f"\n✅ Configuration saved to: {config_file}")

        print(f"\n🎉 Setup complete!")
        print(f"Start with: pytunnel-server --port {port}")

        return config


async def run_wizard(mode: str = 'client'):
    """Run the setup wizard."""
    wizard = SetupWizard()

    if mode == 'client':
        return await wizard.run_client_wizard()
    elif mode == 'server':
        return await wizard.run_server_wizard()
    else:
        raise ValueError(f"Invalid mode: {mode}")
