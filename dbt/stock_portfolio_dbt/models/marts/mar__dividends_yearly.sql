-- stock_portfolio_dbt/models/marts/mar__dividends_yearly.sql
WITH
portfolio_dividends AS (SELECT * FROM {{ ref('int__transactions_dividends') }})

SELECT
    strftime('%Y', datestamp) AS year,
    SUM(total_dividends) AS yearly_dividends
FROM portfolio_dividends
GROUP BY year
