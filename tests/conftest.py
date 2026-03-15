"""Pytest conftest: add project root to path."""
import os
import sys

# Project root = parent of tests/
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def pytest_configure(config):
    os.chdir(PROJECT_ROOT)
