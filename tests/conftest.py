"""Legacy provider tests are opt-in; default tests never download remote music."""

import pytest


def pytest_addoption(parser):
    parser.addoption("--live", action="store_true", default=False, help="Run legacy third-party provider tests")


def pytest_collection_modifyitems(config, items):
    for item in items:
        if item.path.name.startswith("test_addon_") or item.path.name == "test_source.py":
            item.add_marker(pytest.mark.live)
            if not config.getoption("--live"):
                item.add_marker(pytest.mark.skip(reason="Third-party service test; use --live explicitly"))
