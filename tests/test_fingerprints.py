from core.fingerprints import fingerprint_error, guess_language, normalize_error


def test_normalize_error_removes_common_noise() -> None:
    raw = "2026-04-26T12:00:00Z /tmp/app/main.py line 42 port 5173 abcdef1234567890"

    normalized = normalize_error(raw)

    assert "2026-04-26" not in normalized
    assert "/tmp/app/main.py" not in normalized
    assert "5173" not in normalized
    assert "abcdef1234567890" not in normalized


def test_python_module_missing_fingerprint() -> None:
    assert (
        fingerprint_error("ModuleNotFoundError: No module named 'numpy'")
        == "python.import.numpy.missing"
    )


def test_python_pytest_fixture_missing_fingerprint() -> None:
    assert (
        fingerprint_error("fixture 'client' not found")
        == "python.pytest.fixture.client.missing"
    )


def test_node_peer_dependency_fingerprint() -> None:
    assert (
        fingerprint_error("npm ERR! ERESOLVE unable to resolve peer dependency react@18")
        == "node.peerdep.react.conflict"
    )


def test_web_cors_fingerprint() -> None:
    assert (
        fingerprint_error("CORS blocked by API: missing Access-Control-Allow-Origin header")
        == "web.cors.api.blocked"
    )


def test_typescript_undefined_property_fingerprint() -> None:
    assert (
        fingerprint_error("TypeError: Cannot read properties of undefined (reading 'id')")
        == "ts.undefined.property"
    )


def test_guess_language() -> None:
    assert guess_language("pytest fixture not found") == "python"
    assert guess_language("tsconfig path error") == "typescript"
    assert guess_language("CORS blocked") == "web"
