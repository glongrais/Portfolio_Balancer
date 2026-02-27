"""
Equity API Router
Endpoints for tracking company equity grants and vesting schedules
"""
import logging
from typing import List
from fastapi import APIRouter, HTTPException, Response, status

from datetime import datetime
from fastapi import Query

from api.schemas import (
    EquityGrantCreate,
    EquityGrantUpdate,
    EquityGrantResponse,
    EquitySummaryResponse,
    EquityValueHistoryItem,
    EquityValueHistoryResponse,
    VestingEventCreate,
    VestingEventUpdate,
    VestingEventResponse,
)
from services.database_service import DatabaseService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/summary", response_model=EquitySummaryResponse)
async def get_summary():
    """
    Get aggregated equity summary across all grants.
    """
    try:
        result = DatabaseService.getEquitySummary()
        return EquitySummaryResponse(**result)
    except Exception as e:
        logger.error(f"Error fetching equity summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch equity summary: {str(e)}"
        )


@router.get("/history", response_model=EquityValueHistoryResponse)
async def get_history(
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date (YYYY-MM-DD)"),
):
    """
    Get historical equity vested value over time for charts.
    """
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

        history = DatabaseService.getEquityValueHistory(start_date, end_date)
        data = [EquityValueHistoryItem(date=d, value=round(v, 2)) for d, v in history]
        return EquityValueHistoryResponse(data=data)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching equity history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch equity history: {str(e)}"
        )


@router.get("/grants", response_model=List[EquityGrantResponse])
async def get_grants():
    """
    Get all equity grants with live-computed vested/unvested values.
    """
    try:
        grants = DatabaseService.getEquityGrants()
        return [EquityGrantResponse(**g) for g in grants]
    except Exception as e:
        logger.error(f"Error fetching equity grants: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch equity grants: {str(e)}"
        )


@router.post("/grants", status_code=status.HTTP_201_CREATED, response_model=EquityGrantResponse)
async def create_grant(grant: EquityGrantCreate):
    """
    Create a new equity grant with optional vesting events.
    """
    try:
        vesting_events = [{"date": e.date, "shares": e.shares, "taxed_shares": e.taxed_shares} for e in grant.vesting_events]
        result = DatabaseService.addEquityGrant(
            grant.name, grant.symbol, grant.total_shares, grant.grant_date, grant.grant_price, vesting_events
        )
        return EquityGrantResponse(**result)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating equity grant: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create equity grant: {str(e)}"
        )


@router.get("/grants/{grant_id}", response_model=EquityGrantResponse)
async def get_grant(grant_id: int):
    """
    Get a single equity grant with full detail.
    """
    try:
        result = DatabaseService.getEquityGrant(grant_id)
        return EquityGrantResponse(**result)
    except KeyError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error fetching equity grant: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch equity grant: {str(e)}"
        )


@router.put("/grants/{grant_id}", response_model=EquityGrantResponse)
async def update_grant(grant_id: int, grant: EquityGrantUpdate):
    """
    Update equity grant metadata.
    """
    try:
        result = DatabaseService.updateEquityGrant(grant_id, grant.name)
        return EquityGrantResponse(**result)
    except KeyError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error updating equity grant: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update equity grant: {str(e)}"
        )


@router.delete("/grants/{grant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_grant(grant_id: int):
    """
    Delete an equity grant and its vesting events.
    """
    try:
        DatabaseService.deleteEquityGrant(grant_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except KeyError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error deleting equity grant: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete equity grant: {str(e)}"
        )


@router.post("/grants/{grant_id}/vesting-events", status_code=status.HTTP_201_CREATED, response_model=VestingEventResponse)
async def add_vesting_event(grant_id: int, event: VestingEventCreate):
    """
    Add a vesting event to a grant.
    """
    try:
        result = DatabaseService.addEquityVestingEvent(grant_id, event.date, event.shares, event.taxed_shares)
        return VestingEventResponse(**result)
    except KeyError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error adding vesting event: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add vesting event: {str(e)}"
        )


@router.put("/grants/{grant_id}/vesting-events/{event_id}", response_model=VestingEventResponse)
async def update_vesting_event(grant_id: int, event_id: int, event: VestingEventUpdate):
    """
    Update a vesting event.
    """
    try:
        result = DatabaseService.updateEquityVestingEvent(
            event_id, event.date, event.shares, event.taxed_shares
        )
        return VestingEventResponse(**result)
    except KeyError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error updating vesting event: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update vesting event: {str(e)}"
        )


@router.delete("/grants/{grant_id}/vesting-events/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vesting_event(grant_id: int, event_id: int):
    """
    Delete a vesting event.
    """
    try:
        DatabaseService.deleteEquityVestingEvent(event_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except KeyError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error deleting vesting event: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete vesting event: {str(e)}"
        )
