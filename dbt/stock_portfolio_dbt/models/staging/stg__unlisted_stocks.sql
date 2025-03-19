-- stock_portfolio_dbt/models/staging/stg__unlisted_stocks.sql
WITH
unlisted_companies AS (SELECT rowid, * FROM {{ ref('unlisted_companies') }})

SELECT
    -(rowid+100) AS stockid,
    symbol,
    name
FROM unlisted_companies