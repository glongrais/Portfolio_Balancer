-- models/staging/stg__transactions.sql
WITH
transactions AS (SELECT * FROM {{ source('sqlite', 'transactions') }})

select 
    *
from transactions