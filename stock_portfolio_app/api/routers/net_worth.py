"""
Net Worth API Router
Endpoints for tracking total wealth across asset categories
"""
import logging
from datetime import datetime
from collections import defaultdict
from fastapi import APIRouter, HTTPException, Response, status, Query

from api.schemas import (
    NetWorthAssetItem,
    NetWorthCurrentResponse,
    NetWorthHistoryEntry,
    NetWorthHistoryResponse,
    NetWorthAssetCreate,
    NetWorthAssetUpdate,
    NetWorthAssetResponse,
)
from services.database_service import DatabaseService
from services.portfolio_service import PortfolioService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/current", response_model=NetWorthCurrentResponse)
async def get_current_net_worth():
    """
    Get current net worth breakdown by asset category.
    PEA value is computed live from the portfolio.
    """
    try:
        pea_value = float(PortfolioService.calculatePortfolioValue())
        stored_assets = DatabaseService.getNetWorthAssets()
        equity_vested_total = DatabaseService.getEquityVestedTotal()

        assets = [NetWorthAssetItem(id="pea", label="PEA", value=pea_value)]
        if equity_vested_total > 0:
            assets.append(NetWorthAssetItem(
                id="equity", label="Equity", value=equity_vested_total
            ))
        for asset in stored_assets:
            assets.append(NetWorthAssetItem(
                id=asset["id"],
                label=asset["label"],
                value=asset["current_value"],
            ))

        total = sum(a.value for a in assets)
        last_updated = datetime.now().strftime('%Y-%m-%d')

        return NetWorthCurrentResponse(
            total=round(total, 2),
            assets=assets,
            last_updated=last_updated,
        )
    except Exception as e:
        logger.error(f"Error fetching current net worth: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch current net worth: {str(e)}"
        )


@router.get("/history", response_model=NetWorthHistoryResponse)
async def get_net_worth_history(
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date (YYYY-MM-DD)"),
):
    """
    Get monthly snapshots of net worth over time.
    PEA history is derived from the portfolio value evolution view.
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

        # Build monthly data: {YYYY-MM-DD: {asset_id: value}}
        monthly_data = defaultdict(dict)

        # PEA history from portfolio value evolution
        pea_dates = []
        pea_history = DatabaseService.getPortfolioValueHistory()
        for row in pea_history:
            date_str = row[0] if isinstance(row[0], str) else row[0].strftime('%Y-%m-%d')
            if start_date <= date_str <= end_date:
                monthly_data[date_str]["pea"] = float(row[1])
                pea_dates.append(date_str)

        # Equity history: compute for every PEA date using forward-filled prices
        equity_history = DatabaseService.getEquityValueHistory(
            start_date, end_date, target_dates=sorted(pea_dates), convert_to_eur=True
        )
        for date_str, value in equity_history:
            if value > 0:
                monthly_data[date_str]["equity"] = round(value, 2)

        # Other asset snapshots
        snapshots = DatabaseService.getNetWorthSnapshots(start_date, end_date)
        for snap in snapshots:
            monthly_data[snap["date"]][snap["asset_id"]] = snap["value"]

        # Build response entries sorted by date
        data = []
        for date in sorted(monthly_data.keys()):
            assets = monthly_data[date]
            total = sum(assets.values())
            data.append(NetWorthHistoryEntry(
                date=date,
                total=round(total, 2),
                assets=assets,
            ))

        return NetWorthHistoryResponse(data=data)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching net worth history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch net worth history: {str(e)}"
        )


@router.post("/assets", status_code=status.HTTP_201_CREATED, response_model=NetWorthAssetResponse)
async def create_asset(asset: NetWorthAssetCreate):
    """
    Create a new net worth asset category.
    """
    try:
        result = DatabaseService.addNetWorthAsset(asset.id, asset.label, asset.current_value)
        return NetWorthAssetResponse(**result)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating asset: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create asset: {str(e)}"
        )


@router.put("/assets/{asset_id}", response_model=NetWorthAssetResponse)
async def update_asset(asset_id: str, asset: NetWorthAssetUpdate):
    """
    Update an existing net worth asset category.
    """
    try:
        result = DatabaseService.updateNetWorthAsset(asset_id, asset.label, asset.current_value)
        return NetWorthAssetResponse(**result)
    except KeyError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error updating asset: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update asset: {str(e)}"
        )


@router.delete("/assets/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_asset(asset_id: str):
    """
    Delete a net worth asset category and its snapshots.
    """
    try:
        DatabaseService.deleteNetWorthAsset(asset_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except KeyError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error deleting asset: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete asset: {str(e)}"
        )
