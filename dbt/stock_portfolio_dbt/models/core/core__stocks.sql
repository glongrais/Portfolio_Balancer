-- stock_portfolio_dbt/models/core/core__stocks.sql
WITH
stocks AS (
    SELECT
        stockid,
        name,
        symbol,
        price,
        currency,
        market_cap,
        sector,
        industry,
        country,
        logo_url,
        quote_type,
        ex_dividend_date,
        previous_close,
        dividend,
        dividend_yield
    FROM {{ ref('stg__stocks') }}
),
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
    NULL AS country,
    '' AS logo_url,
    'EQUITY' AS quote_type,
    NULL AS ex_dividend_date,
    0 AS previous_close,
    0 AS dividend,
    0 AS dividend_yield
FROM unlisted_stocks