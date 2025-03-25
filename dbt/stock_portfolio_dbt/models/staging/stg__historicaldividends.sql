-- stock_portfolio_dbt/staging/stg__historicaldividends.sql
WITH
historical_dividends AS (SELECT * FROM {{ source('sqlite', 'historicaldividends') }})

SELECT
    *
FROM historical_dividends