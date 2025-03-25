-- stock_portfolio_dbt/models/intermediate/int__portfolio_positions_evolution.sql
WITH
stocks AS (SELECT * FROM {{ ref('core__stocks') }}),
transactions_buy AS (
    SELECT
        stockid,
        datestamp,
        quantity
    FROM {{ ref('core__transactions') }}
    WHERE type = 'BUY'
),
transactions_sell AS (
    SELECT
        stockid,
        datestamp,
        -quantity as quantity
    FROM {{ ref('core__transactions') }}
    WHERE type = 'SELL'
),
transactions_union AS (
    SELECT * FROM transactions_buy
    UNION ALL
    SELECT * FROM transactions_sell
),
transactions AS (
    SELECT
        stockid,
        datestamp,
        SUM(quantity) AS daily_quantity
    FROM transactions_union
    GROUP BY stockid, datestamp
),
cumulative_positions AS (
    SELECT
        stockid,
        datestamp,
        SUM(daily_quantity) OVER (
            PARTITION BY stockid
            ORDER BY datestamp
        ) AS cumulative_quantity
    FROM transactions
)
SELECT
    strftime('%Y-%m-%d', cp.datestamp) AS datestamp,
    cp.stockid,
    s.name AS stock_name,
    s.symbol AS stock_symbol,
    cp.cumulative_quantity
FROM cumulative_positions cp
LEFT JOIN stocks s
    ON cp.stockid = s.stockid
