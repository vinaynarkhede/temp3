# PyTunnel Quick Start

Get PyTunnel running in 2 minutes!

## Prerequisites

- Python 3.8+ installed
- Git installed

## Installation (30 seconds)

```bash
# Clone and navigate
git clone <repository-url>
cd pytunnel

# Setup virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Run PyTunnel (1 minute)

Open **3 terminals** in the `pytunnel` directory:

### Terminal 1: Start Server

```bash
source venv/bin/activate  # Windows: venv\Scripts\activate
python -m pytunnel.server.cli --port 8080
```

### Terminal 2: Start Local Service

```bash
source venv/bin/activate  # Windows: venv\Scripts\activate
python examples/simple_server.py 3000
```

### Terminal 3: Start Client

```bash
source venv/bin/activate  # Windows: venv\Scripts\activate
python -m pytunnel.client.cli 3000 --server http://localhost:8080
```

**Look for your tunnel URL in Terminal 3:**
```
============================================================
  Tunnel URL: http://localhost:8080/abc12345
  Forwarding to: http://localhost:3000
============================================================
```

## Test It (30 seconds)

Open browser or use curl:

```bash
# Replace abc12345 with your client ID
curl http://localhost:8080/abc12345/
```

You should see a JSON response! 🎉

## What's Next?

- **Having issues?** See [SETUP.md](SETUP.md) for detailed troubleshooting
- **Want more examples?** See [USAGE.md](USAGE.md) for advanced usage
- **Understanding how it works?** See [README.md](README.md) for architecture

## Common Commands

```bash
# Run with custom port
python -m pytunnel.server.cli --port 9090

# Use custom client ID
python -m pytunnel.client.cli 3000 --client-id my-app

# Expose different local port
python -m pytunnel.client.cli 5000 --server http://localhost:8080
```

---

**Need help?** Check the full [SETUP.md](SETUP.md) guide!
