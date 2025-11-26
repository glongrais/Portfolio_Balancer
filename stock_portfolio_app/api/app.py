"""
FastAPI application for Portfolio Balancer API
"""
import logging
import sys
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.db_utils import initialize_database
from services.database_service import DatabaseService
from api.middleware import (
    log_requests_middleware,
    validation_exception_handler,
    http_exception_handler,
    general_exception_handler
)

logger = logging.getLogger(__name__)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(name)s - %(message)s'
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events
    """
    # Startup: Initialize database and load data
    logger.info("Starting up Portfolio Balancer API...")
    try:
        # Initialize database
        db_path = os.path.join(os.path.dirname(__file__), '../../data/portfolio.db')
        initialize_database(db_path)
        
        # Load stocks and positions into memory
        DatabaseService.getStocks()
        DatabaseService.getPositions()
        DatabaseService.updatePortfolioPositionsPrice()
        DatabaseService.updateHistoricalStocksPortfolio("", "")
        
        logger.info("Portfolio Balancer API started successfully")
    except Exception as e:
        logger.error(f"Failed to initialize application: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down Portfolio Balancer API...")

# Create FastAPI application
app = FastAPI(
    title="Portfolio Balancer API",
    description="API for managing and balancing investment portfolios",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this based on your frontend domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add custom middleware
app.middleware("http")(log_requests_middleware)

# Add exception handlers
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)

# Import and include routers
from api.routers import portfolio, stocks, transactions

app.include_router(portfolio.router, prefix="/api/v1/portfolio", tags=["portfolio"])
app.include_router(stocks.router, prefix="/api/v1/stocks", tags=["stocks"])
app.include_router(transactions.router, prefix="/api/v1/transactions", tags=["transactions"])

@app.get("/")
async def root():
    """
    Root endpoint - API health check
    """
    return {
        "message": "Portfolio Balancer API",
        "status": "online",
        "version": "1.0.0"
    }

@app.get("/api/health")
async def health_check():
    """
    Health check endpoint
    """
    return {
        "status": "healthy",
        "stocks_count": len(DatabaseService.stocks),
        "positions_count": len(DatabaseService.positions)
    }

