-- stock_portfolio_dbt/models/core/core__stocks.sql
WITH
stocks AS (SELECT * FROM {{ ref('stg__stocks') }}),
unlisted_stocks AS (SELECT * FROM {{ ref('stg__unlisted_stocks') }})

SELECT
    *
FROM stocks
UNION ALL
SELECT
    stockid,
    name,
    symbol,
    NULL AS price
FROM unlisted_stocks