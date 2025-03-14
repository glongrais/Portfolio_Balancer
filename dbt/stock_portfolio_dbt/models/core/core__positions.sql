-- models/intermediate/core__positions.sql
WITH
positions AS (SELECT * FROM {{ ref('stg__positions') }}),
stocks AS (SELECT * FROM {{ ref('stg__stocks') }}),
total_portfolio_value AS (SELECT * FROM {{ ref('int__total_portfolio_value') }})

select 
    positions.stockid as stock_id,
    positions.quantity,
    ROUND(positions.distribution_target, 2) as distribution_target,
    ROUND((positions.quantity*stocks.price)/total_portfolio_value.total_portfolio_value*100, 2) as distribution_real
from positions
left join stocks
    on positions.stockid = stocks.stockid
cross join total_portfolio_value
