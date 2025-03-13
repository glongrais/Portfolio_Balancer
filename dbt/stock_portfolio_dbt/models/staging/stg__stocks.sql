-- models/staging/stg__stocks.sql
WITH
stocks AS (SELECT * FROM {{ source('sqlite', 'stocks') }})

select 
    *
from stocks
