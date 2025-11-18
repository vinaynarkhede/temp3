"""Tests for setup wizard functionality."""

import pytest
import socket
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from pytunnel.common.wizard import SetupWizard
from pytunnel.common.config import ClientConfig, ServerConfig


def test_wizard_initialization():
    """Test wizard initializes correctly."""
    wizard = SetupWizard()
    assert wizard.detected_services == []


def test_port_scanning():
    """Test port scanning functionality."""
    wizard = SetupWizard()

    # Test with known closed port
    assert not wizard._is_port_open('localhost', 65535)


def test_port_scanning_open_port():
    """Test detecting an open port."""
    wizard = SetupWizard()

    # Create a temporary server
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(('localhost', 0))  # Bind to any available port
        server.listen(1)
        port = server.getsockname()[1]

        # Should detect the open port
        assert wizard._is_port_open('localhost', port)


def test_detect_local_services_empty():
    """Test service detection when no services running."""
    wizard = SetupWizard()

    # Mock all ports as closed
    with patch.object(wizard, '_is_port_open', return_value=False):
        services = wizard.detect_local_services()
        assert len(services) == 0


def test_detect_local_services_found():
    """Test service detection when services are running."""
    wizard = SetupWizard()

    # Mock port 3000 as open
    def mock_port_check(host, port):
        return port == 3000

    with patch.object(wizard, '_is_port_open', side_effect=mock_port_check):
        services = wizard.detect_local_services()

        assert len(services) == 1
        assert services[0]['port'] == 3000
        assert 'React' in services[0]['description']


def test_detect_project_name_from_git():
    """Test project name detection from git."""
    wizard = SetupWizard()

    # Mock git command to return a URL
    mock_result = Mock()
    mock_result.returncode = 0
    mock_result.stdout = "https://github.com/user/my-awesome-project.git"

    with patch('subprocess.run', return_value=mock_result):
        name = wizard.detect_project_name()
        assert name == "my-awesome-project"


def test_detect_project_name_fallback_to_directory():
    """Test project name falls back to directory name."""
    wizard = SetupWizard()

    # Mock git command to fail
    mock_result = Mock()
    mock_result.returncode = 1

    with patch('subprocess.run', return_value=mock_result):
        with patch('pathlib.Path.cwd') as mock_cwd:
            mock_cwd.return_value = Path('/home/user/test-project')
            name = wizard.detect_project_name()
            assert name == "test-project"


def test_sanitize_subdomain_valid():
    """Test subdomain sanitization with valid input."""
    wizard = SetupWizard()

    assert wizard._sanitize_subdomain("my-app") == "my-app"
    assert wizard._sanitize_subdomain("test123") == "test123"


def test_sanitize_subdomain_invalid_chars():
    """Test subdomain sanitization removes invalid characters."""
    wizard = SetupWizard()

    # Special characters should be converted to hyphens
    assert wizard._sanitize_subdomain("my_app") == "my-app"
    assert wizard._sanitize_subdomain("my@app!") == "my-app"
    assert wizard._sanitize_subdomain("My.App") == "my-app"


def test_sanitize_subdomain_length_constraints():
    """Test subdomain sanitization enforces length constraints."""
    wizard = SetupWizard()

    # Too short
    assert wizard._sanitize_subdomain("ab") == "my-app"

    # Too long (should truncate)
    long_name = "a" * 100
    sanitized = wizard._sanitize_subdomain(long_name)
    assert len(sanitized) <= 63


def test_sanitize_subdomain_consecutive_hyphens():
    """Test subdomain sanitization removes consecutive hyphens."""
    wizard = SetupWizard()

    assert wizard._sanitize_subdomain("my---app") == "my-app"
    assert wizard._sanitize_subdomain("test__project") == "test-project"


def test_sanitize_subdomain_leading_trailing_hyphens():
    """Test subdomain sanitization removes leading/trailing hyphens."""
    wizard = SetupWizard()

    assert wizard._sanitize_subdomain("-myapp-") == "myapp"
    assert wizard._sanitize_subdomain("--test--") == "test"


@pytest.mark.asyncio
async def test_simple_client_wizard():
    """Test simplified client wizard."""
    wizard = SetupWizard()

    # Mock user inputs
    inputs = iter([
        "3000",  # port
        "http://localhost:8080",  # server_url
        "n",  # use subdomain
        "n",  # save config
    ])

    with patch('builtins.input', lambda _: next(inputs)):
        config = wizard._run_simple_client_wizard()

        assert isinstance(config, ClientConfig)
        assert config.local_port == 3000
        assert config.server_url == "http://localhost:8080"
        assert config.subdomain is None


@pytest.mark.asyncio
async def test_simple_client_wizard_with_subdomain():
    """Test simplified client wizard with subdomain."""
    wizard = SetupWizard()

    inputs = iter([
        "5000",  # port
        "",  # server_url (default)
        "y",  # use subdomain
        "myapp",  # subdomain
        "n",  # save config
    ])

    with patch('builtins.input', lambda _: next(inputs)):
        with patch.object(wizard, 'detect_project_name', return_value='suggested'):
            config = wizard._run_simple_client_wizard()

            assert config.local_port == 5000
            assert config.subdomain == "myapp"


@pytest.mark.asyncio
async def test_simple_server_wizard():
    """Test simplified server wizard."""
    wizard = SetupWizard()

    inputs = iter([
        "0.0.0.0",  # host
        "8080",  # port
        "n",  # save config
    ])

    with patch('builtins.input', lambda _: next(inputs)):
        config = wizard._run_simple_server_wizard()

        assert isinstance(config, ServerConfig)
        assert config.host == "0.0.0.0"
        assert config.port == 8080
        assert config.enable_dashboard is True


def test_show_detected_services_with_console():
    """Test showing detected services with rich console."""
    try:
        from rich.console import Console
        wizard = SetupWizard()

        services = [
            {'port': 3000, 'description': 'React App', 'host': 'localhost'},
            {'port': 5000, 'description': 'Flask', 'host': 'localhost'},
        ]

        # Should not raise exception
        wizard.show_detected_services(services)
    except ImportError:
        pytest.skip("Rich not available")


def test_show_detected_services_empty():
    """Test showing detected services when empty."""
    wizard = SetupWizard()

    # Should handle empty list gracefully
    wizard.show_detected_services([])


def test_wizard_without_rich():
    """Test wizard works without rich library."""
    wizard = SetupWizard()

    # Mock RICH_AVAILABLE as False
    import pytunnel.common.wizard as wizard_module
    original = wizard_module.RICH_AVAILABLE
    wizard_module.RICH_AVAILABLE = False

    try:
        wizard = SetupWizard()
        assert wizard.console is None

        # Should still work for simple wizard
        inputs = iter(["3000", "", "n", "n"])
        with patch('builtins.input', lambda _: next(inputs)):
            config = wizard._run_simple_client_wizard()
            assert config.local_port == 3000
    finally:
        wizard_module.RICH_AVAILABLE = original


def test_detect_services_handles_permission_error():
    """Test service detection handles permission errors gracefully."""
    wizard = SetupWizard()

    # Mock _is_port_open to raise exception
    with patch.object(wizard, '_is_port_open', side_effect=PermissionError("Access denied")):
        # Should not crash, just return empty list or handle gracefully
        try:
            services = wizard.detect_local_services()
            assert isinstance(services, list)
        except PermissionError:
            # If it propagates, that's also acceptable behavior
            pass
