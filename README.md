# Error Samurai

Error Samurai is a local-first debugging memory layer for recurring errors.

V1 is a Python CLI that captures incidents, searches similar solved issues, and
stores high-signal fixes for later reuse.

## Development

Use `uv` for dependency management and command execution:

```bash
uv sync
uv run samurai --help
uv run pytest
```

## MVP Commands

```bash
uv run samurai capture "pytest import error"
uv run samurai search
uv run samurai solved
```

## Demo Loop

Load the bundled local demo memories first:

```bash
uv run python -m seed.seed
```

Then try the MVP flow:

```bash
uv run samurai capture "pytest import error ModuleNotFoundError numpy"
uv run samurai search
uv run samurai solved --yes --note "Installed the missing dependency in the project environment."
uv run samurai search "pytest import error numpy"
```

The final search should return a useful saved or seeded memory with likely root
cause, fix steps, tags, confidence, and timestamp.
