WITH
positions AS (SELECT stock_id, quantity FROM {{ ref('core__positions') }}),
transactions AS (
    SELECT
        stockid AS stock_id,
        SUM(CASE WHEN type = 'BUY' THEN quantity WHEN type = 'SELL' THEN -quantity ELSE 0 END) AS quantity
    FROM {{ ref('core__transactions') }}
    GROUP BY stockid
)

SELECT
    p.stock_id,
    p.quantity AS position_quantity,
    t.quantity AS transaction_quantity
FROM positions p
JOIN transactions t
ON p.stock_id = t.stock_id
WHERE p.quantity != t.quantity
