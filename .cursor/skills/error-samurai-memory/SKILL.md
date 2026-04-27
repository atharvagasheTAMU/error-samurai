---
name: error-samurai-memory
description: Captures debugging errors with Error Samurai and immediately searches prior memories. Use when an error occurs, a terminal command fails, the user asks to debug a failure, or the user asks to test Error Samurai memory usefulness.
---

# Error Samurai Memory

## Purpose

Use Error Samurai as the first debugging memory step for recurring errors in this project.

When an error occurs or the user asks for help debugging, capture the error and immediately search for similar saved memories before proposing or making a fix.

## Workflow

1. Collect the exact error text.
   - Prefer the terminal output, stack trace, failing test output, or user-provided error.
   - If the error text is unavailable, ask the user for it or rerun the failing command if safe.

2. From the repository root, capture the incident:

```powershell
uv run samurai capture "<error text>"
```

3. Immediately generate the LLM-ready memory context for the active incident:

```powershell
uv run samurai context
```

4. Report the context before continuing:
   - Paste or summarize the `samurai context` output.
   - Summarize the top match, root cause, fix steps, and confidence.
   - Say whether the memory appears useful for the current error.
   - If no useful memory is found, say that clearly and continue normal debugging.

5. After the issue is fixed, ask before saving the learning unless the user already requested automatic saving:

```powershell
uv run samurai solved --yes --note "<short fix summary>"
```

## Search-Only Use

If the user asks to test memory usefulness or search for a known issue without a current active incident, run:

```powershell
uv run samurai context "<query>"
```

Then summarize whether the returned memory would help solve the issue.

## Command Guidelines

- Run commands from the project root.
- Do not skip `samurai context` after `samurai capture`; the point is to visibly inject useful memory into debugging.
- Use `samurai search` only for extra manual exploration after the context block is shown.
- Keep summaries short and actionable.
- If `uv run samurai ...` fails because dependencies are missing, run `uv sync` once, then retry.
- Do not save a memory for trivial noise unless the user asks or the fix is genuinely reusable.
