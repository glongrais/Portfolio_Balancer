"""
Pydantic schemas for API request and response models
"""
from enum import Enum
from pydantic import ConfigDict, BaseModel, Field
from typing import Optional, List
from datetime import datetime


class BalanceStrategy(str, Enum):
    REBALANCE = "rebalance"
    PROPORTIONAL = "proportional"

# General Schemas
class AmountResponse(BaseModel):
    amount: float = Field(..., description="Amount")
    currency: str = Field(default="EUR", description="Currency")

# Stock Schemas
class StockBase(BaseModel):
    symbol: str = Field(..., description="Stock ticker symbol")
    name: str = Field(default="", description="Company name")
    price: float = Field(default=0.0, description="Current stock price")
    currency: str = Field(default="", description="Currency of the stock")
    market_cap: Optional[float] = Field(default=None, description="Market capitalization")
    sector: str = Field(default="", description="Company sector")
    industry: str = Field(default="", description="Company industry")
    country: str = Field(default="", description="Company country")
    dividend: float = Field(default=0.0, description="Dividend value")
    dividend_yield: float = Field(default=0.0, description="Dividend yield percentage")
    logo_url: str = Field(default="", description="URL to company logo")
    quote_type: str = Field(default="EQUITY", description="Quote type (EQUITY, ETF, etc.)")
    ex_dividend_date: Optional[str] = Field(default=None, description="Ex-dividend date (YYYY-MM-DD)")

class StockResponse(StockBase):
    stockid: int = Field(..., description="Unique stock identifier")
    model_config = ConfigDict(from_attributes=True)

class StockCreate(BaseModel):
    symbol: str = Field(..., description="Stock ticker symbol to add")

# Position Schemas
class PositionBase(BaseModel):
    quantity: int = Field(..., description="Number of shares held")
    distribution_target: Optional[float] = Field(None, description="Target distribution percentage")
    distribution_real: float = Field(default=0.0, description="Current distribution percentage")

class PositionResponse(PositionBase):
    stockid: int = Field(..., description="Stock identifier")
    average_cost_basis: Optional[float] = Field(None, description="Average cost basis")
    stock: Optional[StockResponse] = Field(None, description="Associated stock information")
    delta: float = Field(..., description="Difference between target and real distribution")
    model_config = ConfigDict(from_attributes=True)

class PositionCreate(BaseModel):
    symbol: str = Field(..., description="Stock symbol")
    quantity: int = Field(..., description="Number of shares", gt=0)
    distribution_target: Optional[float] = Field(None, description="Target distribution percentage", ge=0, le=100)

class PositionUpdate(BaseModel):
    quantity: Optional[int] = Field(None, description="New quantity of shares", gt=0)
    distribution_target: Optional[float] = Field(None, description="New target distribution percentage", ge=0, le=100)

# Portfolio Schemas
class PortfolioValueResponse(BaseModel):
    total_value: float = Field(..., description="Total portfolio value")
    currency: str = Field(default="EUR", description="Currency")
    positions_count: int = Field(..., description="Number of positions")

class BalanceRequest(BaseModel):
    amount_to_buy: float = Field(..., description="Amount of money to invest", gt=0)
    min_amount_to_buy: float = Field(default=100, description="Minimum amount per purchase", gt=0)
    strategy: BalanceStrategy = Field(default=BalanceStrategy.PROPORTIONAL, description="Allocation strategy: 'proportional' allocates strictly by target percentages, 'rebalance' fixes current imbalances")

class BalanceRecommendation(BaseModel):
    symbol: str = Field(..., description="Stock symbol")
    shares: int = Field(..., description="Number of shares to buy")
    amount: float = Field(..., description="Total amount to spend")
    stock_price: float = Field(..., description="Current stock price")

class BalanceResponse(BaseModel):
    recommendations: List[BalanceRecommendation] = Field(..., description="List of buy recommendations")
    leftover: float = Field(..., description="Remaining amount after recommendations")
    total_invested: float = Field(..., description="Total amount recommended to invest")

class DistributionItem(BaseModel):
    symbol: str = Field(..., description="Stock symbol")
    name: str = Field(..., description="Company name")
    distribution_real: float = Field(..., description="Current distribution percentage")
    distribution_target: Optional[float] = Field(None, description="Target distribution percentage")
    delta: float = Field(..., description="Difference between target and real")
    value: float = Field(..., description="Current position value")

class DistributionResponse(BaseModel):
    distributions: List[DistributionItem] = Field(..., description="Distribution breakdown")
    total_value: float = Field(..., description="Total portfolio value")

class PortfolioValueHistoryItem(BaseModel):
    date: datetime = Field(..., description="Date")
    value: float = Field(..., description="Portfolio value")

class PortfolioValueHistoryResponse(BaseModel):
    portfolio_value_history: List[PortfolioValueHistoryItem] = Field(..., description="Portfolio value history")

# Transaction Schemas
class TransactionType(str, Enum):
    BUY = "buy"
    SELL = "sell"

class TransactionBase(BaseModel):
    symbol: str = Field(..., description="Stock symbol")
    quantity: int = Field(..., description="Number of shares")
    price: float = Field(..., description="Price per share")
    type: TransactionType = Field(..., description="Transaction type (buy/sell)")
    datestamp: datetime = Field(..., description="Transaction date")

class TransactionResponse(TransactionBase):
    transactionid: int = Field(..., description="Transaction ID")
    stockid: int = Field(..., description="Stock ID")
    model_config = ConfigDict(from_attributes=True)

class TransactionCreate(BaseModel):
    symbol: str = Field(..., description="Stock symbol")
    quantity: int = Field(..., description="Number of shares", gt=0)
    price: float = Field(..., description="Price per share", gt=0)
    type: TransactionType = Field(..., description="Transaction type (buy/sell)")
    date: datetime = Field(..., description="Transaction date")
    rowid: int = Field(..., description="External row identifier")

# Dividend Schemas
class DividendResponse(BaseModel):
    total_dividend: float = Field(..., description="Total earned dividend")
    currency: str = Field(default="EUR", description="Currency")

class DividendByStockItem(BaseModel):
    symbol: str = Field(..., description="Stock symbol")
    name: str = Field(..., description="Company name")
    quantity: int = Field(..., description="Number of shares")
    dividend_rate: float = Field(..., description="Dividend per share")
    total_dividend: float = Field(..., description="Total dividend from this stock")
    expected_date: Optional[str] = Field(None, description="Expected payment date (YYYY-MM-DD)")

class DividendBreakdownResponse(BaseModel):
    dividends: List[DividendByStockItem] = Field(..., description="Dividend breakdown by stock")
    total_yearly_dividend: float = Field(..., description="Total expected yearly dividend")
    currency: str = Field(default="EUR", description="Currency")

class DividendSummaryResponse(BaseModel):
    total_dividend: float = Field(..., description="Total expected yearly dividend")
    year_to_date_dividend: float = Field(..., description="Year to date dividend")
    yearly_forecast_dividend: float = Field(..., description="Yearly forecast dividend")
    next_dividend: Optional[DividendByStockItem] = Field(None, description="Next dividend")
    currency: str = Field(default="EUR", description="Currency")

# Dividend Calendar Schemas
class DividendCalendarEvent(BaseModel):
    date: str = Field(..., description="Dividend date (YYYY-MM-DD)")
    symbol: str = Field(..., description="Stock symbol")
    name: str = Field(..., description="Company name")
    amount_per_share: float = Field(..., description="Dividend amount per share")
    total_amount: float = Field(..., description="Total dividend amount (amount * quantity held)")
    type: str = Field(..., description="Event type: 'historical' or 'projected'")

class DividendCalendarResponse(BaseModel):
    events: List[DividendCalendarEvent] = Field(..., description="Dividend calendar events")
    start_date: str = Field(..., description="Calendar start date")
    end_date: str = Field(..., description="Calendar end date")
    total_historical: float = Field(..., description="Sum of historical dividend amounts in range")
    total_projected: float = Field(..., description="Sum of projected dividend amounts in range")

# Deposit Schemas
class DepositCreate(BaseModel):
    datestamp: datetime = Field(..., description="Deposit date")
    amount: float = Field(..., description="Deposit amount", gt=0)

class DepositResponse(BaseModel):
    depositid: int = Field(..., description="Deposit ID")
    datestamp: str = Field(..., description="Deposit date")
    amount: float = Field(..., description="Deposit amount")
    portfolioid: int = Field(..., description="Portfolio ID")
    currency: str = Field(default="EUR", description="Currency")

class DepositsTotalResponse(BaseModel):
    total_deposits: float = Field(..., description="Total deposits amount")
    currency: str = Field(default="EUR", description="Currency")

# Stock Price History Schemas
class StockPriceHistoryItem(BaseModel):
    datestamp: str = Field(..., description="Date (YYYY-MM-DD)")
    closeprice: float = Field(..., description="Closing price")

class StockPriceHistoryResponse(BaseModel):
    symbol: str = Field(..., description="Stock symbol")
    name: str = Field(default="", description="Company name")
    currency: str = Field(default="", description="Currency")
    data: List[StockPriceHistoryItem] = Field(..., description="Historical price data points")

# Update Stock Prices Request
class UpdatePricesResponse(BaseModel):
    message: str = Field(..., description="Status message")
    updated_count: int = Field(..., description="Number of stocks updated")
