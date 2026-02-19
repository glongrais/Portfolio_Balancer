"""
Dev API Router
Endpoints for development and data import utilities
"""
import logging
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from utils.file_utils import FileUtils

logger = logging.getLogger(__name__)

router = APIRouter()


class RefreshNumbersResponse(BaseModel):
    message: str = Field(..., description="Status message")
    duration_seconds: float = Field(..., description="Time taken in seconds")


@router.post("/refresh-numbers", response_model=RefreshNumbersResponse)
async def refresh_numbers():
    """
    Refresh positions and transactions from the Apple Numbers file.
    This is a dev-only endpoint used to sync local Numbers data into the database.
    """
    try:
        duration = FileUtils.refresh_from_numbers()
        return RefreshNumbersResponse(
            message="Numbers data refreshed successfully",
            duration_seconds=round(duration, 2),
        )
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Numbers file not found at: {FileUtils.get_numbers_file_path()}",
        )
    except Exception as e:
        logger.error(f"Error refreshing Numbers data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to refresh Numbers data: {str(e)}",
        )
