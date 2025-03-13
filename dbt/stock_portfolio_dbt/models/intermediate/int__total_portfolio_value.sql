-- models/intermediate/int__total_portfolio_value.sql
WITH
positions AS (SELECT * FROM {{ ref('stg__positions') }}),
stocks AS (SELECT * FROM {{ ref('stg__stocks') }})

SELECT
    ROUND(SUM(positions.quantity * stocks.price), 2) AS total_portfolio_value
FROM positions
LEFT JOIN stocks
    ON positions.stockid = stocks.stockid
