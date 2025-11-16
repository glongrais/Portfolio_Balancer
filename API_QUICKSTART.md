# Portfolio Balancer API - Quick Start Guide

## 🚀 Get Started in 3 Minutes

### Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 2: Start the API Server

```bash
./run_api.sh
```

That's it! The API is now running at http://localhost:8000

### Step 3: Try It Out

Open your browser and visit:
- **Interactive API Docs**: http://localhost:8000/docs

Or test from the command line:

```bash
# Check if API is running
curl http://localhost:8000/api/health

# Get portfolio value
curl http://localhost:8000/api/portfolio/value

# Get balancing recommendations
curl -X POST http://localhost:8000/api/portfolio/balance \
  -H "Content-Type: application/json" \
  -d '{"amount_to_buy": 1000}'
```

## 📊 What Can I Do With This API?

### Portfolio Management
- ✅ Get total portfolio value
- ✅ View all positions and their distributions
- ✅ Get smart buy recommendations to balance your portfolio
- ✅ Analyze actual vs target allocations
- ✅ Track expected dividends

### Stock Management
- ✅ Add new stocks to track
- ✅ Update stock prices in real-time
- ✅ Add and update positions
- ✅ View detailed stock information

### Transaction Tracking
- ✅ Record buy/sell transactions
- ✅ View transaction history
- ✅ Get transaction summaries and analytics

## 🎯 Common Use Cases

### Use Case 1: Check Portfolio Health

```python
import requests

response = requests.get("http://localhost:8000/api/portfolio/distribution")
data = response.json()

# See which positions are under/over-allocated
for dist in data['distributions']:
    if dist['delta'] > 0:
        print(f"{dist['symbol']} is UNDER-allocated by {dist['delta']:.2f}%")
```

### Use Case 2: Get Buy Recommendations

```bash
curl -X POST http://localhost:8000/api/portfolio/balance \
  -H "Content-Type: application/json" \
  -d '{"amount_to_buy": 5000, "min_amount_to_buy": 200}'
```

Returns exactly which stocks to buy and how many shares!

### Use Case 3: Track Dividends

```python
import requests

response = requests.get("http://localhost:8000/api/portfolio/dividends/breakdown")
data = response.json()

print(f"Expected yearly dividends: €{data['total_yearly_dividend']}")
for stock in data['dividends']:
    print(f"  {stock['symbol']}: €{stock['total_dividend']}")
```

## 📱 Using with Your Frontend

The API is CORS-enabled and ready to use with any frontend framework:

### React Example

```javascript
// Fetch portfolio value
const response = await fetch('http://localhost:8000/api/portfolio/value');
const data = await response.json();
console.log(`Portfolio Value: €${data.total_value}`);

// Balance portfolio
const balanceResponse = await fetch('http://localhost:8000/api/portfolio/balance', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({amount_to_buy: 1000})
});
const recommendations = await balanceResponse.json();
```

### Vue Example

```javascript
// In your component
async getPortfolio() {
  const response = await fetch('http://localhost:8000/api/portfolio/positions');
  this.positions = await response.json();
}

async balancePortfolio(amount) {
  const response = await fetch('http://localhost:8000/api/portfolio/balance', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({amount_to_buy: amount})
  });
  this.recommendations = await response.json();
}
```

## 🐍 Python Client

Use the included Python client:

```python
from api.client_example import PortfolioClient

client = PortfolioClient()

# Get portfolio value
value = client.get_portfolio_value()
print(f"Total: €{value['total_value']}")

# Get positions
positions = client.get_positions()
for pos in positions:
    print(f"{pos['stock']['symbol']}: {pos['quantity']} shares")

# Balance portfolio
recommendations = client.balance_portfolio(1000)
for rec in recommendations['recommendations']:
    print(f"Buy {rec['shares']} shares of {rec['symbol']}")
```

Or run the example:

```bash
python stock_portfolio_app/api/client_example.py
```

## 📖 Documentation

- **Interactive API Docs**: http://localhost:8000/docs (when server is running)
- **Complete API Reference**: [API_DOCUMENTATION.md](API_DOCUMENTATION.md)
- **API Setup Guide**: [stock_portfolio_app/api/README.md](stock_portfolio_app/api/README.md)

## 🔧 Configuration

### Change the Port

```bash
cd stock_portfolio_app
uvicorn api.app:app --port 8080
```

### Enable Debug Logging

```bash
uvicorn api.app:app --log-level debug
```

### Production Deployment

```bash
cd stock_portfolio_app
gunicorn api.app:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000
```

## 🎨 Frontend Ideas

Now that you have a REST API, you can build:

1. **Web Dashboard** - React/Vue/Angular app showing portfolio analytics
2. **Mobile App** - React Native or Flutter app for portfolio management
3. **Slack Bot** - Get portfolio updates in Slack
4. **Discord Bot** - Share portfolio stats with friends
5. **Telegram Bot** - Receive buy recommendations on the go
6. **Chrome Extension** - Quick portfolio overview in your browser
7. **Desktop App** - Electron app for portfolio management

## 🆘 Troubleshooting

**API won't start?**
- Make sure you've installed dependencies: `pip install -r requirements.txt`
- Check if port 8000 is available: `lsof -i :8000`

**Import errors?**
- Make sure you're running from the correct directory: `cd stock_portfolio_app`

**Database errors?**
- Check that `data/portfolio.db` exists
- Initialize it if needed (see main README)

**Can't connect from frontend?**
- CORS is enabled by default
- Check that your API is running: `curl http://localhost:8000/api/health`

## 💡 Tips

1. Use the interactive docs at `/docs` to test endpoints
2. Check the `X-Process-Time` header to monitor performance
3. Use the Python client for quick prototyping
4. All amounts are in EUR by default
5. Stock prices update in real-time from Yahoo Finance
6. The API caches stocks and positions in memory for speed

## 🎉 Next Steps

1. ✅ Try the example client: `python stock_portfolio_app/api/client_example.py`
2. ✅ Explore the interactive docs at http://localhost:8000/docs
3. ✅ Start building your frontend!

Happy coding! 🚀

