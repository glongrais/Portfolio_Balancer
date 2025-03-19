WITH
dividends AS (SELECT * FROM {{ ref('int__transactions_dividends') }})

SELECT
    stockid,
    name,
    symbol,
    SUM(total_dividends) as total_dividends
FROM dividends
GROUP BY stockid, name, symbol