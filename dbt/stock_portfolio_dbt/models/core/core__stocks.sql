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
    NULL AS price,
    NULL AS currency,
    NULL AS market_cap,
    NULL AS sector,
    NULL AS industry,
    NULL AS country
FROM unlisted_stocks