"""
Stocks API Router
Endpoints for stock management and information
"""
import logging
from fastapi import APIRouter, HTTPException, Response, status, Path, Query
from typing import List, Optional

from api.schemas import (
    StockResponse,
    StockCreate,
    UpdatePricesResponse,
    StockPriceHistoryResponse,
    StockPriceHistoryItem,
)
from services.database_service import DatabaseService

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/", response_model=List[StockResponse])
async def get_all_stocks():
    """
    Get all stocks in the database
    """
    try:
        stocks = []
        for stock in DatabaseService.stocks.values():
            stocks.append(StockResponse(
                stockid=stock.stockid,
                symbol=stock.symbol,
                name=stock.name,
                price=stock.price,
                currency=stock.currency,
                market_cap=stock.market_cap,
                sector=stock.sector,
                industry=stock.industry,
                country=stock.country,
                dividend=stock.dividend,
                dividend_yield=stock.dividend_yield,
                ex_dividend_date=stock.ex_dividend_date
            ))
        return stocks
    except Exception as e:
        logger.error(f"Error fetching stocks: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch stocks: {str(e)}"
        )

@router.get("/{symbol}", response_model=StockResponse)
async def get_stock(symbol: str = Path(..., description="Stock ticker symbol")):
    """
    Get information about a specific stock by symbol
    """
    try:
        symbol = symbol.upper()
        if symbol not in DatabaseService.symbol_map:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Stock with symbol '{symbol}' not found"
            )

        stockid = DatabaseService.symbol_map[symbol]
        stock = DatabaseService.stocks[stockid]

        return StockResponse(
            stockid=stock.stockid,
            symbol=stock.symbol,
            name=stock.name,
            price=stock.price,
            currency=stock.currency,
            market_cap=stock.market_cap,
            sector=stock.sector,
            industry=stock.industry,
            country=stock.country,
            dividend=stock.dividend,
            dividend_yield=stock.dividend_yield,
            logo_url=stock.logo_url,
            quote_type=stock.quote_type,
            ex_dividend_date=stock.ex_dividend_date
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching stock {symbol}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch stock: {str(e)}"
        )

@router.post("/", response_model=StockResponse, status_code=status.HTTP_201_CREATED)
async def add_stock(stock_create: StockCreate):
    """
    Add a new stock to the database
    """
    try:
        symbol = stock_create.symbol.upper()

        # Check if stock already exists
        if symbol in DatabaseService.symbol_map:
            stockid = DatabaseService.symbol_map[symbol]
            stock = DatabaseService.stocks[stockid]
            logger.info(f"Stock {symbol} already exists, returning existing stock")
            return StockResponse(
                stockid=stock.stockid,
                symbol=stock.symbol,
                name=stock.name,
                price=stock.price,
                currency=stock.currency,
                market_cap=stock.market_cap,
                sector=stock.sector,
                industry=stock.industry,
                country=stock.country,
                dividend=stock.dividend,
                dividend_yield=stock.dividend_yield
            )

        # Add new stock
        stockid = DatabaseService.addStock(symbol)
        stock = DatabaseService.stocks[stockid]

        return StockResponse(
            stockid=stock.stockid,
            symbol=stock.symbol,
            name=stock.name,
            price=stock.price,
            currency=stock.currency,
            market_cap=stock.market_cap,
            sector=stock.sector,
            industry=stock.industry,
            country=stock.country,
            dividend=stock.dividend,
            dividend_yield=stock.dividend_yield,
            logo_url=stock.logo_url,
            quote_type=stock.quote_type,
            ex_dividend_date=stock.ex_dividend_date
        )
    except Exception as e:
        logger.error(f"Error adding stock {stock_create.symbol}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add stock: {str(e)}"
        )

@router.get("/{symbol}/price-history", response_model=StockPriceHistoryResponse)
async def get_stock_price_history(
    symbol: str = Path(..., description="Stock ticker symbol"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)")
):
    """
    Get historical price data for a specific stock
    """
    try:
        symbol = symbol.upper()
        if symbol not in DatabaseService.symbol_map:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Stock with symbol '{symbol}' not found"
            )

        data = DatabaseService.getStockPriceHistory(symbol, start_date, end_date)
        stock = DatabaseService.stocks[DatabaseService.symbol_map[symbol]]

        return StockPriceHistoryResponse(
            symbol=stock.symbol,
            name=stock.name,
            currency=stock.currency,
            data=[StockPriceHistoryItem(**item) for item in data]
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching price history for {symbol}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch price history: {str(e)}"
        )

@router.post("/update-prices", response_model=UpdatePricesResponse)
async def update_all_stock_prices():
    """
    Update current prices for all stocks in the database
    """
    try:
        DatabaseService.updateStocksPrice()
        return UpdatePricesResponse(
            message="Stock prices updated successfully",
            updated_count=len(DatabaseService.stocks)
        )
    except Exception as e:
        logger.error(f"Error updating stock prices: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update stock prices: {str(e)}"
        )
