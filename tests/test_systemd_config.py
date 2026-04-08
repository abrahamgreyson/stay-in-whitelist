"""
Tests for systemd service configuration
"""
import pytest
from pathlib import Path


def test_service_template_exists():
    """Verify service template file exists in project root."""
    service_file = Path(__file__).parent.parent / "stay-in-whitelist.service"
    assert service_file.exists(), "stay-in-whitelist.service not found in project root"


def test_service_template_structure():
    """Verify service template contains required sections."""
    service_file = Path(__file__).parent.parent / "stay-in-whitelist.service"
    content = service_file.read_text()

    # Check for required sections
    assert "[Unit]" in content, "Missing [Unit] section"
    assert "[Service]" in content, "Missing [Service] section"
    assert "[Install]" in content, "Missing [Install] section"

    # Check for required directives
    assert "Description=" in content, "Missing Description in [Unit]"
    assert "Type=simple" in content, "Type should be 'simple'"
    assert "WorkingDirectory=" in content, "Missing WorkingDirectory"
    assert "ExecStart=" in content, "Missing ExecStart"


def test_service_paths_consistency():
    """Verify WorkingDirectory and ExecStart paths are consistent."""
    service_file = Path(__file__).parent.parent / "stay-in-whitelist.service"
    content = service_file.read_text()

    # Extract WorkingDirectory
    working_dir = None
    for line in content.split('\n'):
        if line.startswith('WorkingDirectory='):
            working_dir = line.split('=', 1)[1].strip()
            break

    assert working_dir, "WorkingDirectory not found"

    # Verify ExecStart references the same directory
    for line in content.split('\n'):
        if line.startswith('ExecStart='):
            exec_start = line.split('=', 1)[1].strip()
            assert working_dir in exec_start, \
                f"ExecStart path doesn't match WorkingDirectory: {exec_start}"
            assert "main.py" in exec_start, \
                f"ExecStart should reference main.py: {exec_start}"
            break


def test_service_network_dependencies():
    """Verify service waits for network."""
    service_file = Path(__file__).parent.parent / "stay-in-whitelist.service"
    content = service_file.read_text()

    assert "After=network-online.target" in content, \
        "Service should wait for network-online.target"
    assert "Wants=network-online.target" in content, \
        "Service should want network-online.target"


def test_service_restart_configuration():
    """Verify restart behavior is configured."""
    service_file = Path(__file__).parent.parent / "stay-in-whitelist.service"
    content = service_file.read_text()

    assert "Restart=on-failure" in content, \
        "Service should restart on failure"
    assert "RestartSec=" in content, \
        "RestartSec should be configured"


def test_service_logging_configuration():
    """Verify logging paths reference correct log file."""
    service_file = Path(__file__).parent.parent / "stay-in-whitelist.service"
    content = service_file.read_text()

    # Check that logging references stay_in_whitelist.log (not old name)
    stdout_lines = [l for l in content.split('\n') if l.startswith('StandardOutput=')]
    stderr_lines = [l for l in content.split('\n') if l.startswith('StandardError=')]

    assert len(stdout_lines) > 0, "StandardOutput not configured"
    assert len(stderr_lines) > 0, "StandardError not configured"

    # Verify log file name
    for line in stdout_lines + stderr_lines:
        assert "stay_in_whitelist.log" in line, \
            f"Log path should reference stay_in_whitelist.log: {line}"
        assert "update_whitelist.log" not in line, \
            f"Log path should not reference old name (update_whitelist.log): {line}"
