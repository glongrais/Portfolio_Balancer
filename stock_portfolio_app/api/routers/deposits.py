"""
Deposits API Router
Endpoints for tracking cash deposits into the portfolio
"""
import logging
from typing import List
from fastapi import APIRouter, HTTPException, status, Query, Path

from api.schemas import DepositCreate, DepositResponse, DepositsTotalResponse
from services.database_service import DatabaseService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/{portfolio_id}/deposits/", response_model=List[DepositResponse])
async def get_deposits(
    portfolio_id: int = Path(..., description="Portfolio ID"),
    limit: int = Query(100, description="Maximum number of deposits to return", ge=1, le=1000)
):
    """
    Get deposit history
    """
    try:
        return DatabaseService.getDeposits(limit, portfolio_id=portfolio_id)
    except Exception as e:
        logger.error(f"Error fetching deposits: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch deposits: {str(e)}"
        )


@router.get("/{portfolio_id}/deposits/total", response_model=DepositsTotalResponse)
async def get_total_deposits(portfolio_id: int = Path(..., description="Portfolio ID")):
    """
    Get total amount deposited
    """
    try:
        total = DatabaseService.getTotalDeposits(portfolio_id=portfolio_id)
        return DepositsTotalResponse(
            total_deposits=total,
            currency="EUR"
        )
    except Exception as e:
        logger.error(f"Error fetching total deposits: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch total deposits: {str(e)}"
        )


@router.post("/{portfolio_id}/deposits/", status_code=status.HTTP_201_CREATED, response_model=DepositResponse)
async def add_deposit(
    deposit: DepositCreate,
    portfolio_id: int = Path(..., description="Portfolio ID"),
):
    """
    Add a new deposit
    """
    try:
        datestamp = deposit.datestamp.strftime("%Y-%m-%d")
        result = DatabaseService.addDeposit(datestamp, deposit.amount, portfolio_id=portfolio_id)
        return DepositResponse(**result)
    except Exception as e:
        logger.error(f"Error adding deposit: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add deposit: {str(e)}"
        )
