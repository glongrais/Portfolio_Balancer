-- stock_portfolio_dbt/models/intermediate/int_transactions.sql
WITH
transactions AS (SELECT * FROM {{ ref('stg__transactions') }}),
untracked_transactions AS (SELECT * FROM {{ ref('untracked_transactions') }}),

transactions_all AS(
    SELECT
        t.stockid,
        t.datestamp,
        t.type,
        t.quantity,
        t.price,
        t.portfolioid,
        'TRACKED' AS status
    FROM transactions AS t
    UNION
    SELECT
        ut.stockid,
        ut.datestamp,
        ut.type,
        ut.quantity,
        ut.price,
        ut.portfolioid,
        'UNTRACKED' AS status
    FROM untracked_transactions AS ut
)

SELECT
    *
FROM transactions_all
