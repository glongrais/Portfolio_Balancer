"""
Pydantic schemas for API request and response models
"""
from pydantic import ConfigDict, BaseModel, Field
from typing import Optional, List
from datetime import datetime

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
class TransactionBase(BaseModel):
    symbol: str = Field(..., description="Stock symbol")
    quantity: int = Field(..., description="Number of shares")
    price: float = Field(..., description="Price per share")
    type: str = Field(..., description="Transaction type (buy/sell)")
    datestamp: datetime = Field(..., description="Transaction date")

class TransactionResponse(TransactionBase):
    transactionid: int = Field(..., description="Transaction ID")
    stockid: int = Field(..., description="Stock ID")
    model_config = ConfigDict(from_attributes=True)

class TransactionCreate(BaseModel):
    symbol: str = Field(..., description="Stock symbol")
    quantity: int = Field(..., description="Number of shares", gt=0)
    price: float = Field(..., description="Price per share", gt=0)
    type: str = Field(..., description="Transaction type (buy/sell)")
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

class DividendBreakdownResponse(BaseModel):
    dividends: List[DividendByStockItem] = Field(..., description="Dividend breakdown by stock")
    total_yearly_dividend: float = Field(..., description="Total expected yearly dividend")
    currency: str = Field(default="EUR", description="Currency")

# Update Stock Prices Request
class UpdatePricesResponse(BaseModel):
    message: str = Field(..., description="Status message")
    updated_count: int = Field(..., description="Number of stocks updated")

