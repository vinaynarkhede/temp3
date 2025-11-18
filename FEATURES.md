## PyTunnel Advanced Features

Comprehensive guide to all advanced features in PyTunnel v0.2.0

---

## Table of Contents

1. [HTTPS/TLS Support](#httpstls-support)
2. [Custom Subdomains](#custom-subdomains)
3. [Authentication & Authorization](#authentication--authorization)
4. [Web Dashboard](#web-dashboard)
5. [Traffic Inspection & Logging](#traffic-inspection--logging)
6. [TCP Tunnel Support](#tcp-tunnel-support)
7. [Bandwidth Limiting](#bandwidth-limiting)
8. [Multiple Protocol Support](#multiple-protocol-support)
9. [Configuration Management](#configuration-management)

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

For more information, see the main [README.md](README.md) and [USAGE.md](USAGE.md).
