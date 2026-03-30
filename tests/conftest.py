#!/usr/bin/env python3
"""
Pytest configuration and shared fixtures for openspec-extended tests.
"""

import os
import pytest


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "unit: Unit tests - fast, no external dependencies"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests - test component workflows"
    )
    config.addinivalue_line(
        "markers", "mechanism: Mechanism tests - CLI validation without AI calls"
    )
    config.addinivalue_line(
        "markers", "e2e: E2E full tests - require AI calls (set E2E_CONFIRM=1)"
    )


def pytest_collection_modifyitems(config, items):
    """Skip e2e tests unless E2E_CONFIRM=1."""
    if os.environ.get("E2E_CONFIRM") != "1":
        skip_e2e = pytest.mark.skip(reason="Set E2E_CONFIRM=1 to run e2e tests")
        for item in items:
            if "e2e" in item.keywords and "mechanism" not in item.keywords:
                item.add_marker(skip_e2e)
