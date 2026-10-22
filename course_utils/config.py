"""Local notebook configuration; credentials never appear in repr."""
from dataclasses import dataclass, field
from pathlib import Path
import os
from dotenv import dotenv_values

@dataclass(frozen=True)
class Settings:
    typesafe_api_key: str | None = field(default=None, repr=False)
    openai_api_key: str | None = field(default=None, repr=False)
    openai_model: str = 'gpt-6-luna'
    openai_decisions_model: str = 'gpt-6-luna'
    jev_old: str = 'jev-1.13.0'
    jev_new: str = 'jev-1.14.0'
    mode: str = 'live'


def find_root(start: Path) -> Path:
    start = start.resolve()
    for candidate in (start, *start.parents):
        if (candidate / 'requirements.txt').is_file() and (candidate / 'course_utils/__init__.py').is_file():
            return candidate
    raise FileNotFoundError('Start Jupyter inside the course repository.')


def load_settings(root: Path) -> Settings:
    values = {**dotenv_values(root / '.env'), **os.environ}
    def value(name, default=None):
        raw = values.get(name)
        return raw.strip() if raw and raw.strip() else default
    mode = value('COURSE_MODE', 'live')
    if mode not in {'live', 'recorded'}:
        raise ValueError('COURSE_MODE must be live or recorded.')
    return Settings(typesafe_api_key=value('TYPESAFE_API_KEY'), openai_api_key=value('OPENAI_API_KEY'),
                    openai_model=value('OPENAI_MODEL', 'gpt-6-luna'),
                    openai_decisions_model=value('OPENAI_DECISIONS_MODEL', 'gpt-6-luna'), mode=mode)


def require_key(settings: Settings, provider: str) -> str:
    if provider not in {'typesafe', 'openai'}:
        raise ValueError(f'Unknown provider: {provider}')
    key = getattr(settings, provider + '_api_key')
    if not key:
        variable = 'TYPESAFE_API_KEY' if provider == 'typesafe' else 'OPENAI_API_KEY'
        raise ValueError(f'Set {variable} in the repository .env, then rerun setup.')
    return key
