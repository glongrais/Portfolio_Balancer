-- models/staging/stg__positions.sql
WITH
positions AS (SELECT * FROM {{ source('sqlite', 'positions') }})

select 
    *
from positions