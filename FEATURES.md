## PyTunnel Advanced Features

Comprehensive guide to all advanced features in PyTunnel v0.3.0

---

## Table of Contents

### Core Features (v0.2.0)
1. [HTTPS/TLS Support](#httpstls-support)
2. [Custom Subdomains](#custom-subdomains)
3. [Authentication & Authorization](#authentication--authorization)
4. [Web Dashboard](#web-dashboard)
5. [Traffic Inspection & Logging](#traffic-inspection--logging)
6. [TCP Tunnel Support](#tcp-tunnel-support)
7. [Bandwidth Limiting](#bandwidth-limiting)
8. [Multiple Protocol Support](#multiple-protocol-support)
9. [Configuration Management](#configuration-management)

### DX & Enterprise Features (v0.3.0)
10. [Interactive Setup Wizard](#interactive-setup-wizard)
11. [CLI UX Enhancements](#cli-ux-enhancements)
12. [Shareable Tunnel Links](#shareable-tunnel-links)
13. [Webhook Integrations](#webhook-integrations)
14. [Advanced Security](#advanced-security)
15. [Compliance & Audit Logging](#compliance--audit-logging)

---

## HTTPS/TLS Support

Secure your tunnels with TLS/SSL encryption.

### Features

- Server-side TLS termination
- Client certificate verification
- Self-signed certificate generation for testing
- Support for custom CA certificates

### Usage

#### Generate Self-Signed Certificate (Testing)

```python
from pytunnel.common.tls import TLSConfig

cert_file, key_file = TLSConfig.generate_self_signed_cert(
    cert_file="server.crt",
    key_file="server.key",
    days=365
)
```

#### Start Server with TLS

```bash
pytunnel-server \
  --host 0.0.0.0 \
  --port 8443 \
  --enable-tls \
  --cert-file server.crt \
  --key-file server.key
```

#### Client Connection to TLS Server

```bash
pytunnel-client 3000 \
  --server https://tunnel.example.com:8443 \
  --verify-ssl \
  --ca-file ca.crt
```

### Configuration

```json
{
  "enable_tls": true,
  "cert_file": "/path/to/server.crt",
  "key_file": "/path/to/server.key",
  "ca_file": "/path/to/ca.crt"
}
```

---

## Custom Subdomains

Use memorable subdomains instead of random client IDs.

### Features

- Custom subdomain registration
- Subdomain validation (3-63 chars, alphanumeric + hyphens)
- Reserved subdomain list
- Subdomain expiration (optional TTL)
- Automatic cleanup of expired subdomains

### Usage

#### Request Custom Subdomain

```bash
pytunnel-client 3000 \
  --server http://tunnel.example.com:8080 \
  --subdomain my-awesome-app
```

Your tunnel URL will be: `http://my-awesome-app.tunnel.example.com:8080`

#### Subdomain Rules

- **Valid:** `my-app`, `api-v2`, `test123`
- **Invalid:** `ab` (too short), `-app` (starts with hyphen), `My-App` (uppercase)
- **Reserved:** `www`, `api`, `admin`, `dashboard`, `status`

### API Usage

```python
from pytunnel.common.subdomains import get_subdomain_manager

manager = get_subdomain_manager(base_domain="tunnel.example.com")

# Register subdomain
success = manager.register_subdomain(
    subdomain="my-app",
    client_id="abc123",
    username="user@example.com",
    ttl=3600  # Optional: expire after 1 hour
)

# Get client for subdomain
client_id = manager.get_client_for_subdomain("my-app")

# Cleanup expired
removed = manager.cleanup_expired()
```

---

## Authentication & Authorization

Secure your tunnel server with authentication.

### Features

- User account management
- Password hashing (SHA-256)
- API key authentication
- Temporary access tokens
- Subdomain access control
- Per-user tunnel limits

### Usage

#### Create User Account

```python
from pytunnel.common.auth import get_auth_manager

auth = get_auth_manager()

user = auth.create_user(
    username="john@example.com",
    password="secure_password",
    allowed_subdomains={"my-app", "test-app"},
    max_tunnels=5
)

print(f"API Key: {user.api_key}")
```

#### Client Authentication

```bash
# Using API key
pytunnel-client 3000 \
  --server http://tunnel.example.com:8080 \
  --api-key "your-api-key-here"

# Using username/password
pytunnel-client 3000 \
  --server http://tunnel.example.com:8080 \
  --username john@example.com \
  --password secure_password
```

### Access Control

```python
# Check if user can use subdomain
can_use = auth.can_use_subdomain("john@example.com", "my-app")

# Check if user can create more tunnels
can_create = auth.can_create_tunnel("john@example.com")

# Generate temporary token (1 hour)
token = auth.generate_token("john@example.com", ttl=3600)
```

### Persistence

```python
# Save users to file
auth.save_to_file("users.json")

# Load users from file
auth.load_from_file("users.json")
```

---

## Web Dashboard

Beautiful web interface for monitoring tunnels and traffic.

### Features

- Real-time tunnel monitoring
- Traffic statistics and graphs
- Request/response logs
- Bandwidth usage tracking
- Active tunnel list
- Responsive design

### Access Dashboard

```
http://your-server:8080/dashboard
```

### API Endpoints

- `GET /api/stats` - Get overall statistics
- `GET /api/tunnel/{client_id}` - Get specific tunnel stats

### Dashboard Metrics

- **Active Tunnels:** Number of connected clients
- **Total Requests:** All-time request count
- **Bandwidth Used:** Total data transferred
- **Avg Response Time:** Average across all tunnels

### Sample Response

```json
{
  "active_tunnels": 3,
  "total_requests": 1247,
  "bandwidth_used": 45000000,
  "avg_response": 142,
  "tunnels": [
    {
      "client_id": "abc123",
      "subdomain": "my-app",
      "status": "active",
      "requests": 523,
      "bandwidth": 15000000,
      "connected_at": 1700000000000
    }
  ]
}
```

---

## Traffic Inspection & Logging

Monitor and analyze all traffic through your tunnels.

### Features

- Request/response logging
- Traffic statistics per client
- Bandwidth tracking
- Status code analysis
- HTTP method analysis
- Export logs to JSON
- Configurable log retention

### Usage

```python
from pytunnel.common.traffic import get_traffic_inspector

inspector = get_traffic_inspector()

# Log a request
inspector.log_request(
    client_id="abc123",
    request_id="req-456",
    method="GET",
    path="/api/users",
    status=200,
    request_size=1024,
    response_size=4096,
    duration_ms=45.3,
    remote_addr="192.168.1.1",
    user_agent="Mozilla/5.0..."
)

# Get recent logs
logs = inspector.get_logs(client_id="abc123", limit=100)

# Get statistics
stats = inspector.get_stats("abc123")
# {
#   'total_requests': 523,
#   'total_bytes_in': 50000,
#   'total_bytes_out': 150000,
#   'avg_response_time': 45.3,
#   'status_codes': {'200': 450, '404': 50, '500': 23},
#   'methods': {'GET': 400, 'POST': 100, 'PUT': 23}
# }

# Export logs
inspector.export_logs("traffic.json", client_id="abc123")

# Clear logs
inspector.clear_logs(client_id="abc123")
```

---

## TCP Tunnel Support

Tunnel raw TCP connections, not just HTTP.

### Features

- Generic TCP tunneling
- Connection management
- Binary data support
- Multiple simultaneous connections

### Protocol

```python
from pytunnel.common.tcp_protocol import *

# Connect to TCP service
msg = create_tcp_connect(
    connection_id="conn-123",
    host="localhost",
    port=5432  # PostgreSQL
)

# Send data
msg = create_tcp_data(
    connection_id="conn-123",
    data=b"SELECT * FROM users;"
)

# Close connection
msg = create_tcp_disconnect(
    connection_id="conn-123",
    reason="Client closed"
)
```

### Use Cases

- Database tunneling (PostgreSQL, MySQL)
- SSH tunneling
- Redis connections
- Custom TCP protocols

---

## Bandwidth Limiting

Control bandwidth usage for clients and globally.

### Features

- Per-client bandwidth limits
- Global bandwidth limits
- Upload/download separate limits
- Token bucket algorithm
- Request rate limiting
- Burst capacity support

### Usage

#### Set Client Bandwidth Limit

```python
from pytunnel.common.bandwidth import get_bandwidth_limiter

limiter = get_bandwidth_limiter()

# Limit client to 1MB/s upload, 2MB/s download
limiter.set_client_limit(
    client_id="abc123",
    upload_limit=1_000_000,    # 1 MB/s
    download_limit=2_000_000,  # 2 MB/s
    burst_size=5_000_000       # 5 MB burst
)
```

#### Set Global Bandwidth Limit

```python
# Limit all clients combined to 10MB/s
limiter.set_global_limit(
    upload_limit=10_000_000,
    download_limit=10_000_000
)
```

#### Acquire Bandwidth

```python
# Before sending data
allowed = await limiter.acquire_upload(
    client_id="abc123",
    size=1024,  # bytes
    timeout=10.0
)

if allowed:
    # Send data
    pass
else:
    # Rate limited
    pass
```

### Request Rate Limiting

```python
from pytunnel.common.bandwidth import get_rate_limiter

rate_limiter = get_rate_limiter(
    max_requests=100,
    window_seconds=60
)

if rate_limiter.is_allowed("client_id"):
    # Process request
    pass
else:
    # Rate limited
    pass

# Check remaining requests
remaining = rate_limiter.get_remaining("client_id")
```

---

## Multiple Protocol Support

Support for various protocols beyond HTTP.

### Supported Protocols

- **HTTP** - Standard HTTP/1.1
- **HTTPS** - TLS-encrypted HTTP
- **WebSocket** - Bidirectional WebSocket connections
- **TCP** - Raw TCP tunneling
- **gRPC** - Google RPC framework

### Protocol Detection

```python
from pytunnel.common.protocols import ProtocolDetector

detector = ProtocolDetector()

# Detect from HTTP headers
protocol = detector.detect_from_request(headers, path)

# Check for WebSocket
is_ws = detector.is_websocket_upgrade(headers)
```

### WebSocket Support

```python
from pytunnel.common.protocols import WebSocketTunnelHandler

handler = WebSocketTunnelHandler()

# Create upgrade request
upgrade = handler.create_upgrade_request(path="/ws", headers={...})

# Send WebSocket frame
frame = handler.create_frame_message(data=b"Hello", opcode=1)

# Close WebSocket
close = handler.create_close_message(code=1000, reason="Normal")
```

### gRPC Support

```python
from pytunnel.common.protocols import GRPCTunnelHandler

handler = GRPCTunnelHandler()

# Create gRPC request
request = handler.create_grpc_request(
    method="/api.Service/Method",
    headers={"content-type": "application/grpc"},
    data=b"..."
)

# Parse gRPC status
status = handler.parse_grpc_status(headers)
```

### Enable Protocols

```python
from pytunnel.common.protocols import get_protocol_config

config = get_protocol_config()

# Enable WebSocket tunneling
config.enable_protocol(TunnelProtocol.WEBSOCKET)

# Enable TCP tunneling
config.enable_protocol(TunnelProtocol.TCP)

# Enable gRPC
config.enable_protocol(TunnelProtocol.GRPC)

# Check if enabled
if config.is_enabled(TunnelProtocol.WEBSOCKET):
    # Handle WebSocket
    pass
```

---

## Configuration Management

Flexible configuration through files and environment variables.

### Server Configuration

```json
{
  "host": "0.0.0.0",
  "port": 8080,
  "base_domain": "tunnel.example.com",

  "enable_tls": true,
  "cert_file": "/etc/pytunnel/server.crt",
  "key_file": "/etc/pytunnel/server.key",

  "enable_auth": true,
  "auth_file": "/etc/pytunnel/users.json",
  "require_api_key": true,

  "enable_dashboard": true,
  "enable_traffic_logging": true,
  "enable_subdomains": true,

  "max_clients": 100,
  "max_request_size": 10485760,
  "request_timeout": 30,

  "enable_bandwidth_limit": true,
  "global_upload_limit": 10000000,
  "global_download_limit": 10000000,

  "enable_rate_limit": true,
  "max_requests_per_minute": 100,

  "enable_websocket": true,
  "enable_tcp": false,
  "enable_grpc": false
}
```

### Client Configuration

```json
{
  "server_url": "https://tunnel.example.com:8443",
  "local_host": "localhost",
  "local_port": 3000,

  "client_id": "my-client",
  "subdomain": "my-app",

  "api_key": "your-api-key",
  "username": "user@example.com",

  "verify_ssl": true,
  "ca_file": "/path/to/ca.crt",

  "auto_reconnect": true,
  "reconnect_delay": 5,
  "heartbeat_interval": 30
}
```

### Load Configuration

```python
from pytunnel.common.config import ConfigManager

# Load server config
config = ConfigManager.load_server_config("server.json")

# Load client config
config = ConfigManager.load_client_config("client.json")

# Create example configs
ConfigManager.create_example_server_config("server_example.json")
ConfigManager.create_example_client_config("client_example.json")
```

### Environment Variables

Server:
- `PYTUNNEL_HOST` - Server host
- `PYTUNNEL_PORT` - Server port
- `PYTUNNEL_DOMAIN` - Base domain
- `PYTUNNEL_TLS_CERT` - TLS certificate file
- `PYTUNNEL_TLS_KEY` - TLS key file
- `PYTUNNEL_AUTH_FILE` - User auth file

Client:
- `PYTUNNEL_SERVER` - Server URL
- `PYTUNNEL_LOCAL_HOST` - Local host
- `PYTUNNEL_LOCAL_PORT` - Local port
- `PYTUNNEL_API_KEY` - API key
- `PYTUNNEL_USERNAME` - Username
- `PYTUNNEL_PASSWORD` - Password
- `PYTUNNEL_SUBDOMAIN` - Custom subdomain

---

## Examples

### Secure Production Setup

```bash
# 1. Generate certificates
python -c "from pytunnel.common.tls import TLSConfig; TLSConfig.generate_self_signed_cert()"

# 2. Create users
python -c "
from pytunnel.common.auth import get_auth_manager
auth = get_auth_manager()
user = auth.create_user('john@example.com', 'password123')
print(f'API Key: {user.api_key}')
auth.save_to_file('users.json')
"

# 3. Start server
pytunnel-server \
  --enable-tls --cert-file server.crt --key-file server.key \
  --enable-auth --auth-file users.json \
  --enable-dashboard \
  --enable-bandwidth-limit --global-upload-limit 10000000

# 4. Connect client
pytunnel-client 3000 \
  --server https://tunnel.example.com:8443 \
  --api-key "your-api-key" \
  --subdomain my-app \
  --verify-ssl
```

### Monitor Traffic

```bash
# Access dashboard
open http://tunnel.example.com:8080/dashboard

# Get stats via API
curl http://tunnel.example.com:8080/api/stats

# Get client stats
curl http://tunnel.example.com:8080/api/tunnel/abc123
```

---

## Performance Tips

1. **Use TLS for production** - Secure your tunnels in production
2. **Enable rate limiting** - Prevent abuse
3. **Set bandwidth limits** - Control resource usage
4. **Monitor dashboard** - Watch for unusual patterns
5. **Regular cleanup** - Remove expired subdomains
6. **Log rotation** - Prevent log files from growing too large

---

## Security Best Practices

1. **Always use authentication** in production
2. **Use strong passwords** and API keys
3. **Enable TLS** for encrypted communications
4. **Limit subdomain access** per user
5. **Set tunnel limits** per user
6. **Monitor traffic logs** for suspicious activity
7. **Regular backups** of user data
8. **Keep software updated**

---

## Troubleshooting

### TLS Issues

```bash
# Test TLS connection
openssl s_client -connect tunnel.example.com:8443

# Verify certificate
openssl x509 -in server.crt -text -noout
```

### Authentication Issues

```python
# Check user exists
auth = get_auth_manager()
auth.load_from_file('users.json')
print(auth.users.keys())

# Verify password
auth.verify_password('username', 'password')
```

### Bandwidth Issues

```python
# Check client stats
limiter = get_bandwidth_limiter()
stats = limiter.get_client_stats('client_id')
print(stats)
```

---

## Interactive Setup Wizard

New in v0.3.0: Guided setup for both client and server configurations.

### Features

- **Port Scanning**: Automatically detects services running on common ports
- **Project Detection**: Suggests subdomain from git repo or directory name
- **Smart Defaults**: Pre-fills common configuration values
- **Interactive Prompts**: User-friendly questionnaire-style setup
- **Rich Terminal UI**: Beautiful tables and colored output (when available)
- **Configuration Persistence**: Save settings for easy reuse

### Usage

#### Client Setup Wizard

```python
from pytunnel.common.wizard import run_wizard

# Run interactive client setup
config = await run_wizard(mode='client')
```

The wizard will:
1. Scan for local services (port 3000, 5000, 8000, etc.)
2. Show detected services in a table
3. Ask which port to tunnel
4. Detect project name from git or directory
5. Offer custom subdomain option
6. Request server URL and authentication
7. Save configuration

#### Server Setup Wizard

```python
# Run interactive server setup
config = await run_wizard(mode='server')
```

The wizard guides you through:
1. Host and port configuration
2. Security preset selection (Basic/Standard/Paranoid)
3. TLS/SSL setup
4. Authentication options
5. Feature toggles (dashboard, subdomains, etc.)
6. Configuration save

### CLI Integration

```bash
# Client wizard (future)
pytunnel-client --wizard

# Server wizard (future)
pytunnel-server --wizard
```

### Features Detection

The wizard automatically detects:
- **React/Node.js** on port 3000
- **Flask/Python** on port 5000
- **Angular** on port 4200
- **Vite** on port 5173
- **Django** on port 8000
- **Jupyter Notebook** on port 8888

---

## CLI UX Enhancements

New in v0.3.0: Beautiful, informative command-line interface with real-time feedback.

### Features

- **Progress Bars**: Visual feedback for long-running operations
- **Live Displays**: Real-time updating status information
- **Rich Terminal UI**: Colored output, tables, and panels
- **Graceful Fallbacks**: Works without rich library in plain terminals
- **Status Command**: New `pytunnel-status` command

### Progress Tracking

```python
from pytunnel.common.cli_display import ProgressTracker

tracker = ProgressTracker()

# Track task progress
with tracker.track_task("Processing requests", total=100) as update:
    for i in range(100):
        # Do work
        update(1)  # Increment by 1

# Track downloads with bandwidth display
with tracker.track_download("Downloading file", total=1000000) as update:
    update(500000)  # Update progress
```

### Live Status Display

```python
from pytunnel.common.cli_display import LiveDisplay

display = LiveDisplay()

# Live updating display
with display.live_display() as update:
    update("Status: Connecting...")
    # Do work
    update("Status: Connected!")

# Spinner for operations
with display.spinner("Processing..."):
    # Long operation
    pass
```

### Status Command

```bash
# Show all status information
pytunnel-status

# Show only tunnels
pytunnel-status --tunnels-only

# Show only security info
pytunnel-status --security-only

# Show only compliance info
pytunnel-status --compliance-only

# JSON output
pytunnel-status --json
```

### Status Display

```python
from pytunnel.common.cli_display import get_status_display

display = get_status_display()

# Show tunnel status
display.show_tunnel_status(tunnels)

# Show security status
display.show_security_status(security_stats)

# Show compliance status
display.show_compliance_status(compliance_status)

# Show complete summary
display.show_summary(tunnels, security, compliance)
```

---

## Shareable Tunnel Links

New in v0.3.0: Create temporary shareable links for demos and testing.

### Features

- **Time-Limited Access**: Links expire after specified duration (max 7 days)
- **Password Protection**: Optional password for access control
- **IP Whitelist**: Restrict access to specific IP addresses
- **Access Count Limits**: Limit number of times link can be used
- **Brute-Force Protection**: 3 failed attempts = 15 minute lockout
- **Beautiful Landing Page**: Professional share page with instructions

### Usage

```python
from pytunnel.common.shares import get_share_manager

manager = get_share_manager()

# Create a share link
share = manager.create_share(
    tunnel_id="abc123",
    expires_in_seconds=3600,  # 1 hour
    password="demo123",
    ip_whitelist={"192.168.1.0/24"},
    max_access_count=10
)

print(f"Share URL: /share/{share.share_id}")
print(f"Password: {share.password}")
print(f"Expires: {share.expires_at}")
```

### Access Share

```bash
# Access via browser
http://tunnel.example.com:8080/share/xyz789

# Enter password if required
# Link redirects to actual tunnel
```

### Share Management

```python
# Get share details
share = manager.get_share("xyz789")

# Verify access
allowed, reason = manager.verify_share_access(
    share_id="xyz789",
    password="demo123",
    ip_address="192.168.1.100"
)

# List all shares
shares = manager.list_shares(tunnel_id="abc123")

# Delete share
manager.delete_share("xyz789")

# Cleanup expired
removed = manager.cleanup_expired()
```

### Share Properties

```python
@dataclass
class Share:
    share_id: str           # Unique share ID
    tunnel_id: str          # Associated tunnel
    created_at: float       # Creation timestamp
    expires_at: float       # Expiration timestamp
    password: Optional[str] # Password hash (if protected)
    ip_whitelist: Set[str]  # Allowed IP addresses/ranges
    max_access_count: int   # Max number of accesses
    access_count: int       # Current access count
```

### Security Features

- **Maximum 7-day expiration**: Prevents long-lived shares
- **Password hashing**: Passwords stored with SHA-256
- **Rate limiting**: 3 failed attempts triggers 15-minute lockout
- **IP validation**: CIDR support for network ranges
- **Access tracking**: Monitor who accessed and when

---

## Webhook Integrations

New in v0.3.0: Get notified about tunnel events via webhooks.

### Features

- **Multi-Platform Support**: Slack, Discord, PagerDuty, custom webhooks
- **Event Filtering**: Choose which events to send
- **HMAC Signatures**: Verify webhook authenticity
- **SSRF Protection**: Blocks localhost and private IPs
- **Rate Limiting**: Prevents webhook spam
- **Retry Logic**: Automatic retries with exponential backoff

### Supported Platforms

- **Slack**: Native Slack message formatting
- **Discord**: Rich Discord embeds
- **PagerDuty**: Incident creation
- **Custom**: Generic webhook with JSON payload

### Usage

```python
from pytunnel.common.webhooks import get_webhook_manager, WebhookType

manager = get_webhook_manager()

# Add Slack webhook
manager.add_webhook(
    url="https://hooks.slack.com/services/YOUR/WEBHOOK/URL",
    webhook_type=WebhookType.SLACK,
    events=["tunnel.created", "tunnel.deleted", "security.alert"],
    secret="your-secret-key"  # For HMAC signatures
)

# Add Discord webhook
manager.add_webhook(
    url="https://discord.com/api/webhooks/YOUR/WEBHOOK",
    webhook_type=WebhookType.DISCORD,
    events=["*.created", "*.deleted"]  # Wildcard patterns
)

# Trigger webhook
await manager.trigger(
    event="tunnel.created",
    data={
        "tunnel_id": "abc123",
        "subdomain": "myapp",
        "user": "john@example.com"
    }
)
```

### Event Types

- `tunnel.created` - New tunnel created
- `tunnel.deleted` - Tunnel closed
- `tunnel.request` - Request received (high volume!)
- `share.created` - Share link created
- `share.accessed` - Share link accessed
- `security.alert` - Security event detected
- `auth.failed` - Authentication failure
- `config.changed` - Configuration updated

### Webhook Payload

```json
{
  "event": "tunnel.created",
  "timestamp": 1700000000.123,
  "data": {
    "tunnel_id": "abc123",
    "subdomain": "myapp",
    "user": "john@example.com",
    "ip_address": "192.168.1.1"
  }
}
```

### HMAC Signature Verification

```python
import hmac
import hashlib

def verify_webhook(payload: bytes, signature: str, secret: str) -> bool:
    expected = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(signature, expected)
```

Signature sent in `X-Webhook-Signature` header.

### Security Features

- **URL Validation**: Blocks localhost (127.0.0.1), private IPs (10.x, 192.168.x)
- **HTTPS Required**: For production webhooks
- **Rate Limiting**: Max 10 webhooks per minute per endpoint
- **Timeout**: 5 second timeout for webhook requests
- **HMAC**: Sign payloads with shared secret

---

## Advanced Security

New in v0.3.0: Enterprise-grade security features.

### Features

- **IP Filtering**: Whitelist/blacklist with CIDR support
- **Connection Limits**: Per-IP and total limits
- **Rate Limiting**: Requests per minute limits
- **DDoS Protection**: Auto-blocking after violations
- **Security Score**: 0-100 score based on configuration
- **Connection Tracking**: Monitor active connections

### Security Presets

```python
from pytunnel.common.security import SecurityConfig, SecurityPreset

# Basic (permissive)
config = SecurityConfig.from_preset(SecurityPreset.BASIC)

# Standard (balanced)
config = SecurityConfig.from_preset(SecurityPreset.STANDARD)

# Paranoid (strict)
config = SecurityConfig.from_preset(SecurityPreset.PARANOID)
```

### IP Filtering

```python
from pytunnel.common.security import SecurityConfig, SecurityManager

# Whitelist mode
config = SecurityConfig(
    ip_whitelist={"192.168.1.0/24", "10.0.0.100"}
)

# Blacklist mode
config = SecurityConfig(
    ip_blacklist={"1.2.3.4", "5.6.7.0/24"}
)

manager = SecurityManager(config)

# Check if IP allowed
allowed, reason = manager.check_connection("192.168.1.50")
```

### Connection Limiting

```python
config = SecurityConfig(
    max_connections_per_ip=5,      # Max 5 per IP
    max_connections_total=100,     # Max 100 total
    connection_rate_limit=10       # Max 10 new connections per minute
)

manager = SecurityManager(config)

# Register connection
manager.register_connection("192.168.1.1")

# Unregister when done
manager.unregister_connection("192.168.1.1")

# Get connection stats
stats = manager.get_stats()
```

### DDoS Protection

```python
config = SecurityConfig(
    request_rate_limit=100,  # Max 100 requests per minute per IP
    block_threshold=3        # Auto-block after 3 violations
)

manager = SecurityManager(config)

# Check request rate
allowed, reason = manager.check_request("192.168.1.1")

# Get blocked IPs
blocked = manager.get_blocked_ips()

# Manually unblock
manager.unblock_ip("192.168.1.1")
```

### Security Score

```python
manager = SecurityManager(config)

# Get security score (0-100)
score = manager.get_security_score()

# Score factors:
# - IP filtering enabled: +20
# - Connection limits set: +20
# - Rate limiting enabled: +20
# - Signature required: +20
# - Encryption enabled: +20
```

### Security Stats

```python
stats = manager.get_stats()

# {
#   'security_score': 85,
#   'connections': {
#     'total_connections': 10,
#     'connections_by_ip': {'192.168.1.1': 2}
#   },
#   'blocked_ips': [
#     {'ip': '1.2.3.4', 'blocked_at': 1700000000, 'reason': 'Rate limit'}
#   ],
#   'config': {
#     'has_whitelist': True,
#     'has_blacklist': False,
#     'max_connections_per_ip': 5
#   }
# }
```

---

## Compliance & Audit Logging

New in v0.3.0: Enterprise compliance and GDPR-ready audit logging.

### Features

- **Tamper-Evident Logging**: Cryptographic hash chains
- **Audit Trail**: Comprehensive event logging
- **GDPR Tools**: Data export and deletion
- **Data Retention**: Configurable retention policies
- **Auto-Cleanup**: Automatic old data removal
- **Integrity Verification**: Detect log tampering

### Audit Logging

```python
from pytunnel.common.compliance import (
    get_compliance_manager, AuditEventType
)

manager = get_compliance_manager()

# Log an event
entry = manager.audit_logger.log_event(
    event_type=AuditEventType.TUNNEL_CREATED,
    user_id="john@example.com",
    ip_address="192.168.1.1",
    details={"tunnel_id": "abc123", "subdomain": "myapp"}
)

# Get audit logs
logs = manager.audit_logger.get_entries(
    user_id="john@example.com",
    event_type=AuditEventType.TUNNEL_CREATED.value,
    limit=100
)

# Verify integrity
is_valid, errors = manager.audit_logger.verify_integrity()

# Export logs
manager.audit_logger.export_to_json("audit_export.json")
```

### Event Types

```python
class AuditEventType(Enum):
    USER_CREATED = "user.created"
    USER_DELETED = "user.deleted"
    USER_LOGIN = "user.login"
    USER_LOGOUT = "user.logout"
    TUNNEL_CREATED = "tunnel.created"
    TUNNEL_DELETED = "tunnel.deleted"
    SHARE_CREATED = "share.created"
    SHARE_ACCESSED = "share.accessed"
    DATA_EXPORTED = "data.exported"
    DATA_DELETED = "data.deleted"
    CONFIG_CHANGED = "config.changed"
    SECURITY_ALERT = "security.alert"
```

### Data Retention

```python
from pytunnel.common.compliance import RetentionPolicy

policy = RetentionPolicy(
    log_retention_days=90,      # Keep logs for 90 days
    share_retention_days=30,    # Keep shares for 30 days
    traffic_retention_days=7,   # Keep traffic logs for 7 days
    auto_cleanup_enabled=True   # Auto-cleanup old data
)

manager = get_compliance_manager(retention_policy=policy)

# Manual cleanup
stats = manager.retention_manager.cleanup_old_data(
    audit_logger=manager.audit_logger,
    share_manager=shares,
    traffic_inspector=traffic
)

# {'audit_logs_removed': 50, 'shares_removed': 10, 'traffic_logs_removed': 1000}
```

### GDPR Compliance

```python
# Export user data (Right to Access)
data = manager.gdpr_manager.export_user_data(
    user_id="john@example.com",
    include_logs=True,
    include_tunnels=True,
    include_shares=True
)

# {
#   'user_id': 'john@example.com',
#   'export_timestamp': 1700000000.0,
#   'data': {
#     'audit_logs': [...],
#     'tunnels': [...],
#     'shares': [...]
#   }
# }

# Delete user data (Right to Erasure)
stats = manager.gdpr_manager.delete_user_data(
    user_id="john@example.com",
    delete_logs=False,  # Keep audit trail for compliance
    delete_tunnels=True,
    delete_shares=True
)

# {'tunnels_deleted': 5, 'shares_deleted': 2}
```

### Compliance Status

```python
status = manager.get_compliance_status()

# {
#   'audit_log_integrity': True,
#   'audit_log_errors': [],
#   'total_audit_entries': 1234,
#   'retention_policy': {
#     'log_retention_days': 90,
#     'auto_cleanup_enabled': True
#   },
#   'last_cleanup': 1700000000.0,
#   'gdpr_ready': True
# }
```

### Tamper Detection

The audit log uses a cryptographic hash chain:

```python
# Each entry contains:
# - previous_hash: Hash of previous entry
# - entry_hash: Hash of current entry + previous_hash

# This creates an immutable chain
# Any tampering breaks the chain and is detected

entry1 = log_event(...)  # previous_hash = None
entry2 = log_event(...)  # previous_hash = entry1.entry_hash
entry3 = log_event(...)  # previous_hash = entry2.entry_hash

# If entry2 is modified, entry3.previous_hash won't match
# verify_integrity() will detect this
```

---

For more information, see the main [README.md](README.md) and [USAGE.md](USAGE.md).
