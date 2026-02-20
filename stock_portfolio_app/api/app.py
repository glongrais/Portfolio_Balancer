"""
FastAPI application for Portfolio Balancer API
"""
import logging
import sqlite3
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from pythonjsonlogger import json as json_logger

from config import DB_PATH
from utils.db_utils import initialize_database, validate_schema, get_db_stats
from services.database_service import DatabaseService
from api.middleware import (
    log_requests_middleware,
    validation_exception_handler,
    http_exception_handler,
    general_exception_handler
)
from api.routers import portfolio, stocks, transactions, deposits, dev
from utils.file_utils import FileUtils

# Configure structured JSON logging
log_handler = logging.StreamHandler()
log_handler.setFormatter(
    json_logger.JsonFormatter(
        fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
        rename_fields={"asctime": "timestamp", "levelname": "level"},
    )
)
logging.basicConfig(level=logging.INFO, handlers=[log_handler])

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events
    """
    # Startup: Initialize database and load data
    logger.info("Starting up Portfolio Balancer API...")
    try:
        # Initialize database
        initialize_database(DB_PATH)

        # Validate that all required tables and views exist
        missing = validate_schema(DB_PATH)
        if missing:
            logger.warning("Missing database objects: %s", ", ".join(missing))

        # Load stocks and positions into memory
        DatabaseService.getStocks()
        DatabaseService.getPositions()
        DatabaseService.updatePortfolioPositionsPrice()
        DatabaseService.updateHistoricalStocksPortfolio("", "")

        # Refresh data from Numbers file
        try:
            FileUtils.refresh_from_numbers()
        except Exception as e:
            logger.warning(f"Numbers refresh failed on startup (non-blocking): {e}")

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

# Prometheus metrics
try:
    from prometheus_fastapi_instrumentator import Instrumentator
    Instrumentator().instrument(app).expose(app, endpoint="/metrics")
except ImportError:
    logger.info("prometheus-fastapi-instrumentator not installed, /metrics endpoint disabled")

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

# Include routers
app.include_router(portfolio.router, prefix="/api/v1/portfolio", tags=["portfolio"])
app.include_router(stocks.router, prefix="/api/v1/stocks", tags=["stocks"])
app.include_router(transactions.router, prefix="/api/v1/transactions", tags=["transactions"])
app.include_router(deposits.router, prefix="/api/v1/deposits", tags=["deposits"])
app.include_router(dev.router, prefix="/api/v1/dev", tags=["dev"])

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
    Health check endpoint that verifies DB connectivity
    """
    db_ok = False
    try:
        with sqlite3.connect(DB_PATH) as connection:
            connection.execute("SELECT 1")
        db_ok = True
    except Exception as e:
        logger.error("Health check DB probe failed: %s", e)

    status = "healthy" if db_ok else "degraded"
    return {
        "status": status,
        "database": "ok" if db_ok else "unreachable",
        "stocks_count": len(DatabaseService.stocks),
        "positions_count": len(DatabaseService.positions)
    }

@app.get("/api/health/db")
async def db_health():
    """
    Detailed database monitoring endpoint
    """
    try:
        stats = get_db_stats(DB_PATH)
        missing = validate_schema(DB_PATH)
        return {
            "status": "ok" if not missing else "warning",
            "missing_objects": missing,
            **stats
        }
    except Exception as e:
        logger.error("DB health check failed: %s", e)
        raise HTTPException(status_code=500, detail=f"DB health check failed: {str(e)}")
