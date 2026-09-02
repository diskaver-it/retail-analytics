{#
    By default dbt glues the target schema onto the custom one and you end up
    with main_staging / main_marts. The dashboard queries these schemas by name,
    so keep them as written.
#}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
