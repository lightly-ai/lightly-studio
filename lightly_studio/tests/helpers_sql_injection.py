"""Metadata keys that carry a SQL-injection payload.

Keys reach the query builders from filter and sort fields in request bodies, and
nothing validates them. Each key below changes the statement if a query builder
pastes it into the SQL text instead of binding it.

Import the module and use ``helpers_sql_injection.PAYLOADS`` so that the compiled-SQL
tests and the end-to-end tests stay in step.
"""

PAYLOADS = [
    # Closes the string literal and starts a new statement.
    "x'); DROP TABLE victim; --",
    # Closes the DuckDB json_extract call and appends a subquery.
    "x') AS FLOAT), (SELECT 1 FROM victim) --",
    # Turns the comparison into a tautology.
    "temp' OR '1'='1",
    # Rides in through the array-index brackets, which once rendered unquoted.
    "a[0; DROP TABLE victim]",
    # Reads as JSONPath rather than as a key name.
    "$.temp",
    # Concatenates a subquery into the value.
    "'||(SELECT count(*) FROM victim)||'",
]
