-- stock_portfolio_dbt/int__total_portfolio_deposits.sql
WITH
portfolio_deposits AS (SELECT * FROM {{ ref('stg__deposits') }})

SELECT
    SUM(amount) AS total_deposits
FROM portfolio_deposits
