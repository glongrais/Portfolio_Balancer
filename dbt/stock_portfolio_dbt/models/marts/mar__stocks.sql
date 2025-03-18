-- stock_portfolio_dbt/models/marts/mar__stocks.sql
WITH
stocks AS (SELECT * FROM {{ ref('core__stocks') }})

SELECT
    *
FROM stocks