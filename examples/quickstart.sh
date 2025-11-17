#!/bin/bash

# QuickStart script for PyTunnel
# This script demonstrates how to run PyTunnel locally

echo "PyTunnel QuickStart"
echo "==================="
echo ""
echo "This script will start:"
echo "1. A tunnel server on port 8080"
echo "2. A simple HTTP server on port 3000"
echo "3. A tunnel client connecting them"
echo ""
echo "Press Ctrl+C in any terminal to stop that component"
echo ""

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed"
    exit 1
fi

# Check if in the right directory
if [ ! -f "setup.py" ]; then
    echo "Error: Please run this script from the PyTunnel root directory"
    exit 1
fi

echo "Opening 3 terminal windows..."
echo ""
echo "Terminal 1: Tunnel Server (port 8080)"
echo "Terminal 2: Local HTTP Server (port 3000)"
echo "Terminal 3: Tunnel Client"
echo ""
echo "After all terminals are open:"
echo "- Wait for the client to connect and display the tunnel URL"
echo "- Test the tunnel by visiting the URL in your browser"
echo "- Or use: curl http://localhost:8080/<client-id>/"
echo ""

# Determine the terminal emulator
if command -v gnome-terminal &> /dev/null; then
    TERM_CMD="gnome-terminal --"
elif command -v xterm &> /dev/null; then
    TERM_CMD="xterm -e"
elif command -v konsole &> /dev/null; then
    TERM_CMD="konsole -e"
else
    echo "Manual setup required:"
    echo ""
    echo "Terminal 1 - Start the tunnel server:"
    echo "  python -m pytunnel.server.cli --port 8080"
    echo ""
    echo "Terminal 2 - Start a local HTTP server:"
    echo "  python examples/simple_server.py 3000"
    echo ""
    echo "Terminal 3 - Start the tunnel client:"
    echo "  python -m pytunnel.client.cli 3000 --server http://localhost:8080"
    echo ""
    exit 0
fi

# Start server
$TERM_CMD bash -c "echo 'Starting Tunnel Server...'; python -m pytunnel.server.cli --port 8080; exec bash" &
sleep 2

# Start local HTTP server
$TERM_CMD bash -c "echo 'Starting Local HTTP Server...'; python examples/simple_server.py 3000; exec bash" &
sleep 2

# Start client
$TERM_CMD bash -c "echo 'Starting Tunnel Client...'; python -m pytunnel.client.cli 3000 --server http://localhost:8080; exec bash" &

echo "All components started!"
echo ""
echo "To test the tunnel:"
echo "1. Look for the tunnel URL in the client terminal"
echo "2. Visit that URL in your browser or use curl"
echo ""
