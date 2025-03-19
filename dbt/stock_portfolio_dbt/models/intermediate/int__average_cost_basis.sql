WITH
transactions_buy AS (SELECT * FROM {{ ref('core__transactions') }} WHERE type = 'BUY'),
transactions_sell AS (SELECT * FROM {{ ref('core__transactions') }} WHERE type = 'SELL'),

transactions_buy_grouped AS (
    SELECT
        stockid,
        SUM(quantity) AS total_quantity,
        SUM(quantity * price) AS total_cost
    FROM transactions_buy
    GROUP BY stockid
),

transactions_sell_grouped AS (
    SELECT
        stockid,
        SUM(quantity) AS total_quantity,
        SUM(quantity * price) AS total_cost
    FROM transactions_sell
    GROUP BY stockid
)

SELECT
    tb.stockid as stock_id,
    CASE
        WHEN (tb.total_quantity - COALESCE(ts.total_quantity, 0)) > 0
        THEN ROUND((tb.total_cost - COALESCE(ts.total_cost, 0)) / (tb.total_quantity - COALESCE(ts.total_quantity, 0)), 3)
        ELSE 0
    END AS average_cost_basis
FROM transactions_buy_grouped tb
LEFT JOIN transactions_sell_grouped ts
ON tb.stockid = ts.stockid
