-- macros/test_sum_consistency.sql
{% macro test_sum_consistency(model1, model2, column1, column2) %}
WITH
model1_sum AS (
    SELECT ROUND(SUM({{ column1 }})) AS sum_value
    FROM {{ ref(model1) }}
),
model2_sum AS (
    SELECT ROUND(SUM({{ column2 }})) AS sum_value
    FROM {{ ref(model2) }}
)

SELECT
    m1.sum_value AS {{ model1 }}_sum,
    m2.sum_value AS {{ model2 }}_sum
FROM model1_sum m1, model2_sum m2
WHERE m1.sum_value != m2.sum_value
{% endmacro %}
