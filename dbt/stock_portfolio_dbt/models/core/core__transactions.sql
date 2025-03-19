-- stock_portfolio_dbt/models/intermediate/int_transactions.sql
WITH
transactions AS (SELECT * FROM {{ ref('stg__transactions') }}),
untracked_transactions AS (SELECT * FROM {{ ref('stg__untracked_transactions') }}),

transactions_all AS(
    SELECT
        t.transactionid,
        t.stockid,
        t.quantity,
        t.price,
        t.type,
        t.datestamp,
        t.rowid,
        t.portfolioid,
        CASE
            WHEN t.stockid > 0 THEN 'TRACKED'
            ELSE 'UNTRACKED'
        END AS status
    FROM transactions AS t
    UNION
    SELECT
        ut.transactionid,
        ut.stockid,
        ut.quantity,
        ut.price,
        ut.type,
        ut.datestamp,
        ut.rowid,
        ut.portfolioid,
        'UNTRACKED' AS status
    FROM untracked_transactions AS ut
)

SELECT
    *
FROM transactions_all
