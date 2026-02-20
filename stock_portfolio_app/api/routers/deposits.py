"""
Deposits API Router
Endpoints for tracking cash deposits into the portfolio
"""
import logging
import sqlite3
from fastapi import APIRouter, HTTPException, status, Query

from api.schemas import DepositCreate, DepositResponse, DepositsTotalResponse
from config import DB_PATH

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/")
async def get_deposits(
    limit: int = Query(100, description="Maximum number of deposits to return", ge=1, le=1000)
):
    """
    Get deposit history
    """
    try:
        query = "SELECT depositid, datestamp, amount, portfolioid, currency FROM deposits ORDER BY datestamp DESC LIMIT ?"
        with sqlite3.connect(DB_PATH) as connection:
            cursor = connection.execute(query, [limit])
            rows = cursor.fetchall()

        deposits = []
        for row in rows:
            deposits.append({
                "depositid": row[0],
                "datestamp": row[1],
                "amount": row[2],
                "portfolioid": row[3],
                "currency": row[4] or "EUR",
            })

        return deposits
    except Exception as e:
        logger.error(f"Error fetching deposits: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch deposits: {str(e)}"
        )


@router.get("/total", response_model=DepositsTotalResponse)
async def get_total_deposits():
    """
    Get total amount deposited
    """
    try:
        query = "SELECT COALESCE(SUM(amount), 0) FROM deposits"
        with sqlite3.connect(DB_PATH) as connection:
            cursor = connection.execute(query)
            total = cursor.fetchone()[0]

        return DepositsTotalResponse(
            total_deposits=round(total, 2),
            currency="EUR"
        )
    except Exception as e:
        logger.error(f"Error fetching total deposits: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch total deposits: {str(e)}"
        )


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=DepositResponse)
async def add_deposit(deposit: DepositCreate):
    """
    Add a new deposit
    """
    try:
        query = "INSERT INTO deposits (datestamp, amount, portfolioid, currency) VALUES (?, ?, 1, 'EUR')"
        datestamp = deposit.datestamp.strftime("%Y-%m-%d")

        with sqlite3.connect(DB_PATH) as connection:
            cursor = connection.execute(query, [datestamp, deposit.amount])
            connection.commit()
            deposit_id = cursor.lastrowid

        return DepositResponse(
            depositid=deposit_id,
            datestamp=datestamp,
            amount=deposit.amount,
            portfolioid=1,
            currency="EUR"
        )
    except Exception as e:
        logger.error(f"Error adding deposit: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add deposit: {str(e)}"
        )
