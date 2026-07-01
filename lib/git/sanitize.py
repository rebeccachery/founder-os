import re

_DROP_LINE_PATTERNS = (
    re.compile(r"(?i)(password|api[_-]?key|token|secret|credential)"),
    re.compile(r"(?i)\bTODO\b.*\b(remove|delete|before launch)\b"),
    re.compile(r"(?i)(hardcoded|slack|jira|linear|notion)"),
    re.compile(r"^[\s\-*]*(?:src|internal|config|\.env|docs)/", re.I),
)

_MAX_BODY_LEN = 300


def sanitize_commit_body(body: str | None) -> str | None:
    if not body:
        return None

    kept: list[str] = []
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if any(pattern.search(stripped) for pattern in _DROP_LINE_PATTERNS):
            continue
        kept.append(stripped)

    if not kept:
        return None

    text = " ".join(kept)
    if len(text) > _MAX_BODY_LEN:
        text = text[: _MAX_BODY_LEN - 3].rstrip() + "..."
    return text
