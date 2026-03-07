# Portfolio Balancer

A comprehensive portfolio management application that reads stock portfolios, tracks transactions, analyzes distributions, and provides intelligent buy recommendations.

## Benchmark

Use the safe benchmark runner so heavy tests never mutate your production DB.

### Safe heavy benchmark workflow

- The runner clones `data/portfolio.db` into `data/benchmark/portfolio_benchmark_<timestamp>.db`
- It starts an isolated API process with `PORTFOLIO_DB_PATH` set to the clone
- It runs Locust in headless mode against that isolated API
- It writes CSV/HTML artifacts and appends a summary to `stock_portfolio_app/benchmark/results/results.md`

### Read-heavy profile (no write endpoints)

```bash
.venv/bin/python stock_portfolio_app/benchmark/run_benchmark.py \
  --profile read_heavy \
  --users 80 \
  --spawn-rate 20 \
  --duration 3m
```

### Mixed profile (includes writes, safe on cloned DB only)

```bash
.venv/bin/python stock_portfolio_app/benchmark/run_benchmark.py \
  --profile mixed \
  --users 50 \
  --spawn-rate 10 \
  --duration 2m
```

### Artifacts and trend history

- Run artifacts: `stock_portfolio_app/benchmark/results/run_<timestamp>_<profile>_*.csv`
- HTML report: `stock_portfolio_app/benchmark/results/run_<timestamp>_<profile>.html`
- Historical summary: `stock_portfolio_app/benchmark/results/results.md`

### Optional docker-compose note

If you run the API through Docker Compose for benchmarks, use a DB override and avoid the default `data/portfolio.db`:

```bash
PORTFOLIO_DB_PATH=/app/data/benchmark.db docker compose up -d
```

## Features

- **Portfolio Management**: Track stocks, positions, and transactions
- **Portfolio Balancing**: Get smart buy recommendations based on target allocations
- **Dividend Tracking**: Monitor expected dividends across your portfolio
- **Real-time Pricing**: Fetch current stock prices from Yahoo Finance
- **Transaction History**: Track all buy/sell transactions
- **Distribution Analysis**: Compare actual vs target allocations
- **REST API**: Full-featured API for frontend integration
- **DBT Analytics**: SQL-based analytics and reporting layer

## Project Structure

```
Portfolio_Balancer/
├── stock_portfolio_app/        # Main application
│   ├── api/                    # REST API (FastAPI)
│   │   ├── app.py             # Main API application
│   │   ├── schemas.py         # Pydantic models
│   │   ├── middleware.py      # Error handling & logging
│   │   ├── client_example.py  # Python client example
│   │   └── routers/           # API endpoints
│   │       ├── portfolio.py   # Portfolio management
│   │       ├── stocks.py      # Stock management
│   │       └── transactions.py # Transaction tracking
│   ├── models/                # Data models
│   ├── services/              # Business logic
│   ├── external/              # External APIs (Yahoo Finance)
│   └── utils/                 # Utilities
├── dbt/                       # DBT analytics project
├── data/                      # SQLite database
├── run_api.sh                 # API startup script
├── API_DOCUMENTATION.md       # Complete API docs
└── README.md                  # This file
```

## Technology Stack

- **Backend**: Python 3.11+
- **API Framework**: FastAPI
- **Database**: SQLite
- **Analytics**: DBT (Data Build Tool)
- **Stock Data**: yfinance (Yahoo Finance)
- **Testing**: pytest

## Documentation

- [API Documentation](API_DOCUMENTATION.md) - Complete API reference
- [API README](stock_portfolio_app/api/README.md) - API setup and usage
- [DBT Documentation](dbt/stock_portfolio_dbt/README.md) - Analytics layer

## Development

### Running Tests

```bash
pytest stock_portfolio_app/tests/
```

### Running DBT Models

```bash
cd dbt/stock_portfolio_dbt
dbt run
dbt test
```

## Resources

numbers_parser:  
`brew install python-snappy`  
`CPPFLAGS="-I/opt/homebrew/include -L/opt/homebrew/lib" pip install numbers-parser`

## Status

![test status](https://github.com/glongrais/Portfolio_Balancer/actions/workflows/tests.yaml/badge.svg)

## Quick Start

### 1. Installation

```bash
pip install -r requirements.txt
```

### 2. Run the API Server

```bash
./run_api.sh
```

Or manually:

```bash
cd stock_portfolio_app
uvicorn api.app:app --reload --host 0.0.0.0 --port 8000
```

### 3. Access the API

- **API Documentation**: http://localhost:8000/docs
- **API Base URL**: http://localhost:8000/api

### 4. Try the Example Client

```bash
python stock_portfolio_app/api/client_example.py
```

## API Usage

### Get Portfolio Value

```bash
curl http://localhost:8000/api/portfolio/value
```

### Balance Portfolio

```bash
curl -X POST http://localhost:8000/api/portfolio/balance \
  -H "Content-Type: application/json" \
  -d '{"amount_to_buy": 1000, "min_amount_to_buy": 100}'
```

### Add a Position

```bash
curl -X POST http://localhost:8000/api/stocks/positions \
  -H "Content-Type: application/json" \
  -d '{"symbol": "AAPL", "quantity": 10, "distribution_target": 10.0}'
```

See [API_DOCUMENTATION.md](API_DOCUMENTATION.md) for complete API reference.

## Command Line Usage (Legacy)

Run example:  
`python3 -m portfolio_balancer.balancer -f test.json -a 500 -fs`

JSON Input example:
````JSON
[
    {
        "symbol":"AAPl",
        "quantity":1,
        "distribution_target":10.0 
    },
    {
        "symbol":"MSFT",
        "quantity":1,
        "distribution_target":7.5
    },
    ...
]
````