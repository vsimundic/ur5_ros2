"""Tests for best-effort application event logging."""

import json

from robots_and_cubes_game.event_log import JsonlEventLogger


def test_jsonl_event_logger_writes_structured_record(tmp_path):
    path = tmp_path / 'events' / 'game.jsonl'
    logger = JsonlEventLogger(path)
    logger.write('round_generated', 3, 'round-1', 'request-1', {'seed': 42})
    record = json.loads(path.read_text(encoding='utf-8'))
    assert record['event_type'] == 'round_generated'
    assert record['state_version'] == 3
    assert record['payload'] == {'seed': 42}


def test_event_logger_ignores_filesystem_failure(tmp_path):
    blocked_parent = tmp_path / 'not_a_directory'
    blocked_parent.write_text('file', encoding='utf-8')
    logger = JsonlEventLogger(blocked_parent / 'game.jsonl')
    logger.write('robot_error', 4, 'round-1', 'request-1', {})
