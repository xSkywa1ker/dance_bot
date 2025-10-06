from __future__ import annotations

from pathlib import Path
from uuid import uuid4

BASE_MEDIA_DIR = Path(__file__).resolve().parents[1] / "media"


def ensure_media_directory(subdir: Path | str | None = None) -> Path:
    base = BASE_MEDIA_DIR
    if subdir:
        base = base / Path(subdir)
    base.mkdir(parents=True, exist_ok=True)
    return base


def get_media_path(subdir: Path | str | None, original_name: str | None = None) -> Path:
    directory = ensure_media_directory(subdir)
    suffix = ""
    if original_name:
        suffix = Path(original_name).suffix
    filename = f"{uuid4().hex}{suffix}"
    return directory / filename


def remove_media_file(relative_path: str) -> None:
    path = BASE_MEDIA_DIR / Path(relative_path)
    try:
        path.unlink()
    except FileNotFoundError:
        return
    except OSError:
        return


def relative_media_path(path: Path) -> str:
    try:
        return str(path.relative_to(BASE_MEDIA_DIR))
    except ValueError:
        return str(path)
