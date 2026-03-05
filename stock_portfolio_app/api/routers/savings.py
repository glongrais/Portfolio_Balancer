"""
Savings Accounts API Router
Endpoints for managing cash savings accounts and their transactions
"""
import logging
from datetime import datetime
from typing import List
from fastapi import APIRouter, HTTPException, Response, status, Query

from api.schemas import (
    SavingsAccountCreate,
    SavingsAccountUpdate,
    SavingsAccountResponse,
    SavingsTransactionCreate,
    SavingsTransactionUpdate,
    SavingsTransactionResponse,
    SavingsSummaryResponse,
    SavingsBalanceHistoryItem,
    SavingsBalanceHistoryResponse,
)
from services.database_service import DatabaseService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/summary", response_model=SavingsSummaryResponse)
async def get_savings_summary():
    """Get aggregated savings summary: total balance in EUR, all accounts."""
    try:
        accounts = DatabaseService.getSavingsAccounts()
        total = DatabaseService.getSavingsAccountsTotal()
        return SavingsSummaryResponse(
            total_balance=total,
            accounts_count=len(accounts),
            accounts=[SavingsAccountResponse(**a) for a in accounts],
        )
    except Exception as e:
        logger.error(f"Error fetching savings summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch savings summary: {str(e)}"
        )


@router.get("/history", response_model=SavingsBalanceHistoryResponse)
async def get_savings_history(
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date (YYYY-MM-DD)"),
):
    """Get historical total savings balance over time."""
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

        history = DatabaseService.getSavingsBalanceHistory(start_date, end_date)
        data = [SavingsBalanceHistoryItem(date=d, balance=round(v, 2)) for d, v in history]
        return SavingsBalanceHistoryResponse(data=data)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching savings history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch savings history: {str(e)}"
        )


@router.get("/accounts", response_model=List[SavingsAccountResponse])
async def get_accounts():
    """List all savings accounts."""
    try:
        accounts = DatabaseService.getSavingsAccounts()
        return [SavingsAccountResponse(**a) for a in accounts]
    except Exception as e:
        logger.error(f"Error fetching savings accounts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch savings accounts: {str(e)}"
        )


@router.post("/accounts", status_code=status.HTTP_201_CREATED, response_model=SavingsAccountResponse)
async def create_account(account: SavingsAccountCreate):
    """Create a new savings account."""
    try:
        result = DatabaseService.addSavingsAccount(
            account.name, account.bank, account.currency,
            account.balance, account.interest_rate,
        )
        return SavingsAccountResponse(**result)
    except Exception as e:
        logger.error(f"Error creating savings account: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create savings account: {str(e)}"
        )


@router.get("/accounts/{account_id}", response_model=SavingsAccountResponse)
async def get_account(account_id: int):
    """Get a single savings account."""
    try:
        result = DatabaseService.getSavingsAccount(account_id)
        return SavingsAccountResponse(**result)
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error fetching savings account: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch savings account: {str(e)}"
        )


@router.put("/accounts/{account_id}", response_model=SavingsAccountResponse)
async def update_account(account_id: int, account: SavingsAccountUpdate):
    """Update savings account metadata (not balance)."""
    try:
        result = DatabaseService.updateSavingsAccount(
            account_id, account.name, account.bank, account.interest_rate,
        )
        return SavingsAccountResponse(**result)
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating savings account: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update savings account: {str(e)}"
        )


@router.delete("/accounts/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(account_id: int):
    """Delete a savings account and its transactions."""
    try:
        DatabaseService.deleteSavingsAccount(account_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error deleting savings account: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete savings account: {str(e)}"
        )


@router.get("/accounts/{account_id}/transactions", response_model=List[SavingsTransactionResponse])
async def get_transactions(account_id: int):
    """List transactions for a savings account."""
    try:
        txns = DatabaseService.getSavingsTransactions(account_id)
        return [SavingsTransactionResponse(**t) for t in txns]
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error fetching savings transactions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch savings transactions: {str(e)}"
        )


@router.post("/accounts/{account_id}/transactions", status_code=status.HTTP_201_CREATED, response_model=SavingsTransactionResponse)
async def add_transaction(account_id: int, txn: SavingsTransactionCreate):
    """Add a transaction to a savings account (updates balance)."""
    try:
        result = DatabaseService.addSavingsTransaction(
            account_id, txn.type.value, txn.amount, txn.datestamp, txn.note or "",
        )
        return SavingsTransactionResponse(**result)
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error adding savings transaction: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add savings transaction: {str(e)}"
        )


@router.put("/accounts/{account_id}/transactions/{txn_id}", response_model=SavingsTransactionResponse)
async def update_transaction(account_id: int, txn_id: int, txn: SavingsTransactionUpdate):
    """Update a savings transaction."""
    try:
        result = DatabaseService.updateSavingsTransaction(
            txn_id, txn.amount, txn.datestamp, txn.note,
        )
        return SavingsTransactionResponse(**result)
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating savings transaction: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update savings transaction: {str(e)}"
        )


@router.delete("/accounts/{account_id}/transactions/{txn_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_transaction(account_id: int, txn_id: int):
    """Delete a savings transaction."""
    try:
        DatabaseService.deleteSavingsTransaction(txn_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error deleting savings transaction: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete savings transaction: {str(e)}"
        )
