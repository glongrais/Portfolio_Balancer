"""
Crypto API Router
Endpoints for managing cryptocurrency holdings via the existing portfolio infrastructure
"""
import logging
from datetime import datetime
from typing import List
from fastapi import APIRouter, HTTPException, Response, status, Query

from api.schemas import (
    CryptoHoldingResponse,
    CryptoHoldingCreate,
    CryptoTransactionCreate,
    CryptoSummaryResponse,
    CryptoValueHistoryItem,
    CryptoValueHistoryResponse,
    TransactionResponse,
)
from services.database_service import DatabaseService
from services.stock_api import StockAPI

logger = logging.getLogger(__name__)

router = APIRouter()


def _build_holding_response(pos: dict) -> CryptoHoldingResponse:
    """Build a CryptoHoldingResponse from a crypto position dict."""
    qty = pos["quantity"]
    price = pos["current_price"]
    currency = pos["currency"]
    cost_basis = pos["average_cost_basis"]

    fx_rate = 1.0
    if currency != "EUR":
        fx_rate = StockAPI.get_fx_rate(currency, "EUR")

    value = qty * price
    value_eur = round(value * fx_rate, 2)

    gain_loss = None
    gain_loss_pct = None
    if cost_basis is not None and cost_basis > 0:
        gain_loss = round(value - qty * cost_basis, 2)
        gain_loss_pct = round((price - cost_basis) / cost_basis * 100, 2)

    return CryptoHoldingResponse(
        symbol=pos["symbol"],
        name=pos["name"],
        quantity=qty,
        average_cost_basis=cost_basis,
        current_price=price,
        currency=currency,
        value=round(value, 2),
        value_eur=value_eur,
        gain_loss=gain_loss,
        gain_loss_pct=gain_loss_pct,
    )


@router.get("/holdings", response_model=List[CryptoHoldingResponse])
async def get_holdings():
    """Get all crypto holdings with live prices."""
    try:
        positions = DatabaseService.getCryptoPositions()
        return [_build_holding_response(p) for p in positions]
    except Exception as e:
        logger.error(f"Error fetching crypto holdings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch crypto holdings: {str(e)}"
        )


@router.post("/holdings", status_code=status.HTTP_201_CREATED, response_model=CryptoHoldingResponse)
async def add_holding(holding: CryptoHoldingCreate):
    """Add a new crypto holding. Validates that the symbol is a cryptocurrency."""
    try:
        symbol = holding.symbol.upper()
        portfolio_id = DatabaseService.getCryptoPortfolioId()

        # Add stock (fetches from yfinance) and validate it's a cryptocurrency
        stockid = DatabaseService.addStock(symbol)
        stock = DatabaseService.stocks.get(stockid)
        if stock is None or stock.quote_type != "CRYPTOCURRENCY":
            quote_type = stock.quote_type if stock else "unknown"
            raise ValueError(
                f"{symbol} is not a cryptocurrency (quote_type={quote_type}). "
                f"Use crypto tickers like BTC-USD, ETH-USD."
            )

        # Add position to crypto portfolio
        DatabaseService.addPosition(symbol, holding.quantity, portfolio_id=portfolio_id)

        # Update cost basis if provided
        if holding.average_cost_basis is not None:
            DatabaseService.updatePosition(
                symbol, average_cost_basis=holding.average_cost_basis, portfolio_id=portfolio_id,
            )

        # Return the holding
        positions = DatabaseService.getCryptoPositions()
        for p in positions:
            if p["symbol"] == symbol:
                return _build_holding_response(p)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Holding created but could not be retrieved"
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding crypto holding: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add crypto holding: {str(e)}"
        )


@router.put("/holdings/{symbol}", response_model=CryptoHoldingResponse)
async def update_holding(symbol: str, quantity: float = None, average_cost_basis: float = None):
    """Update quantity or cost basis of a crypto holding."""
    try:
        symbol = symbol.upper()
        portfolio_id = DatabaseService.getCryptoPortfolioId()
        DatabaseService.updatePosition(
            symbol, quantity=quantity, average_cost_basis=average_cost_basis,
            portfolio_id=portfolio_id,
        )
        positions = DatabaseService.getCryptoPositions()
        for p in positions:
            if p["symbol"] == symbol:
                return _build_holding_response(p)
        raise KeyError(f"Crypto holding {symbol} not found")
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating crypto holding: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update crypto holding: {str(e)}"
        )


@router.delete("/holdings/{symbol}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_holding(symbol: str):
    """Remove a crypto holding."""
    try:
        symbol = symbol.upper()
        portfolio_id = DatabaseService.getCryptoPortfolioId()
        DatabaseService.removePosition(symbol, portfolio_id=portfolio_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except Exception as e:
        logger.error(f"Error deleting crypto holding: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete crypto holding: {str(e)}"
        )


@router.get("/summary", response_model=CryptoSummaryResponse)
async def get_summary():
    """Get aggregated crypto summary."""
    try:
        summary = DatabaseService.getCryptoSummary()
        return CryptoSummaryResponse(**summary)
    except Exception as e:
        logger.error(f"Error fetching crypto summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch crypto summary: {str(e)}"
        )


@router.get("/transactions", response_model=List[TransactionResponse])
async def get_transactions(symbol: str = None, limit: int = 100):
    """Get crypto transaction history."""
    try:
        portfolio_id = DatabaseService.getCryptoPortfolioId()
        txns = DatabaseService.getTransactions(
            symbol=symbol, limit=limit, portfolio_id=portfolio_id,
        )
        return [TransactionResponse(**t) for t in txns]
    except Exception as e:
        logger.error(f"Error fetching crypto transactions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch crypto transactions: {str(e)}"
        )


@router.post("/transactions", status_code=status.HTTP_201_CREATED)
async def add_transaction(txn: CryptoTransactionCreate):
    """Add a BUY/SELL/STAKING transaction for a crypto holding."""
    try:
        symbol = txn.symbol.upper()
        portfolio_id = DatabaseService.getCryptoPortfolioId()

        # Validate crypto type
        if symbol not in DatabaseService.symbol_map:
            stockid = DatabaseService.addStock(symbol)
        else:
            stockid = DatabaseService.symbol_map[symbol]

        stock = DatabaseService.stocks.get(stockid)
        if stock is None or stock.quote_type != "CRYPTOCURRENCY":
            raise ValueError(f"{symbol} is not a cryptocurrency")

        if txn.type.value not in ("BUY", "SELL", "STAKING"):
            raise ValueError(f"Invalid transaction type for crypto: {txn.type.value}")

        DatabaseService.upsertTransactions(
            date=txn.date, type=txn.type.value, symbol=symbol,
            quantity=txn.quantity, price=txn.price, portfolio_id=portfolio_id,
        )
        return {"message": f"{txn.type.value} transaction recorded for {symbol}"}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error adding crypto transaction: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add crypto transaction: {str(e)}"
        )


@router.get("/history", response_model=CryptoValueHistoryResponse)
async def get_history(
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date (YYYY-MM-DD)"),
):
    """Get crypto value history over time (derived from portfolio value history)."""
    try:
        try:
            datetime.strptime(start_date, '%Y-%m-%d')
            datetime.strptime(end_date, '%Y-%m-%d')
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid date format. Use YYYY-MM-DD."
            )
        if start_date > end_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="start_date must be before or equal to end_date."
            )

        portfolio_id = DatabaseService.getCryptoPortfolioId()
        history = DatabaseService.getPortfolioValueHistory(portfolio_id)

        # Get FX lookup for USD->EUR conversion
        fx_lookup = DatabaseService.getFxRateLookup("USDEUR", start_date, end_date)
        last_fx = 1.0

        data = []
        for row in history:
            date_str = row[0] if isinstance(row[0], str) else row[0].strftime('%Y-%m-%d')
            if start_date <= date_str <= end_date and row[1] is not None:
                if date_str in fx_lookup:
                    last_fx = fx_lookup[date_str]
                value = round(float(row[1]) * last_fx, 2)
                data.append(CryptoValueHistoryItem(date=date_str, value=value))

        return CryptoValueHistoryResponse(data=data)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching crypto history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch crypto history: {str(e)}"
        )
