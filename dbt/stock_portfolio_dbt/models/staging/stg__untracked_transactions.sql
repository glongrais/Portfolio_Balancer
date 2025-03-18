-- stock_portfolio_dbt/models/staging/stg_untracked_transactions.sql
WITH
untracked_transactions AS (SELECT rowid,* FROM {{ ref('untracked_transactions') }})

SELECT
    -(rowid+100) AS transactionid,
    *
FROM untracked_transactions
