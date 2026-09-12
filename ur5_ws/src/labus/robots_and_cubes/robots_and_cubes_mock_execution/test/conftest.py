from pathlib import Path

import pytest

from robots_and_cubes_config import load_user_settings


@pytest.fixture(scope='session')
def settings():
    root = Path(__file__).parents[2]
    return load_user_settings(root / 'config' / 'user_settings.yaml')
