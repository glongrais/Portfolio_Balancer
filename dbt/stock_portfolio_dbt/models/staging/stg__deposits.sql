-- models/staging/stg__deposits.sql
WITH
deposits AS (SELECT * FROM {{ source('sqlite', 'deposits') }})

select 
    *
from deposits