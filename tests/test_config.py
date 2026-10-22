from pathlib import Path
import pytest

def test_root_from_nested_path_with_spaces(tmp_path):
    from course_utils.config import find_root
    root = tmp_path / 'my course'
    marker = root / 'course_utils/__init__.py'
    marker.parent.mkdir(parents=True)
    marker.touch()
    (root / 'requirements.txt').touch()
    nested = root / 'notebooks/deeper'
    nested.mkdir(parents=True)
    assert find_root(nested) == root

def test_environment_overrides_dotenv(tmp_path, monkeypatch):
    from course_utils.config import load_settings
    (tmp_path / '.env').write_text('TYPESAFE_API_KEY=file-key\n')
    monkeypatch.setenv('TYPESAFE_API_KEY', 'environment-key')
    assert load_settings(tmp_path).typesafe_api_key == 'environment-key'

def test_keys_not_in_repr(tmp_path, monkeypatch):
    from course_utils.config import load_settings
    monkeypatch.setenv('TYPESAFE_API_KEY', 'sentinel-secret')
    assert 'sentinel-secret' not in repr(load_settings(tmp_path))

def test_optional_openai_key(tmp_path, monkeypatch):
    from course_utils.config import load_settings, require_key
    monkeypatch.setenv('TYPESAFE_API_KEY', 'course-key')
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    settings = load_settings(tmp_path)
    assert require_key(settings, 'typesafe') == 'course-key'
    with pytest.raises(ValueError, match='OPENAI_API_KEY'):
        require_key(settings, 'openai')

def test_invalid_mode(tmp_path, monkeypatch):
    from course_utils.config import load_settings
    monkeypatch.setenv('COURSE_MODE', 'pretend-live')
    with pytest.raises(ValueError):
        load_settings(tmp_path)
