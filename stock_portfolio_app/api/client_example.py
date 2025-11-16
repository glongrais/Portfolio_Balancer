"""
Example client for Portfolio Balancer API
This demonstrates how to interact with the API using Python
"""
import requests
from typing import Dict, List, Optional

class PortfolioClient:
    """
    Client for interacting with the Portfolio Balancer API
    """
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
    
    # Portfolio Methods
    
    def get_portfolio_value(self) -> Dict:
        """Get current portfolio value"""
        response = requests.get(f"{self.api_url}/portfolio/value")
        response.raise_for_status()
        return response.json()
    
    def get_positions(self) -> List[Dict]:
        """Get all portfolio positions"""
        response = requests.get(f"{self.api_url}/portfolio/positions")
        response.raise_for_status()
        return response.json()
    
    def balance_portfolio(self, amount_to_buy: float, min_amount_to_buy: float = 100.0) -> Dict:
        """Get portfolio balancing recommendations"""
        response = requests.post(
            f"{self.api_url}/portfolio/balance",
            json={
                "amount_to_buy": amount_to_buy,
                "min_amount_to_buy": min_amount_to_buy
            }
        )
        response.raise_for_status()
        return response.json()
    
    def get_distribution(self) -> Dict:
        """Get current vs target distribution"""
        response = requests.get(f"{self.api_url}/portfolio/distribution")
        response.raise_for_status()
        return response.json()
    
    def get_total_dividends(self) -> Dict:
        """Get total expected yearly dividends"""
        response = requests.get(f"{self.api_url}/portfolio/dividends/total")
        response.raise_for_status()
        return response.json()
    
    def get_dividends_breakdown(self) -> Dict:
        """Get dividend breakdown by stock"""
        response = requests.get(f"{self.api_url}/portfolio/dividends/breakdown")
        response.raise_for_status()
        return response.json()
    
    def update_position_prices(self) -> Dict:
        """Update prices for all positions"""
        response = requests.post(f"{self.api_url}/portfolio/positions/update-prices")
        response.raise_for_status()
        return response.json()
    
    # Stock Methods
    
    def get_all_stocks(self) -> List[Dict]:
        """Get all stocks"""
        response = requests.get(f"{self.api_url}/stocks/")
        response.raise_for_status()
        return response.json()
    
    def get_stock(self, symbol: str) -> Dict:
        """Get specific stock by symbol"""
        response = requests.get(f"{self.api_url}/stocks/{symbol}")
        response.raise_for_status()
        return response.json()
    
    def add_stock(self, symbol: str) -> Dict:
        """Add a new stock"""
        response = requests.post(
            f"{self.api_url}/stocks/",
            json={"symbol": symbol}
        )
        response.raise_for_status()
        return response.json()
    
    def update_stock_prices(self) -> Dict:
        """Update all stock prices"""
        response = requests.post(f"{self.api_url}/stocks/update-prices")
        response.raise_for_status()
        return response.json()
    
    def add_position(self, symbol: str, quantity: int, distribution_target: Optional[float] = None) -> Dict:
        """Add a new position"""
        data = {
            "symbol": symbol,
            "quantity": quantity
        }
        if distribution_target is not None:
            data["distribution_target"] = distribution_target
        
        response = requests.post(
            f"{self.api_url}/stocks/positions",
            json=data
        )
        response.raise_for_status()
        return response.json()
    
    def update_position(self, symbol: str, quantity: Optional[int] = None, 
                       distribution_target: Optional[float] = None) -> Dict:
        """Update an existing position"""
        data = {}
        if quantity is not None:
            data["quantity"] = quantity
        if distribution_target is not None:
            data["distribution_target"] = distribution_target
        
        response = requests.put(
            f"{self.api_url}/stocks/positions/{symbol}",
            json=data
        )
        response.raise_for_status()
        return response.json()
    
    # Transaction Methods
    
    def get_transactions(self, symbol: Optional[str] = None, 
                        transaction_type: Optional[str] = None,
                        limit: int = 100) -> List[Dict]:
        """Get transaction history"""
        params = {"limit": limit}
        if symbol:
            params["symbol"] = symbol
        if transaction_type:
            params["transaction_type"] = transaction_type
        
        response = requests.get(
            f"{self.api_url}/transactions/",
            params=params
        )
        response.raise_for_status()
        return response.json()
    
    def add_transaction(self, symbol: str, quantity: int, price: float,
                       transaction_type: str, date: str, rowid: int) -> Dict:
        """Add a new transaction"""
        response = requests.post(
            f"{self.api_url}/transactions/",
            json={
                "symbol": symbol,
                "quantity": quantity,
                "price": price,
                "type": transaction_type,
                "date": date,
                "rowid": rowid
            }
        )
        response.raise_for_status()
        return response.json()
    
    def get_transaction_summary(self, symbol: Optional[str] = None) -> List[Dict]:
        """Get transaction summary statistics"""
        params = {}
        if symbol:
            params["symbol"] = symbol
        
        response = requests.get(
            f"{self.api_url}/transactions/summary",
            params=params
        )
        response.raise_for_status()
        return response.json()


# Example usage
if __name__ == "__main__":
    # Create client
    client = PortfolioClient()
    
    print("=" * 60)
    print("Portfolio Balancer API Client Example")
    print("=" * 60)
    
    try:
        # Get portfolio value
        print("\n1. Portfolio Value:")
        print("-" * 60)
        value = client.get_portfolio_value()
        print(f"Total Value: €{value['total_value']:,.2f}")
        print(f"Number of Positions: {value['positions_count']}")
        
        # Get positions
        print("\n2. Current Positions:")
        print("-" * 60)
        positions = client.get_positions()
        for pos in positions[:5]:  # Show first 5
            stock = pos['stock']
            print(f"{stock['symbol']:8s} - {pos['quantity']:4d} shares @ €{stock['price']:8.2f} = €{pos['quantity'] * stock['price']:10.2f}")
        if len(positions) > 5:
            print(f"... and {len(positions) - 5} more")
        
        # Get distribution
        print("\n3. Portfolio Distribution:")
        print("-" * 60)
        distribution = client.get_distribution()
        print(f"{'Symbol':<8} {'Target %':>10} {'Actual %':>10} {'Delta':>10} {'Value':>12}")
        print("-" * 60)
        for dist in distribution['distributions'][:5]:
            target = dist['distribution_target'] if dist['distribution_target'] else 0
            print(f"{dist['symbol']:<8} {target:>10.2f} {dist['distribution_real']:>10.2f} "
                  f"{dist['delta']:>10.2f} €{dist['value']:>11,.2f}")
        
        # Balance portfolio
        print("\n4. Balance Recommendations (€1000):")
        print("-" * 60)
        balance = client.balance_portfolio(1000.0, 100.0)
        if balance['recommendations']:
            print(f"{'Symbol':<8} {'Shares':>8} {'Amount':>12} {'Price':>12}")
            print("-" * 60)
            for rec in balance['recommendations']:
                print(f"{rec['symbol']:<8} {rec['shares']:>8d} €{rec['amount']:>11.2f} €{rec['stock_price']:>11.2f}")
            print("-" * 60)
            print(f"Total to Invest: €{balance['total_invested']:,.2f}")
            print(f"Leftover: €{balance['leftover']:,.2f}")
        else:
            print("No recommendations available")
        
        # Get dividends
        print("\n5. Expected Yearly Dividends:")
        print("-" * 60)
        dividends = client.get_total_dividends()
        print(f"Total: €{dividends['total_yearly_dividend']:,.2f}")
        
    except requests.exceptions.ConnectionError:
        print("\n❌ Error: Could not connect to API")
        print("Make sure the API server is running:")
        print("  cd stock_portfolio_app && uvicorn api.app:app --reload")
    except requests.exceptions.HTTPError as e:
        print(f"\n❌ API Error: {e}")
    except Exception as e:
        print(f"\n❌ Unexpected Error: {e}")
    
    print("\n" + "=" * 60)

