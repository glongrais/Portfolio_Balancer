-- stock_portfolio_dbt/models/intermediate/int__stocks_dividends_yearly.sql
WITH
historical_dividends AS (SELECT * FROM {{ ref('stg__historicaldividends') }})

SELECT
    stockid,
    strftime('%Y', datestamp) AS date,
    SUM(dividendvalue) AS dividend
FROM historical_dividends
GROUP BY stockid, date