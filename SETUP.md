# PyTunnel Setup Guide

Complete step-by-step guide to set up and run PyTunnel on your system.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Installation](#installation)
  - [Option 1: Quick Setup (Recommended)](#option-1-quick-setup-recommended)
  - [Option 2: Development Setup](#option-2-development-setup)
- [Verification](#verification)
- [First Run](#first-run)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required

- **Python 3.8 or higher**
- **Git** (to clone the repository)
- **pip** (Python package manager, usually comes with Python)

### Check if you have Python installed

```bash
python3 --version
# or
python --version
```

You should see output like: `Python 3.8.x` or higher

If Python is not installed, download it from [python.org](https://www.python.org/downloads/)

### Check if you have Git installed

```bash
git --version
```

If Git is not installed, download it from [git-scm.com](https://git-scm.com/downloads)

---

## Installation

### Option 1: Quick Setup (Recommended)

This is the fastest way to get PyTunnel running for testing and development.

#### Step 1: Clone the Repository

```bash
# Clone the repository
git clone <your-repository-url>

# Navigate into the directory
cd pytunnel
```

If you don't have a repository URL yet, you can download the source code directly.

#### Step 2: Create a Virtual Environment (Recommended)

Using a virtual environment keeps PyTunnel's dependencies separate from your system Python.

**On Linux/macOS:**
```bash
# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate
```

**On Windows:**
```bash
# Create virtual environment
python -m venv venv

# Activate it
venv\Scripts\activate
```

You should see `(venv)` appear in your terminal prompt when the virtual environment is active.

#### Step 3: Install Dependencies

```bash
# Install required packages
pip install -r requirements.txt
```

This will install:
- `aiohttp` - For HTTP server and client
- `websockets` - For WebSocket communication
- `uvicorn` - ASGI server
- `python-dotenv` - Environment variable management
- `colorama` - Colored terminal output

#### Step 4: Verify Installation

```bash
# Test if the modules can be imported
python -c "import pytunnel; print('PyTunnel imported successfully!')"
```

If you see "PyTunnel imported successfully!" you're ready to go!

---

### Option 2: Development Setup

This option installs PyTunnel as a package with command-line tools.

#### Step 1-2: Same as Option 1

Follow Step 1 and Step 2 from Option 1 above.

#### Step 3: Install PyTunnel as a Package

```bash
# Install in development mode
pip install -e .
```

This creates the command-line tools:
- `pytunnel-server` - Start the tunnel server
- `pytunnel-client` - Start the tunnel client

#### Step 4: Verify Installation

```bash
# Check if commands are available
pytunnel-server --help
pytunnel-client --help
```

You should see help text for each command.

---

## Verification

Let's make sure everything is working correctly.

### Test 1: Protocol Test

```bash
python -c "from pytunnel.common.protocol import create_register_message; print('Protocol OK')"
```

Expected output: `Protocol OK`

### Test 2: Run Unit Tests (Optional)

```bash
# Install pytest (if not already installed)
pip install pytest pytest-asyncio

# Run tests
python -m pytest tests/ -v
```

You should see tests passing.

---

## First Run

Now let's run PyTunnel for the first time!

### Terminal Setup

You'll need **3 terminal windows/tabs**. Keep your virtual environment activated in each terminal.

### Terminal 1: Start the Tunnel Server

```bash
# Activate virtual environment (if not already active)
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate  # Windows

# Start the server
python -m pytunnel.server.cli --port 8080
```

**Expected Output:**
```
2025-11-17 12:00:00 - TunnelServer - INFO - HTTP Proxy listening on http://0.0.0.0:8080
2025-11-17 12:00:00 - TunnelServer - INFO - WebSocket Tunnel listening on ws://0.0.0.0:8080/tunnel
2025-11-17 12:00:00 - TunnelServer - INFO - Server started successfully!
```

✅ Leave this terminal running

### Terminal 2: Start a Local Service

```bash
# Activate virtual environment
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate  # Windows

# Start the example HTTP server
python examples/simple_server.py 3000
```

**Expected Output:**
```
Starting server on http://localhost:3000
Press Ctrl+C to stop
```

✅ Leave this terminal running

### Terminal 3: Start the Tunnel Client

```bash
# Activate virtual environment
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate  # Windows

# Start the client
python -m pytunnel.client.cli 3000 --server http://localhost:8080
```

**Expected Output:**
```
PyTunnel Client
Connecting to server: http://localhost:8080
Local service: http://localhost:3000

2025-11-17 12:00:05 - TunnelClient - INFO - Connecting to tunnel server...
2025-11-17 12:00:05 - TunnelClient - INFO - Connected to tunnel server
2025-11-17 12:00:05 - TunnelClient - INFO - Tunnel established!

============================================================
  Tunnel URL: http://localhost:8080/abc12345
  Forwarding to: http://localhost:3000
============================================================
```

✅ Leave this terminal running

**Note:** Your client ID (e.g., `abc12345`) will be different - it's randomly generated.

### Terminal 4: Test the Tunnel

Open a **4th terminal** to test the tunnel:

```bash
# Replace 'abc12345' with your actual client ID from Terminal 3
curl http://localhost:8080/abc12345/
```

**Expected Output:**
You should see a JSON response from the simple server!

```json
{
  "message": "Hello from PyTunnel!",
  "path": "/",
  "method": "GET",
  "timestamp": "2025-11-17T12:00:10.123456"
}
```

### Test in Browser

You can also open your browser and visit:
```
http://localhost:8080/abc12345/
```

You should see the same JSON response!

---

## Quick Commands with Makefile

If you have `make` installed, you can use these shortcuts:

```bash
# Start the server
make server

# Start the client (specify PORT)
make client PORT=3000

# Run tests
make test

# Install dependencies
make install

# Clean build artifacts
make clean
```

---

## Common Usage Patterns

### Pattern 1: Expose Your Web App

```bash
# Terminal 1: Start server
python -m pytunnel.server.cli --port 8080

# Terminal 2: Start your web app (example with React)
cd my-react-app
npm start  # Usually runs on port 3000

# Terminal 3: Start tunnel client
python -m pytunnel.client.cli 3000 --server http://localhost:8080
```

### Pattern 2: Expose Your API

```bash
# Terminal 1: Start server
python -m pytunnel.server.cli --port 8080

# Terminal 2: Start your API (example with Flask)
cd my-api
python app.py  # Runs on port 5000

# Terminal 3: Start tunnel client
python -m pytunnel.client.cli 5000 --server http://localhost:8080
```

### Pattern 3: Custom Client ID

```bash
# Use a memorable client ID instead of random
python -m pytunnel.client.cli 3000 \
  --server http://localhost:8080 \
  --client-id my-project

# Your tunnel URL will be:
# http://localhost:8080/my-project
```

---

## Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'pytunnel'"

**Solution:**
- Make sure you've installed the dependencies: `pip install -r requirements.txt`
- Make sure you're in the correct directory (the `pytunnel` project root)
- Make sure your virtual environment is activated (you should see `(venv)` in your prompt)

### Issue: "Address already in use" error

**Solution:**
- Port 8080 or 3000 is already being used by another program
- Either stop the other program or use a different port:
  ```bash
  # Use port 9090 instead
  python -m pytunnel.server.cli --port 9090
  ```

### Issue: Client can't connect to server

**Solution:**
- Make sure the server is running first
- Check that the server URL is correct
- If using a remote server, make sure the port is open in the firewall
- Try using the IP address instead of hostname

### Issue: Virtual environment not activating on Windows

**Solution:**
- You might need to allow script execution:
  ```powershell
  Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
  ```
- Then try activating again:
  ```powershell
  venv\Scripts\activate
  ```

### Issue: "pip: command not found"

**Solution:**
- Try using `pip3` instead of `pip`
- Or use: `python -m pip install -r requirements.txt`
- Make sure Python is properly installed

### Issue: Colors not showing on Windows

**Solution:**
- Colors are supported on Windows 10+
- For older Windows versions, the application will work but without colors
- Alternatively, use Windows Terminal or ConEmu for better color support

### Issue: Import errors on Windows

**Solution:**
- Windows uses different path separators
- Make sure you're using Python 3.8 or higher
- Try reinstalling dependencies:
  ```bash
  pip uninstall -r requirements.txt -y
  pip install -r requirements.txt
  ```

---

## Deactivating Virtual Environment

When you're done, you can deactivate the virtual environment:

```bash
deactivate
```

The `(venv)` prefix will disappear from your terminal prompt.

---

## Next Steps

Now that you have PyTunnel set up and running:

1. **Read the full documentation:**
   - [README.md](README.md) - Project overview and architecture
   - [USAGE.md](USAGE.md) - Detailed usage examples

2. **Try advanced features:**
   - Multiple simultaneous tunnels
   - Custom client IDs
   - Deploy server to a public cloud

3. **Development:**
   - Read the code in `pytunnel/` directory
   - Run tests: `python -m pytest tests/ -v`
   - Contribute improvements!

---

## Platform-Specific Notes

### Linux

- Uses `source venv/bin/activate`
- Colors work out of the box
- May need `sudo` for ports < 1024

### macOS

- Same as Linux
- Uses `source venv/bin/activate`
- Colors work out of the box

### Windows

- Uses `venv\Scripts\activate`
- PowerShell recommended over CMD
- Windows Terminal recommended for best experience
- May need to enable script execution (see troubleshooting)

---

## Getting Help

If you encounter issues not covered here:

1. Check the [README.md](README.md) and [USAGE.md](USAGE.md)
2. Look for similar issues in the project's issue tracker
3. Create a new issue with:
   - Your operating system
   - Python version (`python --version`)
   - Error messages (full output)
   - Steps to reproduce

---

## Summary Checklist

- [ ] Python 3.8+ installed
- [ ] Git installed
- [ ] Repository cloned
- [ ] Virtual environment created and activated
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] Server starts successfully
- [ ] Client connects successfully
- [ ] Can access tunnel URL

If you've checked all these boxes, you're ready to use PyTunnel! 🎉
