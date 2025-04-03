-- stock_portfolio_dbt/models/intermediate/int__transactions_dividends.sql
WITH
transactions AS (SELECT * FROM {{ ref('stg__transactions') }}),
stocks AS (SELECT * FROM {{ ref('stg__stocks') }}),
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
    s.stockid,
    s.name,
    s.symbol,
    dt.total_dividends,
    dt.datestamp
FROM dividend_transactions dt
JOIN stocks s
ON dt.stockid = s.stockid
