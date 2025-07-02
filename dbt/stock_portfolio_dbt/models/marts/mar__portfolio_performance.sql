-- dbt/stock_portfolio_dbt/models/marts/mar__portfolio_performance.sql

WITH
portfolio_value_total AS (SELECT * FROM {{ ref('int__portfolio_value_total') }}),
portfolio_purchases_total AS (SELECT * FROM {{ ref('int__portfolio_purchases_total') }})

SELECT
    ROUND(SUM(portfolio_value_total.total_portfolio_value), 2) AS portfolio_value,
    ROUND(SUM(portfolio_purchases_total.total_portfolio_purchases), 2) AS total_portfolio_purchases,
    ROUND(SUM(portfolio_value_total.total_portfolio_value) - SUM(portfolio_purchases_total.total_portfolio_purchases), 2) AS portfolio_performance
FROM portfolio_value_total
JOIN portfolio_purchases_total
