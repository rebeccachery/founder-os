import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def private_dir() -> Path:
    raw = os.getenv("FOUNDER_OS_PRIVATE_DIR", "private")
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = ROOT / path
    return path


def resolve_config(filename: str) -> Path | None:
    """private/config/{file} → config/{file} → config/{stem}.example.yaml"""
    name = Path(filename).name
    stem = Path(filename).stem

    for candidate in (
        private_dir() / "config" / name,
        ROOT / "config" / name,
        ROOT / "config" / f"{stem}.example.yaml",
    ):
        if candidate.exists():
            return candidate
    return None


def private_agent_queries_path(agent_dir: Path) -> Path | None:
    path = private_dir() / "agents" / agent_dir.name / "queries.yaml"
    return path if path.exists() else None
