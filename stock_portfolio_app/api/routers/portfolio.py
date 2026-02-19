"""
Portfolio API Router
Endpoints for portfolio management, balancing, and analysis
"""
import logging
import math
from fastapi import APIRouter, HTTPException, status
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
    UpdatePricesResponse,
    PortfolioValueHistoryResponse,
    PortfolioValueHistoryItem
)
from services.portfolio_service import PortfolioService
from services.database_service import DatabaseService
from services.stock_api import StockAPI

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/value", response_model=PortfolioValueResponse)
async def get_portfolio_value():
    """
    Get the current total value of the portfolio
    """
    try:
        total_value = PortfolioService.calculatePortfolioValue()
        return PortfolioValueResponse(
            total_value=total_value,
            currency="EUR",
            positions_count=len(DatabaseService.positions)
        )
    except Exception as e:
        logger.error(f"Error calculating portfolio value: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate portfolio value: {str(e)}"
        )

@router.get("/positions", response_model=List[PositionResponse])
async def get_portfolio_positions():
    """
    Get all positions in the portfolio
    """
    try:
        positions = []
        for position in DatabaseService.positions.values():
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
                    "dividend_yield": position.stock.dividend_yield
                }    
            positions.append(PositionResponse(
                stockid=position.stockid,
                quantity=position.quantity,
                average_cost_basis=position.average_cost_basis,
                distribution_target=position.distribution_target,
                distribution_real=position.distribution_real,
                stock=stock_dict,
                delta=position.delta()
            ))
        return positions
    except Exception as e:
        logger.error(f"Error fetching positions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch positions: {str(e)}"
        )

@router.post("/balance", response_model=BalanceResponse)
async def balance_portfolio(balance_request: BalanceRequest):
    """
    Get portfolio balancing recommendations based on target distributions
    """
    try:
        amount_to_buy = balance_request.amount_to_buy
        min_amount_to_buy = balance_request.min_amount_to_buy
        strategy = balance_request.strategy

        PortfolioService.updateRealDistribution()

        recommendations = []
        total_invested = 0.0

        if strategy == BalanceStrategy.PROPORTIONAL:
            # Select positions sorted by delta (most underweight first)
            eligible = [
                p for p in DatabaseService.positions.values()
                if p.distribution_target and p.distribution_target > 0
            ]
            eligible.sort(key=lambda p: p.delta(), reverse=True)

            # Iteratively prune positions whose proportional allocation
            # falls below min_amount_to_buy, then renormalize until stable
            changed = True
            while changed:
                changed = False
                target_sum = sum(p.distribution_target for p in eligible)
                if target_sum == 0:
                    break
                next_eligible = []
                for p in eligible:
                    allocation = amount_to_buy * (p.distribution_target / target_sum)
                    shares = math.floor(allocation / p.stock.price)
                    if shares * p.stock.price >= min_amount_to_buy:
                        next_eligible.append(p)
                    else:
                        changed = True
                eligible = next_eligible

            # Allocate proportionally among eligible positions
            target_sum = sum(p.distribution_target for p in eligible)
            for position in eligible:
                allocation = amount_to_buy * (position.distribution_target / target_sum)
                shares_to_buy = math.floor(allocation / position.stock.price)
                invest_amount = shares_to_buy * position.stock.price
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
            total_value = PortfolioService.calculatePortfolioValue() + amount_to_buy
            remaining = amount_to_buy

            sorted_positions = dict(sorted(
                DatabaseService.positions.items(),
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

@router.get("/distribution", response_model=DistributionResponse)
async def get_distribution():
    """
    Get current portfolio distribution vs target distribution
    """
    try:
        PortfolioService.updateRealDistribution()
        total_value = PortfolioService.calculatePortfolioValue()
        
        distributions = []
        for position in DatabaseService.positions.values():
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

@router.get("/dividends/total", response_model=DividendResponse)
async def get_total_dividends():
    """
    Get total expected yearly dividends
    """
    try:
        total_dividend = PortfolioService.getDividendTotal()
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

@router.get("/dividends/summary", response_model=DividendSummaryResponse)
async def get_dividends_summary():
    """
    Get dividend summary
    """
    try:
        total_dividend = PortfolioService.getDividendTotal()
        year_to_date_dividend = PortfolioService.getDividendYearToDate()
        yearly_forecast_dividend = PortfolioService.getDividendYearlyForecast()
        next_dividend_info = PortfolioService.getNextDividend()
        
        next_dividend_item = None
        if next_dividend_info and next_dividend_info.get('stockid'):
            # Get the position for the next dividend
            position = PortfolioService.getPositionById(next_dividend_info['stockid'])
            dividend_rate = next_dividend_info.get('dividend_rate', 0.0)
            
            if position and position.stock:
                next_dividend_item = DividendByStockItem(
                    symbol=position.stock.symbol,
                    name=position.stock.name,
                    quantity=position.quantity,
                    dividend_rate=round(dividend_rate, 2),
                    total_dividend=round(position.quantity * dividend_rate, 2)
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

@router.get("/dividends/breakdown", response_model=DividendBreakdownResponse)
async def get_dividends_breakdown():
    """
    Get dividend breakdown by stock
    """
    try:
        dividends = []
        total_dividend = 0.0
        
        for position in DatabaseService.positions.values():
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

@router.post("/positions/update-prices", response_model=UpdatePricesResponse)
async def update_portfolio_prices():
    """
    Update current prices for all positions in the portfolio
    """
    try:
        DatabaseService.updatePortfolioPositionsPrice()
        return UpdatePricesResponse(
            message="Position prices updated successfully",
            updated_count=len(DatabaseService.positions)
        )
    except Exception as e:
        logger.error(f"Error updating position prices: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update position prices: {str(e)}"
        )

@router.get("/value/history", response_model=PortfolioValueHistoryResponse)
async def get_portfolio_value_history():
    """
    Get portfolio value history
    """
    try:
        portfolio_value_history = PortfolioService.getPortfolioValueHistory()
        portfolio_value_history_items = []
        for item in portfolio_value_history:
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
