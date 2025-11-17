.PHONY: help install test clean server client demo

help:
	@echo "PyTunnel - Makefile Commands"
	@echo "============================="
	@echo ""
	@echo "  make install    - Install dependencies and package"
	@echo "  make test       - Run tests"
	@echo "  make server     - Start tunnel server"
	@echo "  make client     - Start tunnel client (requires PORT)"
	@echo "  make demo       - Run demo with all components"
	@echo "  make clean      - Clean build artifacts"
	@echo ""
	@echo "Examples:"
	@echo "  make server"
	@echo "  make client PORT=3000"
	@echo "  make demo"

install:
	@echo "Installing dependencies..."
	pip install -r requirements.txt
	@echo "Installing PyTunnel..."
	pip install -e .
	@echo "Done!"

test:
	@echo "Running tests..."
	python -m pytest tests/ -v

clean:
	@echo "Cleaning build artifacts..."
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	@echo "Done!"

server:
	@echo "Starting PyTunnel Server..."
	@echo "Press Ctrl+C to stop"
	@echo ""
	python -m pytunnel.server.cli --port 8080

client:
	@ifndef PORT
		$(error PORT is required. Usage: make client PORT=3000)
	@endif
	@echo "Starting PyTunnel Client..."
	@echo "Forwarding localhost:$(PORT) through tunnel"
	@echo "Press Ctrl+C to stop"
	@echo ""
	python -m pytunnel.client.cli $(PORT) --server http://localhost:8080

demo:
	@echo "Starting PyTunnel Demo..."
	@echo "This will open 3 terminal windows"
	@echo ""
	bash examples/quickstart.sh

dev-server:
	@echo "Starting example HTTP server on port 3000..."
	python examples/simple_server.py 3000
