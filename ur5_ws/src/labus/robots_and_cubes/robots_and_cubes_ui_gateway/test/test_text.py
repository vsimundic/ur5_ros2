"""Offline validation for centrally stored Croatian Kid UI copy."""

from pathlib import Path

import pytest

from robots_and_cubes_ui_gateway.text import load_child_text, REQUIRED_TEXT_PATHS


TEXT = Path(__file__).parents[2] / 'config' / 'child_text_hr.yaml'


def test_required_kid_copy_is_complete_and_croatian_file_is_utf8():
    text = load_child_text(TEXT)
    assert text['title'] == 'ROBOTSKA POTRAGA ZA BLAGOM'
    assert 'Robot provjerava tvoj odgovor...' == text['motion']['waiting']
    assert len(REQUIRED_TEXT_PATHS) >= 16


def test_missing_translation_is_a_development_error(tmp_path):
    path = tmp_path / 'bad.yaml'
    path.write_text('title: "Naslov"\n', encoding='utf-8')
    with pytest.raises(ValueError, match='missing'):
        load_child_text(path)
