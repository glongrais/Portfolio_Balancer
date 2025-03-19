-- stock_portfolio_dbt/models/intermediate/int__total_portfolio_dividends.sql
WITH
transactions AS (SELECT * FROM {{ ref('stg__transactions') }}),
dividend_transactions AS (
    SELECT
        stockid,
        SUM(quantity * price) AS total_dividends,
        datestamp
    FROM transactions
    WHERE type = 'DIVIDEND'
    GROUP BY stockid, datestamp
)

SELECT
    SUM(total_dividends) AS total_portfolio_dividends
FROM dividend_transactions
