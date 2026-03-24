# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ChoresPlanner is a CLI tool for managing chores with automatic Google Calendar integration. It's a Python 3.14 project managed with [uv](https://docs.astral.sh/uv/).

**Key Features:**
- Interactive CLI built with Typer and Rich
- SQLite database with SQLAlchemy ORM
- Google Calendar API integration with OAuth2
- Frequency-based scheduling using python-dateutil
- Automatic event creation for the next month

## Commands

**Application:**
- **Run the app:** `uv run main.py [command]`
- **Add a chore:** `uv run main.py add`
- **List chores:** `uv run main.py list`
- **Delete a chore:** `uv run main.py delete <chore_id>`
- **Sync chores:** `uv run main.py sync`

**Testing:**
- **Run all tests:** `uv run pytest`
- **Run specific test file:** `uv run pytest tests/test_scheduler_service.py`
- **Run with coverage:** `uv run pytest --cov=choresplanner`
- **Run specific test class:** `uv run pytest tests/test_models.py::TestChoreModel`
- **View coverage report:** `open htmlcov/index.html` (after running with --cov)

**Development:**
- **Add a dependency:** `uv add <package>`
- **Add dev dependency:** `uv add --dev <package>`
- **Sync dependencies:** `uv sync`

## Architecture

**Project Structure:**
- `choresplanner/cli/` - Typer CLI commands
- `choresplanner/models/` - SQLAlchemy database models (Chore, CalendarEvent)
- `choresplanner/services/` - Business logic (ChoreService, CalendarService, SchedulerService)
- `choresplanner/database/` - Database connection and initialization
- `choresplanner/auth/` - Google OAuth2 authentication
- `choresplanner/utils/` - Utility functions (frequency parsing)

**Database Schema:**
- `chores` table: Stores chore definitions with frequency rules (JSON field for flexibility)
- `calendar_events` table: Links chores to Google Calendar events, tracks event IDs for deletion

**Key Design Patterns:**
- Repository pattern via services layer
- Context manager for database sessions (`get_db()`)
- OAuth2 token management with automatic refresh
- Frequency rules stored as JSON, converted to dateutil.rrule for date generation

## Google Calendar Setup

The app requires Google OAuth2 credentials:
1. Place `credentials.json` in `data/credentials/` (download from Google Cloud Console)
2. On first run, app opens browser for OAuth consent
3. Tokens saved to `data/credentials/token.json` for reuse

**Note:** The `data/` directory is gitignored as it contains sensitive credentials and the database.
