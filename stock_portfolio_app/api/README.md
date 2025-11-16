# Portfolio Balancer API

A FastAPI-based REST API for managing investment portfolios, tracking stocks, and providing portfolio balancing recommendations.

## Quick Start

### 1. Install Dependencies

From the project root:
```bash
pip install -r requirements.txt
```

### 2. Start the API Server

**Option A: Using the startup script (recommended)**
```bash
./run_api.sh
```

**Option B: Using uvicorn directly**
```bash
cd stock_portfolio_app
uvicorn api.app:app --reload --host 0.0.0.0 --port 8000
```

### 3. Access the API

- **API Base URL**: http://localhost:8000
- **Interactive Docs (Swagger)**: http://localhost:8000/docs
- **Alternative Docs (ReDoc)**: http://localhost:8000/redoc

## API Structure

```
stock_portfolio_app/api/
├── __init__.py           # Package initialization
├── app.py                # Main FastAPI application
├── middleware.py         # Custom middleware and error handlers
├── schemas.py            # Pydantic models for request/response validation
├── client_example.py     # Example Python client
└── routers/              # API route handlers
    ├── __init__.py
    ├── portfolio.py      # Portfolio management endpoints
    ├── stocks.py         # Stock and position management endpoints
    └── transactions.py   # Transaction tracking endpoints
```

## Key Features

- **Portfolio Management**: Calculate value, view positions, get distribution analysis
- **Portfolio Balancing**: Get smart buy recommendations based on target allocations
- **Stock Management**: Add stocks, update prices, manage positions
- **Transaction Tracking**: Record and analyze buy/sell transactions
- **Dividend Analysis**: Track expected dividends by stock and total
- **Real-time Price Updates**: Fetch current prices from Yahoo Finance
- **Automatic CORS**: Configured for frontend integration
- **Request Logging**: All requests are logged with timing information
- **Error Handling**: Comprehensive error responses with detailed messages

## API Endpoints

### Portfolio
- `GET /api/portfolio/value` - Get total portfolio value
- `GET /api/portfolio/positions` - Get all positions
- `POST /api/portfolio/balance` - Get balancing recommendations
- `GET /api/portfolio/distribution` - Get distribution analysis
- `GET /api/portfolio/dividends/total` - Get total yearly dividends
- `GET /api/portfolio/dividends/breakdown` - Get dividend breakdown
- `POST /api/portfolio/positions/update-prices` - Update position prices

### Stocks
- `GET /api/stocks/` - Get all stocks
- `GET /api/stocks/{symbol}` - Get specific stock
- `POST /api/stocks/` - Add new stock
- `POST /api/stocks/update-prices` - Update all stock prices
- `POST /api/stocks/positions` - Add new position
- `PUT /api/stocks/positions/{symbol}` - Update position

### Transactions
- `GET /api/transactions/` - Get transaction history
- `POST /api/transactions/` - Add new transaction
- `GET /api/transactions/summary` - Get transaction summary

## Using the API

### Example: Python Client

Run the example client:
```bash
python stock_portfolio_app/api/client_example.py
```

Or use the `PortfolioClient` class in your own code:
```python
from api.client_example import PortfolioClient

client = PortfolioClient()
portfolio_value = client.get_portfolio_value()
print(f"Portfolio Value: €{portfolio_value['total_value']}")
```

### Example: cURL

```bash
# Get portfolio value
curl http://localhost:8000/api/portfolio/value

# Balance portfolio
curl -X POST http://localhost:8000/api/portfolio/balance \
  -H "Content-Type: application/json" \
  -d '{"amount_to_buy": 1000}'

# Add a stock
curl -X POST http://localhost:8000/api/stocks/ \
  -H "Content-Type: application/json" \
  -d '{"symbol": "AAPL"}'
```

### Example: JavaScript/Fetch

```javascript
// Get portfolio value
fetch('http://localhost:8000/api/portfolio/value')
  .then(response => response.json())
  .then(data => console.log(data));

// Balance portfolio
fetch('http://localhost:8000/api/portfolio/balance', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({amount_to_buy: 1000})
})
  .then(response => response.json())
  .then(data => console.log(data));
```

## Configuration

### CORS Settings

By default, the API accepts requests from any origin. For production, update `api/app.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-frontend-domain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Database Path

The database path is set in `services/database_service.py`:

```python
DB_PATH = '../data/portfolio.db'
```

Update this if your database is located elsewhere.

### Logging Level

Set the logging level when starting the server:

```bash
uvicorn api.app:app --log-level debug
```

Or modify the level in `api/app.py`:

```python
logging.basicConfig(level=logging.DEBUG, ...)
```

## Production Deployment

### Using Gunicorn

For production, use Gunicorn with Uvicorn workers:

```bash
pip install gunicorn
cd stock_portfolio_app
gunicorn api.app:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000
```

### Using Docker

Create a `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
WORKDIR /app/stock_portfolio_app

CMD ["uvicorn", "api.app:app", "--host", "0.0.0.0", "--port", "8000"]
```

Build and run:
```bash
docker build -t portfolio-api .
docker run -p 8000:8000 -v $(pwd)/data:/app/data portfolio-api
```

## Testing

Test the API endpoints:

```bash
# Check health
curl http://localhost:8000/api/health

# Get portfolio value
curl http://localhost:8000/api/portfolio/value

# Run the example client
python stock_portfolio_app/api/client_example.py
```

## Development

### Adding New Endpoints

1. Add Pydantic schemas in `api/schemas.py`
2. Create/update router in `api/routers/`
3. Register router in `api/app.py`

Example:
```python
# In api/routers/my_router.py
from fastapi import APIRouter
router = APIRouter()

@router.get("/my-endpoint")
async def my_endpoint():
    return {"message": "Hello"}

# In api/app.py
from api.routers import my_router
app.include_router(my_router.router, prefix="/api/my", tags=["my"])
```

### Hot Reload

Use `--reload` flag for development to auto-restart on code changes:
```bash
uvicorn api.app:app --reload
```

## Troubleshooting

### Import Errors

If you get import errors, make sure you're running from the correct directory:
```bash
cd stock_portfolio_app
uvicorn api.app:app --reload
```

### Database Not Found

The API looks for the database at `../data/portfolio.db` relative to the `stock_portfolio_app` directory. Make sure your database exists at the correct path.

### Port Already in Use

If port 8000 is already in use, specify a different port:
```bash
uvicorn api.app:app --port 8001
```

## Documentation

See the main [API_DOCUMENTATION.md](../../API_DOCUMENTATION.md) file in the project root for complete API reference with examples.

## License

Part of the Portfolio Balancer project.

