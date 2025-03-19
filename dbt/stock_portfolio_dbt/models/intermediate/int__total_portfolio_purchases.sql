-- stock_portfolio_dbt/models/intermediate/int_total_portfolio_purchases.sql
WITH
positions AS (SELECT * FROM {{ ref('core__positions') }}),
average_cost_basis AS (SELECT * FROM {{ ref('int__average_cost_basis') }})

SELECT
    SUM(p.quantity * acb.average_cost_basis) AS total_portfolio_purchases
FROM positions AS p
JOIN average_cost_basis AS acb
    ON p.stock_id = acb.stock_id
