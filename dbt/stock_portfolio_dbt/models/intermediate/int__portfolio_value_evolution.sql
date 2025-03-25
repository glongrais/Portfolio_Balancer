-- stock_portfolio_dbt/models/intermediate/int__portfolio_value_evolution.sql
WITH 
historical_stocks AS (SELECT * FROM {{ ref('stg__historicalstocks') }}),
portfolio_positions_evolution AS (SELECT * FROM {{ ref('int__portfolio_positions_evolution') }}),

filled_cumulative_datestamp AS (
    SELECT
        historical_stocks.*,
        portfolio_positions_evolution.cumulative_quantity AS cumulative_quantity,
        MAX(historical_stocks.datestamp)
            FILTER (WHERE portfolio_positions_evolution.cumulative_quantity>0)
            OVER (
            PARTITION BY historical_stocks.stockid
            ORDER BY historical_stocks.datestamp
                ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
            ) AS last_updated_datestamp
    FROM historical_stocks
    LEFT JOIN portfolio_positions_evolution
        ON historical_stocks.datestamp = portfolio_positions_evolution.datestamp
        AND historical_stocks.stockid = portfolio_positions_evolution.stockid
    WHERE historical_stocks.datestamp >= (SELECT MIN(datestamp) FROM portfolio_positions_evolution)
),

filled_cumulative_quantity AS (
    SELECT
        fcd.closeprice,
        fcd.datestamp,
        fcd.stockid,
        ppe.cumulative_quantity AS filled_cumulative_quantity 
    FROM filled_cumulative_datestamp fcd
    LEFT JOIN portfolio_positions_evolution ppe
        ON fcd.last_updated_datestamp = ppe.datestamp
        AND fcd.stockid = ppe.stockid
)

SELECT
    datestamp,
    ROUND(SUM(filled_cumulative_quantity * closeprice), 2) AS portfolio_value
FROM filled_cumulative_quantity
GROUP BY datestamp
