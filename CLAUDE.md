# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.
Most likely the server will be running with docker compose every time we are working on the
repo. Docker compose is configured to hot reload after every change in the code.

## Commands

```bash
# Run all tests (from repo root — pytest is configured in pyproject.toml)
.venv/bin/python -m pytest

# Run a single test file
.venv/bin/python -m pytest stock_portfolio_app/tests/test_portfolio_api.py

# Run a single test
.venv/bin/python -m pytest stock_portfolio_app/tests/test_portfolio_api.py::test_get_portfolio_value

# Start the API server (from stock_portfolio_app/) only for tests
cd stock_portfolio_app && ../.venv/bin/uvicorn api.app:app --reload --host 0.0.0.0 --port 8001

# Start the API server, prometheus and grafana
docker compose --build -d
```

No linter is configured. The venv lives at `.venv/` in the repo root.

## Architecture

FastAPI app serving a stock portfolio tracker with SQLite storage. All application code is under `stock_portfolio_app/`.

### Layers

- **`api/routers/`** — FastAPI route handlers. Each router file covers a domain (portfolio, stocks, transactions, deposits, net_worth, equity, dev).
- **`api/schemas.py`** — All Pydantic request/response models in one file.
- **`services/database_service.py`** — Primary data access layer (~1400 LOC). All methods are `@classmethod` on `DatabaseService`. This is the largest and most critical file.
- **`services/portfolio_service.py`** — Portfolio calculation logic (balancing, distribution). Also `@classmethod`-only.
- **`services/stock_api.py`** — External API integration (yfinance). Uses `@cached` with TTLCache (60s for prices, 300s for FX rates).
- **`models/`** — Python dataclasses (`Stock`, `Position`, `Transaction`). Each has a `dataclass_factory(cursor, row)` classmethod for SQLite row mapping.
- **`utils/db_utils.py`** — DB initialization, schema validation, `TimedCursor` for slow query logging (>100ms).

### Key Design Patterns

**In-memory caches on DatabaseService:** `stocks` (Dict[int, Stock]), `positions` (Dict[int, Dict[int, Position]]), `symbol_map` (Dict[str, int]) are class-level dicts loaded at startup via the FastAPI lifespan hook. They are updated in-place when mutations happen. Tests must reset these caches in fixtures.

**Multi-portfolio support:** Positions are nested: `positions[portfolio_id][stockid] → Position`. Most methods accept `portfolio_id` (default=1). Three portfolios exist: PEA (EUR), ISK (SEK), CTO (USD). Non-EUR values are converted using FX rates.

**Naming convention:** Python methods use camelCase (e.g., `calculatePortfolioValue`, `getPortfolioValueHistory`), not snake_case.

### API Routes

All routes are prefixed with `/api/v1/`. Portfolio-scoped routes use `/{portfolio_id}/` path parameter:
- `/api/v1/portfolios/{portfolio_id}/value`, `/api/v1/portfolios/{portfolio_id}/balance`, etc.
- `/api/v1/portfolios/{portfolio_id}/transactions/`, `/api/v1/portfolios/{portfolio_id}/deposits/`
- `/api/v1/stocks`, `/api/v1/net-worth`, `/api/v1/equity` — not portfolio-scoped

### Database

SQLite at `data/portfolio.db`. Key tables: `stocks`, `positions`, `transactions`, `deposits`, `portfolios`, `historicalstocks`, `fx_rates_history`, `net_worth_assets`, `net_worth_snapshots`, `equity_grants`, `equity_vesting_events`. Views are managed by dbt (in `dbt/` at repo root).

Transaction types are uppercase strings: `'BUY'`, `'SELL'` and `'DIVIDEND'`.

## Testing Patterns

Tests use `fastapi.testclient.TestClient` with minimal FastAPI apps (one router per test file). External dependencies are mocked via `unittest.mock.patch`. Every test file that touches endpoints has an `autouse` fixture that resets `DatabaseService.symbol_map`, `stocks`, and `positions` to empty dicts.

Test files: `test_portfolio_api.py`, `test_stocks_api.py`, `test_transactions_api.py`, `test_net_worth_api.py`, `test_equity_api.py`, `test_dividend_calendar.py`, `test_database_service.py`, `test_portfolio_service.py`, `test_stock.py`, `test_position.py`.

## Environment Variables

- `PORTFOLIO_DB_PATH` — Override default DB path (default: `data/portfolio.db`)
- `NUMBERS_FILE_PATH` — Apple Numbers spreadsheet for data import
- `SLOW_QUERY_THRESHOLD_MS` — TimedCursor logging threshold (default: 100ms)
