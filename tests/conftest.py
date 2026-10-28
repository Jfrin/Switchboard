"""Make the tests independent of whatever is in .env, the shell or CI.

Every Settings field and every ROUTING_TEAM_<NAME>_REPS variable is removed from the
environment, and the .env file is not read, so each test starts from the code's defaults.
A test that needs a setting sets it itself with monkeypatch.setenv (and calls
get_settings.cache_clear()).
"""

import os
import re

import pytest

from app.config import Settings, get_settings
from app.profile import get_profile

SETTING_VARS = {name.upper() for name in Settings.model_fields}
TEAM_VARS = re.compile(r"ROUTING_TEAM_\w+_REPS")


def _scrub() -> None:
    for var in list(os.environ):
        if var in SETTING_VARS or TEAM_VARS.fullmatch(var):
            del os.environ[var]


Settings.model_config["env_file"] = None  # never read a real .env during tests
_scrub()  # before any test module imports code that reads settings


@pytest.fixture(autouse=True)
def _clean_settings(monkeypatch):
    for var in list(os.environ):
        if var in SETTING_VARS or TEAM_VARS.fullmatch(var):
            monkeypatch.delenv(var)
    get_settings.cache_clear()
    get_profile.cache_clear()
    yield
    get_settings.cache_clear()
    get_profile.cache_clear()
