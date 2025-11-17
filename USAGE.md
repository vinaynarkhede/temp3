# PyTunnel Usage Guide

## Quick Start

### 1. Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Or install the package (recommended)
pip install .
```

### 2. Basic Usage

#### Option A: Using installed commands (after pip install)

```bash
# Start the server
pytunnel-server --host 0.0.0.0 --port 8080

# Start the client
pytunnel-client 3000 --server http://your-server-ip:8080
```

#### Option B: Using Python modules (without installation)

```bash
# Start the server
python -m pytunnel.server.cli --host 0.0.0.0 --port 8080

# Start the client
python -m pytunnel.client.cli 3000 --server http://your-server-ip:8080
```

## Detailed Examples

### Example 1: Local Testing

**Terminal 1 - Start the tunnel server:**
```bash
python -m pytunnel.server.cli --port 8080
```

Output:
```
2025-11-17 12:00:00 - TunnelServer - INFO - HTTP Proxy listening on http://0.0.0.0:8080
2025-11-17 12:00:00 - TunnelServer - INFO - WebSocket Tunnel listening on ws://0.0.0.0:8080/tunnel
2025-11-17 12:00:00 - TunnelServer - INFO - Server started successfully!
```

**Terminal 2 - Start a local web service:**
```bash
# Option 1: Use the provided example server
python examples/simple_server.py 3000

# Option 2: Use Python's built-in HTTP server
python -m http.server 3000

# Option 3: Your own application
cd my-app && npm run dev  # if using Node.js
```

**Terminal 3 - Start the tunnel client:**
```bash
python -m pytunnel.client.cli 3000 --server http://localhost:8080
```

Output:
```
PyTunnel Client
Connecting to server: http://localhost:8080
Local service: http://localhost:3000

2025-11-17 12:00:05 - TunnelClient - INFO - Connecting to tunnel server: ws://localhost:8080/tunnel
2025-11-17 12:00:05 - TunnelClient - INFO - Connected to tunnel server
2025-11-17 12:00:05 - TunnelClient - INFO - Sent registration for client: abc12345
2025-11-17 12:00:05 - TunnelClient - INFO - Tunnel established! URL: http://localhost:8080/abc12345

============================================================
  Tunnel URL: http://localhost:8080/abc12345
  Forwarding to: http://localhost:3000
============================================================
```

**Terminal 4 - Test the tunnel:**
```bash
# Make a GET request
curl http://localhost:8080/abc12345/

# Make a POST request
curl -X POST http://localhost:8080/abc12345/api/test \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello from tunnel!"}'
```

### Example 2: Production Deployment

#### On your public server (e.g., AWS, DigitalOcean):

```bash
# Install PyTunnel
git clone <repository-url>
cd pytunnel
pip install -r requirements.txt

# Run the server (use a process manager like systemd or supervisor)
python -m pytunnel.server.cli --host 0.0.0.0 --port 8080
```

#### On your local machine:

```bash
# Connect to the remote server
python -m pytunnel.client.cli 3000 \
  --server http://your-server-ip:8080 \
  --client-id my-project
```

#### Share the URL:

```
Your tunnel URL: http://your-server-ip:8080/my-project
```

### Example 3: Testing Webhooks

Many services (GitHub, Stripe, etc.) need to send webhooks to your application. Use PyTunnel to expose your local development server:

```bash
# Your webhook handler is running on localhost:5000
python -m pytunnel.client.cli 5000 --server http://tunnel.example.com:8080

# Use the tunnel URL in the webhook configuration:
# http://tunnel.example.com:8080/<your-client-id>/webhooks
```

## Command-Line Options

### Server Options

```bash
python -m pytunnel.server.cli --help
```

Options:
- `--host HOST`: Host to bind to (default: 0.0.0.0)
- `--port PORT`: Port for HTTP proxy (default: 8080)

### Client Options

```bash
python -m pytunnel.client.cli --help
```

Arguments:
- `local_port`: Local port to forward requests to (required)

Options:
- `--server URL`: Tunnel server URL (default: http://localhost:8080)
- `--local-host HOST`: Local host to forward to (default: localhost)
- `--client-id ID`: Custom client ID (optional, auto-generated if not provided)

## Advanced Usage

### Custom Client ID

Use a memorable client ID instead of a random one:

```bash
python -m pytunnel.client.cli 3000 \
  --server http://tunnel.example.com:8080 \
  --client-id my-awesome-app
```

Tunnel URL: `http://tunnel.example.com:8080/my-awesome-app`

### Multiple Tunnels

Run multiple clients to the same server with different IDs:

```bash
# Terminal 1 - Frontend on port 3000
python -m pytunnel.client.cli 3000 \
  --server http://tunnel.example.com:8080 \
  --client-id frontend

# Terminal 2 - Backend API on port 5000
python -m pytunnel.client.cli 5000 \
  --server http://tunnel.example.com:8080 \
  --client-id backend-api
```

Access:
- Frontend: `http://tunnel.example.com:8080/frontend`
- Backend: `http://tunnel.example.com:8080/backend-api`

### Running as a Background Service

Using systemd (Linux):

Create `/etc/systemd/system/pytunnel-server.service`:

```ini
[Unit]
Description=PyTunnel Server
After=network.target

[Service]
Type=simple
User=pytunnel
WorkingDirectory=/opt/pytunnel
ExecStart=/usr/bin/python3 -m pytunnel.server.cli --port 8080
Restart=always

[Install]
WantedBy=multi-user.target
```

Then:

```bash
sudo systemctl daemon-reload
sudo systemctl enable pytunnel-server
sudo systemctl start pytunnel-server
```

## Troubleshooting

### Client can't connect to server

1. Check server is running: `curl http://server-ip:8080/`
2. Check firewall allows port 8080
3. Verify server URL is correct (including http://)

### Requests timing out

1. Check local service is running: `curl http://localhost:3000/`
2. Check client is connected (look for "Tunnel established" message)
3. Increase timeout if needed (currently 30 seconds)

### Connection keeps dropping

- Check network stability
- Server logs will show disconnections
- Client auto-reconnects after 5 seconds

## Testing

### Run Protocol Tests

```bash
# Install pytest
pip install pytest pytest-asyncio

# Run tests
python -m pytest tests/ -v
```

### Manual Testing Script

```bash
# Run the quickstart script for automatic setup
bash examples/quickstart.sh
```

## Performance Considerations

- Each client maintains one WebSocket connection
- HTTP requests are proxied synchronously through tunnels
- Suitable for development and testing, not high-traffic production
- Consider rate limiting for public deployments

## Security Notes

- No built-in authentication - anyone with the URL can access your service
- Use firewall rules to restrict server access if needed
- For production, consider adding:
  - Authentication tokens
  - HTTPS/TLS encryption
  - Rate limiting
  - Access logs

## Next Steps

- Read the main [README.md](README.md) for architecture details
- Check out [examples/](examples/) for sample code
- Contribute improvements via Pull Requests
