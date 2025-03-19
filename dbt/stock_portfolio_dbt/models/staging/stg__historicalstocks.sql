-- stock_portfolio_dbt/models/staging/stg__historicalstocks.sql
WITH
historical_stocks AS (SELECT * FROM {{ source('sqlite', 'historicalstocks') }})

SELECT
    *
FROM historical_stocks