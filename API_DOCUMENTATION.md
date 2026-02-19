# Portfolio Balancer API Documentation

## Overview

The Portfolio Balancer API provides a RESTful interface for managing investment portfolios, tracking stocks, analyzing distributions, and balancing investments.

## Getting Started

### Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the API server:
```bash
cd stock_portfolio_app
uvicorn api.app:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

### Interactive API Documentation

Once the server is running, you can access:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## API Endpoints

### Root & Health

#### `GET /`
Health check - returns API status

**Response:**
```json
{
  "message": "Portfolio Balancer API",
  "status": "online",
  "version": "1.0.0"
}
```

#### `GET /api/health`
Detailed health check with stats

**Response:**
```json
{
  "status": "healthy",
  "stocks_count": 15,
  "positions_count": 12
}
```

---

## Portfolio Endpoints

### `GET /api/portfolio/value`
Get the current total value of the portfolio

**Response:**
```json
{
  "total_value": 50000.00,
  "currency": "EUR",
  "positions_count": 12
}
```

### `GET /api/portfolio/positions`
Get all positions in the portfolio

**Response:**
```json
[
  {
    "stockid": 1,
    "quantity": 50,
    "distribution_target": 10.0,
    "distribution_real": 9.5,
    "delta": 0.5,
    "stock": {
      "stockid": 1,
      "symbol": "AAPL",
      "name": "Apple Inc.",
      "price": 175.50,
      "currency": "USD",
      "market_cap": 2800000000000,
      "sector": "Technology",
      "industry": "Consumer Electronics",
      "country": "US",
      "dividend": 0.96,
      "dividend_yield": 0.55
    }
  }
]
```

### `POST /api/portfolio/balance`
Get portfolio balancing recommendations

**Request Body:**
```json
{
  "amount_to_buy": 1000.0,
  "min_amount_to_buy": 100.0
}
```

**Response:**
```json
{
  "recommendations": [
    {
      "symbol": "AAPL",
      "shares": 5,
      "amount": 877.50,
      "stock_price": 175.50
    }
  ],
  "leftover": 122.50,
  "total_invested": 877.50
}
```

### `GET /api/portfolio/distribution`
Get current vs target distribution for all positions

**Response:**
```json
{
  "distributions": [
    {
      "symbol": "AAPL",
      "name": "Apple Inc.",
      "distribution_real": 9.5,
      "distribution_target": 10.0,
      "delta": 0.5,
      "value": 8775.00
    }
  ],
  "total_value": 50000.00
}
```

### `GET /api/portfolio/dividends/total`
Get total expected yearly dividends

**Response:**
```json
{
  "total_yearly_dividend": 1250.00,
  "currency": "EUR"
}
```

### `GET /api/portfolio/dividends/breakdown`
Get dividend breakdown by stock

**Response:**
```json
{
  "dividends": [
    {
      "symbol": "AAPL",
      "name": "Apple Inc.",
      "quantity": 50,
      "dividend_rate": 0.96,
      "total_dividend": 48.00
    }
  ],
  "total_yearly_dividend": 1250.00,
  "currency": "EUR"
}
```

### `POST /api/portfolio/positions/update-prices`
Update current prices for all portfolio positions

**Response:**
```json
{
  "message": "Position prices updated successfully",
  "updated_count": 12
}
```

---

## Stock Endpoints

### `GET /api/stocks/`
Get all stocks in the database

**Response:**
```json
[
  {
    "stockid": 1,
    "symbol": "AAPL",
    "name": "Apple Inc.",
    "price": 175.50,
    "currency": "USD",
    "market_cap": 2800000000000,
    "sector": "Technology",
    "industry": "Consumer Electronics",
    "country": "US",
    "dividend": 0.96,
    "dividend_yield": 0.55
  }
]
```

### `GET /api/stocks/{symbol}`
Get information about a specific stock

**Parameters:**
- `symbol` (path): Stock ticker symbol (e.g., "AAPL")

**Response:**
```json
{
  "stockid": 1,
  "symbol": "AAPL",
  "name": "Apple Inc.",
  "price": 175.50,
  "currency": "USD",
  "market_cap": 2800000000000,
  "sector": "Technology",
  "industry": "Consumer Electronics",
  "country": "US",
  "dividend": 0.96,
  "dividend_yield": 0.55
}
```

### `POST /api/stocks/`
Add a new stock to the database

**Request Body:**
```json
{
  "symbol": "AAPL"
}
```

**Response:** Returns the stock object (same as GET /api/stocks/{symbol})

### `POST /api/stocks/update-prices`
Update current prices for all stocks

**Response:**
```json
{
  "message": "Stock prices updated successfully",
  "updated_count": 15
}
```

### `POST /api/stocks/positions`
Add a new position to the portfolio

**Request Body:**
```json
{
  "symbol": "AAPL",
  "quantity": 10,
  "distribution_target": 10.0
}
```

**Response:** Returns the position object

### `PUT /api/stocks/positions/{symbol}`
Update an existing position

**Parameters:**
- `symbol` (path): Stock ticker symbol

**Request Body:**
```json
{
  "quantity": 15,
  "distribution_target": 12.0
}
```

**Response:** Returns the updated position object

---

## Transaction Endpoints

### `GET /api/transactions/`
Get transaction history with optional filtering

**Query Parameters:**
- `symbol` (optional): Filter by stock symbol
- `transaction_type` (optional): Filter by type (buy/sell)
- `limit` (optional, default=100): Maximum number of results

**Response:**
```json
[
  {
    "transactionid": 1,
    "stockid": 1,
    "symbol": "AAPL",
    "quantity": 10,
    "price": 150.00,
    "type": "buy",
    "datestamp": "2024-01-15T10:30:00"
  }
]
```

### `POST /api/transactions/`
Add a new transaction

**Request Body:**
```json
{
  "symbol": "AAPL",
  "quantity": 10,
  "price": 175.50,
  "type": "buy",
  "date": "2024-01-15T10:30:00",
  "rowid": 1
}
```

**Response:**
```json
{
  "message": "Transaction added successfully",
  "symbol": "AAPL",
  "type": "buy",
  "quantity": 10,
  "price": 175.50,
  "date": "2024-01-15T10:30:00"
}
```

### `GET /api/transactions/summary`
Get transaction summary statistics

**Query Parameters:**
- `symbol` (optional): Filter by stock symbol

**Response:**
```json
[
  {
    "symbol": "AAPL",
    "name": "Apple Inc.",
    "transaction_count": 5,
    "total_bought": 50,
    "total_sold": 0,
    "total_invested": 7500.00,
    "total_divested": 0.00,
    "net_shares": 50,
    "net_investment": 7500.00
  }
]
```

---

## Error Responses

All endpoints may return the following error responses:

### 400 Bad Request
```json
{
  "detail": "Error message describing what went wrong",
  "status_code": 400
}
```

### 404 Not Found
```json
{
  "detail": "Stock with symbol 'XYZ' not found",
  "status_code": 404
}
```

### 422 Unprocessable Entity
```json
{
  "detail": [
    {
      "loc": ["body", "quantity"],
      "msg": "ensure this value is greater than 0",
      "type": "value_error"
    }
  ],
  "message": "Request validation failed"
}
```

### 500 Internal Server Error
```json
{
  "detail": "An internal server error occurred",
  "message": "Internal server error"
}
```

---

## Example Usage

### Using cURL

#### Get portfolio value:
```bash
curl http://localhost:8000/api/portfolio/value
```

#### Balance portfolio:
```bash
curl -X POST http://localhost:8000/api/portfolio/balance \
  -H "Content-Type: application/json" \
  -d '{"amount_to_buy": 1000, "min_amount_to_buy": 100}'
```

#### Add a new stock:
```bash
curl -X POST http://localhost:8000/api/stocks/ \
  -H "Content-Type: application/json" \
  -d '{"symbol": "AAPL"}'
```

#### Add a position:
```bash
curl -X POST http://localhost:8000/api/stocks/positions \
  -H "Content-Type: application/json" \
  -d '{"symbol": "AAPL", "quantity": 10, "distribution_target": 10.0}'
```

### Using Python

```python
import requests

BASE_URL = "http://localhost:8000/api"

# Get portfolio value
response = requests.get(f"{BASE_URL}/portfolio/value")
print(response.json())

# Balance portfolio
response = requests.post(
    f"{BASE_URL}/portfolio/balance",
    json={"amount_to_buy": 1000, "min_amount_to_buy": 100}
)
print(response.json())

# Get all positions
response = requests.get(f"{BASE_URL}/portfolio/positions")
positions = response.json()
for position in positions:
    print(f"{position['stock']['symbol']}: {position['quantity']} shares")

# Update prices
response = requests.post(f"{BASE_URL}/portfolio/positions/update-prices")
print(response.json())
```

### Using JavaScript/Fetch

```javascript
const BASE_URL = "http://localhost:8000/api";

// Get portfolio value
fetch(`${BASE_URL}/portfolio/value`)
  .then(response => response.json())
  .then(data => console.log(data));

// Balance portfolio
fetch(`${BASE_URL}/portfolio/balance`, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    amount_to_buy: 1000,
    min_amount_to_buy: 100
  })
})
  .then(response => response.json())
  .then(data => console.log(data));

// Get positions
fetch(`${BASE_URL}/portfolio/positions`)
  .then(response => response.json())
  .then(positions => {
    positions.forEach(position => {
      console.log(`${position.stock.symbol}: ${position.quantity} shares`);
    });
  });
```

---

## CORS Configuration

The API is configured to accept requests from any origin by default. For production use, update the CORS settings in `stock_portfolio_app/api/app.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-frontend-domain.com"],  # Replace with your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## Rate Limiting & Performance

- The API uses in-memory caching for stocks and positions to improve performance
- Stock price updates are performed in parallel using ThreadPoolExecutor
- Response times are logged and included in the `X-Process-Time` header

---

## Development

### Running in Development Mode

```bash
cd stock_portfolio_app
uvicorn api.app:app --reload --log-level info
```

### Running in Production

```bash
cd stock_portfolio_app
uvicorn api.app:app --host 0.0.0.0 --port 8000 --workers 4
```

Or use gunicorn:

```bash
gunicorn api.app:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

---

## Next Steps

1. Add authentication (JWT tokens, API keys)
2. Add rate limiting
3. Set up proper logging to files
4. Deploy to a production server
5. Add monitoring and alerting
6. Implement caching strategies for expensive operations
7. Add WebSocket support for real-time updates

