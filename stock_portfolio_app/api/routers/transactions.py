"""
Transactions API Router
Endpoints for transaction management and history
"""
import logging
from fastapi import APIRouter, HTTPException, status, Query
from typing import List, Optional
import sys
import os
import sqlite3

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from api.schemas import TransactionCreate
from services.database_service import DatabaseService, DB_PATH

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
        query = "SELECT t.transactionid, t.stockid, s.symbol, t.quantity, t.price, t.type, t.datestamp, s.name FROM transactions t JOIN stocks s ON t.stockid = s.stockid"
        params = []
        conditions = []
        
        if symbol:
            conditions.append("s.symbol = ?")
            params.append(symbol.upper())
        
        if transaction_type:
            conditions.append("t.type = ?")
            params.append(transaction_type.lower())
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        query += " ORDER BY t.datestamp DESC LIMIT ?"
        params.append(limit)
        
        with sqlite3.connect(DB_PATH) as connection:
            cursor = connection.execute(query, params)
            rows = cursor.fetchall()
        
        transactions = []
        for row in rows:
            transactions.append({
                "transactionid": row[0],
                "stockid": row[1],
                "symbol": row[2],
                "quantity": row[3],
                "price": row[4],
                "type": row[5],
                "datestamp": row[6],
                "name": row[7]
            })
        
        return transactions
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
            type=transaction.type.lower(),
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
        query = """
            SELECT 
                s.symbol,
                s.name,
                COUNT(*) as transaction_count,
                SUM(CASE WHEN t.type = 'buy' THEN t.quantity ELSE 0 END) as total_bought,
                SUM(CASE WHEN t.type = 'sell' THEN t.quantity ELSE 0 END) as total_sold,
                SUM(CASE WHEN t.type = 'buy' THEN t.quantity * t.price ELSE 0 END) as total_invested,
                SUM(CASE WHEN t.type = 'sell' THEN t.quantity * t.price ELSE 0 END) as total_divested
            FROM transactions t
            JOIN stocks s ON t.stockid = s.stockid
        """
        params = []
        
        if symbol:
            query += " WHERE s.symbol = ?"
            params.append(symbol.upper())
        
        query += " GROUP BY s.symbol, s.name ORDER BY total_invested DESC"
        
        with sqlite3.connect(DB_PATH) as connection:
            cursor = connection.execute(query, params)
            rows = cursor.fetchall()
        
        summary = []
        for row in rows:
            summary.append({
                "symbol": row[0],
                "name": row[1],
                "transaction_count": row[2],
                "total_bought": row[3],
                "total_sold": row[4],
                "total_invested": round(row[5], 2),
                "total_divested": round(row[6], 2),
                "net_shares": row[3] - row[4],
                "net_investment": round(row[5] - row[6], 2)
            })
        
        return summary
    except Exception as e:
        logger.error(f"Error fetching transaction summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch transaction summary: {str(e)}"
        )

