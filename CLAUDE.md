# ChoresPlanner - Claude Code Guidelines

## Development Environment

- Always use `uv` for Python package management. Never use `pip install` or `uv pip install` directly.
  - Add runtime dependencies: `uv add <package>`
  - Add dev/test dependencies: `uv add --dev <package>` or `uv add --group test <package>`
  - Run tools: `uv run <tool>`

## Git

- Always confirm the current git branch before making edits. Run `git branch --show-current` first.
- Do not edit files on the wrong branch. Verify you are on the correct branch before any changes.

## Workflow Rules

- When restructuring projects or proposing new file/directory layouts, ask the user for their preferred structure FIRST before making changes. Do not propose multiple alternatives iteratively.
- Before implementing complex logic, verify you understand the approach by asking if needed — do not take a first swing that will likely be rejected.
- When working with existing parsed or computed data, use it directly. Do not re-parse raw strings when structured attributes are already available on the object.

## Testing

- Do not write tests for third-party library behavior or trivial wrappers. Only test application-specific logic.
- Run tests with `uv run pytest`. Run with coverage via `uv run pytest --cov`.

## Code Style

- Use `match`/`case` syntax for pattern matching where appropriate.
- Keep imports clean — no redundant or unused imports.
