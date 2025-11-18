"""Configuration management for PyTunnel."""

import os
import json
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class ServerConfig:
    """Server configuration."""
    host: str = "0.0.0.0"
    port: int = 8080
    base_domain: Optional[str] = None

    # TLS/SSL settings
    enable_tls: bool = False
    cert_file: Optional[str] = None
    key_file: Optional[str] = None
    ca_file: Optional[str] = None

    # Authentication
    enable_auth: bool = False
    auth_file: Optional[str] = None
    require_api_key: bool = False

    # Features
    enable_dashboard: bool = True
    enable_traffic_logging: bool = True
    enable_subdomains: bool = True

    # Limits
    max_clients: int = 100
    max_request_size: int = 10 * 1024 * 1024  # 10 MB
    request_timeout: int = 30

    # Bandwidth
    enable_bandwidth_limit: bool = False
    global_upload_limit: Optional[int] = None  # bytes per second
    global_download_limit: Optional[int] = None

    # Rate limiting
    enable_rate_limit: bool = False
    max_requests_per_minute: int = 100

    # Protocols
    enable_websocket: bool = True
    enable_tcp: bool = False
    enable_grpc: bool = False


@dataclass
class ClientConfig:
    """Client configuration."""
    server_url: str = "http://localhost:8080"
    local_host: str = "localhost"
    local_port: int = 3000

    # Client identity
    client_id: Optional[str] = None
    subdomain: Optional[str] = None

    # Authentication
    api_key: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None

    # TLS/SSL
    verify_ssl: bool = True
    ca_file: Optional[str] = None

    # Connection
    auto_reconnect: bool = True
    reconnect_delay: int = 5
    heartbeat_interval: int = 30


class ConfigManager:
    """Manages configuration loading and saving."""

    @staticmethod
    def load_server_config(config_file: Optional[str] = None) -> ServerConfig:
        """Load server configuration from file or environment."""
        config = ServerConfig()

        # Load from file if provided
        if config_file and os.path.exists(config_file):
            with open(config_file, 'r') as f:
                data = json.load(f)
                for key, value in data.items():
                    if hasattr(config, key):
                        setattr(config, key, value)

        # Override with environment variables
        config.host = os.getenv('PYTUNNEL_HOST', config.host)
        config.port = int(os.getenv('PYTUNNEL_PORT', config.port))
        config.base_domain = os.getenv('PYTUNNEL_DOMAIN', config.base_domain)

        # TLS settings
        if os.getenv('PYTUNNEL_TLS_CERT'):
            config.enable_tls = True
            config.cert_file = os.getenv('PYTUNNEL_TLS_CERT')
            config.key_file = os.getenv('PYTUNNEL_TLS_KEY')

        # Auth settings
        if os.getenv('PYTUNNEL_AUTH_FILE'):
            config.enable_auth = True
            config.auth_file = os.getenv('PYTUNNEL_AUTH_FILE')

        return config

    @staticmethod
    def load_client_config(config_file: Optional[str] = None) -> ClientConfig:
        """Load client configuration from file or environment."""
        config = ClientConfig()

        # Load from file if provided
        if config_file and os.path.exists(config_file):
            with open(config_file, 'r') as f:
                data = json.load(f)
                for key, value in data.items():
                    if hasattr(config, key):
                        setattr(config, key, value)

        # Override with environment variables
        config.server_url = os.getenv('PYTUNNEL_SERVER', config.server_url)
        config.local_host = os.getenv('PYTUNNEL_LOCAL_HOST', config.local_host)
        config.local_port = int(os.getenv('PYTUNNEL_LOCAL_PORT', str(config.local_port)))

        # Auth settings
        config.api_key = os.getenv('PYTUNNEL_API_KEY', config.api_key)
        config.username = os.getenv('PYTUNNEL_USERNAME', config.username)
        config.password = os.getenv('PYTUNNEL_PASSWORD', config.password)

        # Custom subdomain
        config.subdomain = os.getenv('PYTUNNEL_SUBDOMAIN', config.subdomain)

        return config

    @staticmethod
    def save_server_config(config: ServerConfig, config_file: str):
        """Save server configuration to file."""
        with open(config_file, 'w') as f:
            json.dump(asdict(config), f, indent=2)

    @staticmethod
    def save_client_config(config: ClientConfig, config_file: str):
        """Save client configuration to file."""
        # Don't save sensitive data
        data = asdict(config)
        data.pop('password', None)
        data.pop('api_key', None)

        with open(config_file, 'w') as f:
            json.dump(data, f, indent=2)

    @staticmethod
    def create_example_server_config(output_file: str = "server_config.json"):
        """Create an example server configuration file."""
        config = ServerConfig()
        ConfigManager.save_server_config(config, output_file)
        print(f"Example server configuration created: {output_file}")

    @staticmethod
    def create_example_client_config(output_file: str = "client_config.json"):
        """Create an example client configuration file."""
        config = ClientConfig()
        ConfigManager.save_client_config(config, output_file)
        print(f"Example client configuration created: {output_file}")


def get_config_dir() -> Path:
    """Get the configuration directory."""
    # Use XDG_CONFIG_HOME if available, otherwise ~/.config
    config_home = os.getenv('XDG_CONFIG_HOME')
    if config_home:
        config_dir = Path(config_home) / 'pytunnel'
    else:
        config_dir = Path.home() / '.config' / 'pytunnel'

    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def get_default_server_config_path() -> Path:
    """Get default server config file path."""
    return get_config_dir() / 'server.json'


def get_default_client_config_path() -> Path:
    """Get default client config file path."""
    return get_config_dir() / 'client.json'
