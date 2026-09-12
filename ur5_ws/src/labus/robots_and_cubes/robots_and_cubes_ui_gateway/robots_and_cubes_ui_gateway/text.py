"""Loading and strict validation for centrally stored Croatian Kid UI copy."""

from pathlib import Path
from typing import Any

import yaml


REQUIRED_TEXT_PATHS = (
    'title', 'common.loading', 'common.attempts', 'common.coordinate',
    'common.choose_piece', 'common.choose_cell',
    'common.and', 'common.from_origin',
    'colours.red', 'colours.green', 'colours.blue', 'colours.black', 'colours.white',
    'shapes.red', 'shapes.green', 'shapes.blue', 'shapes.black', 'shapes.white',
    'directions.up', 'directions.down', 'directions.right', 'directions.left',
    'easy.instruction', 'beginner.instruction', 'beginner.target_prefix',
    'easy.target_prefix', 'standard.instruction', 'spatial.instruction',
    'spatial.target_prefix', 'challenge.instruction', 'challenge.target_prefix',
    'motion.waiting',
    'success.title', 'success.text',
    'wrong.one_left', 'wrong.try_again', 'failure.title', 'failure.lost',
    'failure.answer_prefix',
    'error.placeholder',
)


def load_child_text(path: str | Path) -> dict[str, Any]:
    """Load UTF-8 Croatian copy and reject incomplete or non-string values."""
    try:
        text = yaml.safe_load(Path(path).read_text(encoding='utf-8'))
    except (OSError, yaml.YAMLError) as error:
        raise ValueError(f'cannot load Croatian child text: {error}') from error
    if not isinstance(text, dict):
        raise ValueError('Croatian child text root must be a mapping')
    for dotted in REQUIRED_TEXT_PATHS:
        value: Any = text
        for part in dotted.split('.'):
            value = value.get(part) if isinstance(value, dict) else None
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f'Croatian child text missing: {dotted}')
    return text
