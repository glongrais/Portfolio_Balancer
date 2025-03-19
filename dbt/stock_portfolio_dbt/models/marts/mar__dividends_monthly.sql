-- stock_portfolio_dbt/models/marts/mar__dividends_monthly.sql
WITH
portfolio_dividends AS (SELECT * FROM {{ ref('int__transactions_dividends') }})

SELECT
    strftime('%Y-%m', datestamp) AS date,
    SUM(total_dividends) AS monthly_dividends
FROM portfolio_dividends
GROUP BY date
