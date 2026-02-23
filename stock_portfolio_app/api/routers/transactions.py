"""
Transactions API Router
Endpoints for transaction management and history
"""
import logging
from fastapi import APIRouter, HTTPException, status, Query
from typing import Optional

from api.schemas import TransactionCreate
from services.database_service import DatabaseService

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/")
async def get_transactions(
    symbol: Optional[str] = Query(None, description="Filter by stock symbol"),
    transaction_type: Optional[str] = Query(None, description="Filter by transaction type (buy/sell)"),
    limit: int = Query(100, description="Maximum number of transactions to return", ge=1, le=1000)
):
    """
    Get transaction history with optional filtering
    """
    try:
        return DatabaseService.getTransactions(
            symbol=symbol,
            transaction_type=transaction_type,
            limit=limit
        )
    except Exception as e:
        logger.error(f"Error fetching transactions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch transactions: {str(e)}"
        )

@router.post("/", status_code=status.HTTP_201_CREATED)
async def add_transaction(transaction: TransactionCreate):
    """
    Add a new transaction to the portfolio
    """
    try:
        DatabaseService.upsertTransactions(
            date=transaction.date,
            rowid=transaction.rowid,
            type=transaction.type.value,
            symbol=transaction.symbol.upper(),
            quantity=transaction.quantity,
            price=transaction.price
        )

        return {
            "message": "Transaction added successfully",
            "symbol": transaction.symbol.upper(),
            "type": transaction.type,
            "quantity": transaction.quantity,
            "price": transaction.price,
            "date": transaction.date
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error adding transaction: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add transaction: {str(e)}"
        )

@router.get("/summary")
async def get_transaction_summary(
    symbol: Optional[str] = Query(None, description="Filter by stock symbol")
):
    """
    Get transaction summary statistics
    """
    try:
        return DatabaseService.getTransactionSummary(symbol=symbol)
    except Exception as e:
        logger.error(f"Error fetching transaction summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch transaction summary: {str(e)}"
        )
