"""
Portfolio API Router
Endpoints for portfolio management, balancing, and analysis
"""
import logging
import math
from fastapi import APIRouter, HTTPException, Response, status, Query, Path
from typing import List

from api.schemas import (
    PortfolioValueResponse,
    BalanceRequest,
    BalanceStrategy,
    BalanceResponse,
    BalanceRecommendation,
    DistributionResponse,
    DistributionItem,
    DividendResponse,
    DividendBreakdownResponse,
    DividendByStockItem,
    DividendSummaryResponse,
    PositionResponse,
    PositionCreate,
    PositionUpdate,
    UpdatePricesResponse,
    PortfolioValueHistoryResponse,
    PortfolioValueHistoryItem,
    DividendCalendarEvent,
    DividendCalendarResponse,
)
from services.portfolio_service import PortfolioService
from services.database_service import DatabaseService
from services.stock_api import StockAPI

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/{portfolio_id}/value", response_model=PortfolioValueResponse)
async def get_portfolio_value(portfolio_id: int = Path(..., description="Portfolio ID")):
    """
    Get the current total value of the portfolio
    """
    try:
        total_value = PortfolioService.calculatePortfolioValue(portfolio_id)
        return PortfolioValueResponse(
            total_value=total_value,
            currency="EUR",
            positions_count=len(DatabaseService.getPositionsForPortfolio(portfolio_id))
        )
    except Exception as e:
        logger.error(f"Error calculating portfolio value: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate portfolio value: {str(e)}"
        )

@router.get("/{portfolio_id}/positions", response_model=List[PositionResponse])
async def get_portfolio_positions(portfolio_id: int = Path(..., description="Portfolio ID")):
    """
    Get all positions in the portfolio
    """
    try:
        positions = []
        for position in DatabaseService.getPositionsForPortfolio(portfolio_id).values():
            # Convert Stock dataclass to dict for Pydantic
            stock_dict = None
            if position.stock:
                logger.debug(f"Position: {position.stock}")
                stock_dict = {
                    "stockid": position.stock.stockid,
                    "symbol": position.stock.symbol,
                    "name": position.stock.name,
                    "price": position.stock.price,
                    "currency": position.stock.currency,
                    "market_cap": position.stock.market_cap,
                    "sector": position.stock.sector,
                    "industry": position.stock.industry,
                    "country": position.stock.country,
                    "dividend": position.stock.dividend,
                    "dividend_yield": position.stock.dividend_yield,
                    "logo_url": position.stock.logo_url,
                    "quote_type": position.stock.quote_type,
                    "ex_dividend_date": position.stock.ex_dividend_date,
                }
            positions.append(PositionResponse(
                stockid=position.stockid,
                quantity=position.quantity,
                average_cost_basis=position.average_cost_basis,
                distribution_target=position.distribution_target,
                distribution_real=position.distribution_real or 0.0,
                stock=stock_dict,
                delta=position.delta(),
                portfolio_id=position.portfolio_id,
            ))
        return positions
    except Exception as e:
        logger.error(f"Error fetching positions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch positions: {str(e)}"
        )

@router.post("/{portfolio_id}/positions", response_model=PositionResponse, status_code=status.HTTP_201_CREATED)
async def add_position(
    position_create: PositionCreate,
    portfolio_id: int = Path(..., description="Portfolio ID"),
):
    """
    Add a new position to the portfolio
    """
    try:
        symbol = position_create.symbol.upper()

        # Check if position already exists in this portfolio
        if symbol in DatabaseService.symbol_map:
            stockid = DatabaseService.symbol_map[symbol]
            portfolio_positions = DatabaseService.getPositionsForPortfolio(portfolio_id)
            if stockid in portfolio_positions:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Position for {symbol} already exists in portfolio {portfolio_id}. Use PUT to update."
                )

        # Add position
        DatabaseService.addPosition(
            symbol=symbol,
            quantity=position_create.quantity,
            distribution_target=position_create.distribution_target,
            portfolio_id=portfolio_id,
        )

        # Retrieve the newly added position
        stockid = DatabaseService.symbol_map[symbol]
        position = DatabaseService.getPositionsForPortfolio(portfolio_id)[stockid]

        stock_dict = None
        if position.stock:
            stock_dict = {
                "stockid": position.stock.stockid,
                "symbol": position.stock.symbol,
                "name": position.stock.name,
                "price": position.stock.price,
                "currency": position.stock.currency,
                "market_cap": position.stock.market_cap,
                "sector": position.stock.sector,
                "industry": position.stock.industry,
                "country": position.stock.country,
                "dividend": position.stock.dividend,
                "dividend_yield": position.stock.dividend_yield,
                "ex_dividend_date": position.stock.ex_dividend_date,
            }

        return PositionResponse(
            stockid=position.stockid,
            quantity=position.quantity,
            distribution_target=position.distribution_target,
            distribution_real=position.distribution_real or 0.0,
            stock=stock_dict,
            delta=position.delta(),
            portfolio_id=position.portfolio_id,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding position {position_create.symbol}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add position: {str(e)}"
        )

@router.put("/{portfolio_id}/positions/{symbol}", response_model=PositionResponse)
async def update_position(
    position_update: PositionUpdate,
    portfolio_id: int = Path(..., description="Portfolio ID"),
    symbol: str = Path(..., description="Stock ticker symbol"),
):
    """
    Update an existing position in the portfolio
    """
    try:
        symbol = symbol.upper()

        # Check if position exists
        if symbol not in DatabaseService.symbol_map:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Stock with symbol '{symbol}' not found"
            )

        stockid = DatabaseService.symbol_map[symbol]
        portfolio_positions = DatabaseService.getPositionsForPortfolio(portfolio_id)
        if stockid not in portfolio_positions:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Position for {symbol} not found in portfolio {portfolio_id}"
            )

        # Update position
        DatabaseService.updatePosition(
            symbol=symbol,
            quantity=position_update.quantity,
            distribution_target=position_update.distribution_target,
            portfolio_id=portfolio_id,
        )

        # Retrieve updated position
        position = DatabaseService.getPositionsForPortfolio(portfolio_id)[stockid]

        stock_dict = None
        if position.stock:
            stock_dict = {
                "stockid": position.stock.stockid,
                "symbol": position.stock.symbol,
                "name": position.stock.name,
                "price": position.stock.price,
                "currency": position.stock.currency,
                "market_cap": position.stock.market_cap,
                "sector": position.stock.sector,
                "industry": position.stock.industry,
                "country": position.stock.country,
                "dividend": position.stock.dividend,
                "dividend_yield": position.stock.dividend_yield,
                "ex_dividend_date": position.stock.ex_dividend_date,
            }

        return PositionResponse(
            stockid=position.stockid,
            quantity=position.quantity,
            distribution_target=position.distribution_target,
            distribution_real=position.distribution_real or 0.0,
            stock=stock_dict,
            delta=position.delta(),
            portfolio_id=position.portfolio_id,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating position {symbol}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update position: {str(e)}"
        )

@router.delete("/{portfolio_id}/positions/{symbol}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_position(
    portfolio_id: int = Path(..., description="Portfolio ID"),
    symbol: str = Path(..., description="Stock ticker symbol"),
):
    """
    Delete a position from the portfolio.
    Requires all shares to be sold first (quantity must be 0).
    Stock record and transaction history are preserved.
    """
    try:
        symbol_upper = symbol.upper()
        DatabaseService.removePosition(symbol_upper, portfolio_id=portfolio_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
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
        logger.error(f"Error deleting position {symbol}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete position: {str(e)}"
        )

@router.post("/{portfolio_id}/balance", response_model=BalanceResponse)
async def balance_portfolio(
    balance_request: BalanceRequest,
    portfolio_id: int = Path(..., description="Portfolio ID"),
):
    """
    Get portfolio balancing recommendations based on target distributions
    """
    try:
        amount_to_buy = balance_request.amount_to_buy
        min_amount_to_buy = balance_request.min_amount_to_buy
        strategy = balance_request.strategy

        PortfolioService.updateRealDistribution(portfolio_id)

        portfolio_positions = DatabaseService.getPositionsForPortfolio(portfolio_id)
        recommendations = []
        total_invested = 0.0

        if strategy == BalanceStrategy.PROPORTIONAL:
            # Select positions sorted by delta (most underweight first)
            eligible = [
                p for p in portfolio_positions.values()
                if p.distribution_target and p.distribution_target > 0
            ]
            eligible.sort(key=lambda p: p.delta(), reverse=True)

            # Prune positions where even 1 share exceeds the total budget.
            eligible = [p for p in eligible if p.stock.price <= amount_to_buy]

            # Allocate proportionally among remaining eligible positions.
            target_sum = sum(p.distribution_target for p in eligible)
            remaining = amount_to_buy
            for position in eligible:
                allocation = remaining * (position.distribution_target / target_sum)
                shares_to_buy = math.floor(allocation / position.stock.price)

                if shares_to_buy * position.stock.price < min_amount_to_buy:
                    shares_to_buy = math.ceil(allocation / position.stock.price)

                invest_amount = shares_to_buy * position.stock.price
                if invest_amount > remaining or invest_amount < min_amount_to_buy:
                    target_sum -= position.distribution_target
                    continue

                remaining -= invest_amount
                target_sum -= position.distribution_target
                total_invested += invest_amount

                recommendations.append(BalanceRecommendation(
                    symbol=position.stock.symbol,
                    shares=shares_to_buy,
                    amount=round(invest_amount, 2),
                    stock_price=position.stock.price
                ))

            leftover = amount_to_buy - total_invested
        else:
            # Rebalance: allocate new money to fix current imbalances
            total_value = PortfolioService.calculatePortfolioValue(portfolio_id) + amount_to_buy
            remaining = amount_to_buy

            sorted_positions = dict(sorted(
                portfolio_positions.items(),
                key=lambda item: item[1].delta(),
                reverse=True
            ))

            for position in sorted_positions.values():
                if position.stock.price > remaining:
                    continue

                target = position.distribution_target/100 - round(
                    (position.stock.price * position.quantity) / total_value, 4
                )
                money_to_buy = target * total_value
                shares_to_buy = math.floor(min(remaining, money_to_buy) / position.stock.price)

                if (shares_to_buy * position.stock.price) < min_amount_to_buy:
                    continue

                invest_amount = shares_to_buy * position.stock.price
                remaining -= invest_amount
                total_invested += invest_amount

                recommendations.append(BalanceRecommendation(
                    symbol=position.stock.symbol,
                    shares=shares_to_buy,
                    amount=round(invest_amount, 2),
                    stock_price=position.stock.price
                ))

            leftover = remaining

        return BalanceResponse(
            recommendations=recommendations,
            leftover=math.floor(leftover),
            total_invested=round(total_invested, 2)
        )
    except Exception as e:
        logger.error(f"Error balancing portfolio: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to balance portfolio: {str(e)}"
        )

@router.get("/{portfolio_id}/distribution", response_model=DistributionResponse)
async def get_distribution(portfolio_id: int = Path(..., description="Portfolio ID")):
    """
    Get current portfolio distribution vs target distribution
    """
    try:
        PortfolioService.updateRealDistribution(portfolio_id)
        total_value = PortfolioService.calculatePortfolioValue(portfolio_id)

        distributions = []
        for position in DatabaseService.getPositionsForPortfolio(portfolio_id).values():
            value = position.quantity * position.stock.price
            distributions.append(DistributionItem(
                symbol=position.stock.symbol,
                name=position.stock.name,
                distribution_real=position.distribution_real,
                distribution_target=position.distribution_target,
                delta=position.delta(),
                value=round(value, 2)
            ))

        # Sort by delta (descending) to show positions furthest from target first
        distributions.sort(key=lambda x: x.delta, reverse=True)

        return DistributionResponse(
            distributions=distributions,
            total_value=total_value
        )
    except Exception as e:
        logger.error(f"Error fetching distribution: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch distribution: {str(e)}"
        )

@router.get("/{portfolio_id}/dividends/total", response_model=DividendResponse)
async def get_total_dividends(portfolio_id: int = Path(..., description="Portfolio ID")):
    """
    Get total expected yearly dividends
    """
    try:
        total_dividend = PortfolioService.getDividendTotal(portfolio_id)
        return DividendResponse(
            total_dividend=round(total_dividend, 2),
            currency="EUR"
        )
    except Exception as e:
        logger.error(f"Error calculating dividends: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate dividends: {str(e)}"
        )

@router.get("/{portfolio_id}/dividends/summary", response_model=DividendSummaryResponse)
async def get_dividends_summary(portfolio_id: int = Path(..., description="Portfolio ID")):
    """
    Get dividend summary
    """
    try:
        total_dividend = PortfolioService.getDividendTotal(portfolio_id)
        year_to_date_dividend = PortfolioService.getDividendYearToDate(portfolio_id)
        yearly_forecast_dividend = PortfolioService.getDividendYearlyForecast(portfolio_id)
        next_dividend_info = PortfolioService.getNextDividend(portfolio_id)

        next_dividend_item = None
        if next_dividend_info and next_dividend_info.get('stockid'):
            # Get the position for the next dividend
            position = PortfolioService.getPositionById(next_dividend_info['stockid'], portfolio_id)
            dividend_rate = next_dividend_info.get('dividend_rate', 0.0)

            if position and position.stock:
                next_dividend_item = DividendByStockItem(
                    symbol=position.stock.symbol,
                    name=position.stock.name,
                    quantity=position.quantity,
                    dividend_rate=round(dividend_rate, 2),
                    total_dividend=round(position.quantity * dividend_rate, 2),
                    expected_date=next_dividend_info.get('date'),
                )

        return DividendSummaryResponse(
            total_dividend=round(total_dividend, 2),
            year_to_date_dividend=round(year_to_date_dividend, 2),
            yearly_forecast_dividend=round(yearly_forecast_dividend, 2),
            next_dividend=next_dividend_item,
            currency="EUR"
        )
    except Exception as e:
        logger.error(f"Error calculating dividends: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate dividends: {str(e)}"
        )

@router.get("/{portfolio_id}/dividends/breakdown", response_model=DividendBreakdownResponse)
async def get_dividends_breakdown(portfolio_id: int = Path(..., description="Portfolio ID")):
    """
    Get dividend breakdown by stock
    """
    try:
        dividends = []
        total_dividend = 0.0

        for position in DatabaseService.getPositionsForPortfolio(portfolio_id).values():
            dividend_rate = StockAPI.get_current_year_dividends(
                [position.stock.symbol]
            )[position.stock.symbol]
            stock_dividend = dividend_rate * position.quantity
            total_dividend += stock_dividend

            dividends.append(DividendByStockItem(
                symbol=position.stock.symbol,
                name=position.stock.name,
                quantity=position.quantity,
                dividend_rate=round(dividend_rate, 2),
                total_dividend=round(stock_dividend, 2)
            ))

        # Sort by total dividend (descending)
        dividends.sort(key=lambda x: x.total_dividend, reverse=True)

        return DividendBreakdownResponse(
            dividends=dividends,
            total_yearly_dividend=round(total_dividend, 2),
            currency="EUR"
        )
    except Exception as e:
        logger.error(f"Error calculating dividend breakdown: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate dividend breakdown: {str(e)}"
        )

@router.get("/{portfolio_id}/dividends/calendar", response_model=DividendCalendarResponse)
async def get_dividend_calendar(
    portfolio_id: int = Path(..., description="Portfolio ID"),
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date (YYYY-MM-DD)")
):
    """
    Get dividend calendar with historical and projected dividend events for a date range
    """
    try:
        from datetime import datetime
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

        events = DatabaseService.getDividendCalendar(start_date, end_date, portfolio_id=portfolio_id)

        total_historical = sum(e["total_amount"] for e in events if e["type"] == "historical")
        total_projected = sum(e["total_amount"] for e in events if e["type"] == "projected")

        return DividendCalendarResponse(
            events=[DividendCalendarEvent(**e) for e in events],
            start_date=start_date,
            end_date=end_date,
            total_historical=round(total_historical, 2),
            total_projected=round(total_projected, 2),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching dividend calendar: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch dividend calendar: {str(e)}"
        )

@router.post("/positions/update-prices", response_model=UpdatePricesResponse)
async def update_portfolio_prices():
    """
    Update current prices for all positions in the portfolio (all portfolios)
    """
    try:
        DatabaseService.updatePortfolioPositionsPrice()
        total_positions = sum(len(pp) for pp in DatabaseService.positions.values())
        return UpdatePricesResponse(
            message="Position prices updated successfully",
            updated_count=total_positions
        )
    except Exception as e:
        logger.error(f"Error updating position prices: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update position prices: {str(e)}"
        )

@router.get("/{portfolio_id}/value/history", response_model=PortfolioValueHistoryResponse)
async def get_portfolio_value_history(portfolio_id: int = Path(..., description="Portfolio ID")):
    """
    Get portfolio value history
    """
    try:
        portfolio_value_history = PortfolioService.getPortfolioValueHistory(portfolio_id)
        portfolio_value_history_items = []
        for item in portfolio_value_history:
            if item[1] is not None:
                portfolio_value_history_items.append(PortfolioValueHistoryItem(
                    date=item[0],
                    value=item[1]
                ))
        return PortfolioValueHistoryResponse(
            portfolio_value_history=portfolio_value_history_items
        )
    except Exception as e:
        logger.error(f"Error getting portfolio value history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get portfolio value history: {str(e)}"
        )
