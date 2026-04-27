from __future__ import annotations

import re

NOISE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b\d{4}-\d{2}-\d{2}[T ][\d:.]+Z?\b"),
    re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.I),
    re.compile(r"\b[0-9a-f]{12,}\b", re.I),
    re.compile(r"(?i)\bline\s+\d+\b"),
    re.compile(r":\d+:\d+"),
    re.compile(r":\d+"),
    re.compile(r"\bport\s+\d+\b", re.I),
    re.compile(r"\b\d{2,5}\b"),
    re.compile(r"[A-Za-z]:\\[^\s:]+"),
    re.compile(r"/(?:[\w.-]+/)+[\w.-]+"),
)


def _token(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", ".", value.lower()).strip(".")
    return cleaned or "unknown"


def normalize_error(error_text: str) -> str:
    normalized = error_text.strip()
    for pattern in NOISE_PATTERNS:
        normalized = pattern.sub(" ", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def guess_language(error_text: str) -> str | None:
    text = error_text.lower()
    if any(marker in text for marker in ("modulenotfounderror", "importerror", "pytest", "pip ")):
        return "python"
    if any(marker in text for marker in ("npm ", "tsconfig", "typescript", "vite", "webpack", "cannot read")):
        return "typescript"
    if any(marker in text for marker in ("cors", "access-control-allow-origin", "env var")):
        return "web"
    return None


def fingerprint_error(error_text: str, language: str | None = None) -> str:
    normalized = normalize_error(error_text)
    text = normalized.lower()
    language = language or guess_language(normalized)

    python_signature = _python_fingerprint(normalized, text)
    if python_signature:
        return python_signature

    js_signature = _js_ts_fingerprint(normalized, text)
    if js_signature:
        return js_signature

    web_signature = _web_fingerprint(normalized, text)
    if web_signature:
        return web_signature

    prefix = language or "unknown"
    return f"{prefix}.error.{_token(normalized)[:60]}"


def _python_fingerprint(normalized: str, text: str) -> str | None:
    module_missing = re.search(
        r"modulenotfounderror:\s+no module named ['\"](?P<module>[\w.-]+)['\"]",
        normalized,
        re.I,
    )
    if module_missing:
        module = module_missing.group("module").split(".")[0]
        return f"python.import.{_token(module)}.missing"

    import_error = re.search(
        r"importerror:.*cannot import name ['\"](?P<name>[\w.-]+)['\"]",
        normalized,
        re.I,
    )
    if import_error:
        return f"python.import.{_token(import_error.group('name'))}.failed"

    fixture_missing = re.search(
        r"fixture ['\"]?(?P<fixture>[\w.-]+)['\"]? not found",
        normalized,
        re.I,
    )
    if fixture_missing:
        return f"python.pytest.fixture.{_token(fixture_missing.group('fixture'))}.missing"

    if "resolutionimpossible" in text or ("pip" in text and "conflict" in text):
        return "python.pip.conflict"

    nonetype = re.search(
        r"'nonetype' object has no attribute ['\"](?P<attr>[\w.-]+)['\"]",
        normalized,
        re.I,
    )
    if nonetype:
        return f"python.nonetype.{_token(nonetype.group('attr'))}.attribute"

    return None


def _js_ts_fingerprint(normalized: str, text: str) -> str | None:
    if re.search(r"cannot read (properties|property) of undefined", normalized, re.I):
        return "ts.undefined.property"

    if "peer dep" in text or "peer dependency" in text or "eresolve" in text:
        if "react" in text:
            return "node.peerdep.react.conflict"
        return "node.peerdep.conflict"

    if "tsconfig" in text:
        return "ts.tsconfig.error"

    if "vite" in text:
        return "web.vite.failure"

    if "webpack" in text:
        return "web.webpack.failure"

    if "missing env" in text or "environment variable" in text:
        return "web.env.missing"

    return None


def _web_fingerprint(normalized: str, text: str) -> str | None:
    if "cors" in text or "access-control-allow-origin" in text:
        return "web.cors.api.blocked"
    return None
