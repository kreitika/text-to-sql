# ============================================================
# hallucination.py — catches references to tables/columns that
# don't exist in the real schema, BEFORE the query hits the DB.
#
# Why bother, when the database would reject them anyway?
# Without this: Postgres throws a cryptic "column does not exist"
#   error, only AFTER a round-trip.
# With this: we catch it early and turn it into a clear, structured
#   signal ("the model hallucinated column X") that we can log,
#   message to the user, and feed into confidence scoring (M7).
# ============================================================

import sqlparse
from schema_extractor import get_schema_map


def check_hallucination(sql):
    """Check qualified (table.column) references against the real schema.

    Returns (is_valid, list_of_problems).
    Strategy: conservative first cut — flag columns that exist NOWHERE
    in the schema. We don't fully resolve aliases yet (that's the hard
    part), so we check "does this column exist somewhere?" rather than
    "does it exist in THIS specific table?"
    """

    # 1. Build the ground truth of what actually exists.
    schema = get_schema_map()                 # {table: {columns}}
    real_tables = set(schema.keys())          # every real table name

    all_real_columns = set()                  # every real column, across all tables
    for cols in schema.values():
        all_real_columns |= cols              # |= is set union: merge each table's columns in

    problems = []

    # 2. Flatten the SQL into a flat list of tokens (words, dots, symbols).
    #    parse(sql)[0] = the first (only) statement; .flatten() = all tokens.
    parsed = sqlparse.parse(sql)[0]
    tokens = list(parsed.flatten())

    # 3. Walk the tokens looking for the pattern:  <name> . <name>
    #    The "." is our anchor — it marks a qualified reference like p.category.
    for i, tok in enumerate(tokens):
        if tok.value == "." and 0 < i < len(tokens) - 1:
            left = tokens[i - 1].value.lower()    # the table or alias (e.g. "p")
            right = tokens[i + 1].value.lower()   # the column (e.g. "category")

            # Only check things that look like plain identifiers
            # (letters/digits/underscores) — skips functions, numbers, etc.
            if right.replace("_", "").isalnum() and right not in all_real_columns:
                # The column on the right exists in NO table → hallucination.
                problems.append(f"Column '{right}' does not exist in any table.")

    # 4. Valid only if we found zero problems.
    return (len(problems) == 0), problems


# ------------------------------------------------------------
# Test cases
# ------------------------------------------------------------

if __name__ == "__main__":
    tests = [
        "SELECT c.name FROM categories c;",              # valid — 'name' exists
        "SELECT p.category FROM products p;",            # hallucinated — real col is category_id
        "SELECT o.customer_id FROM orders o;",           # valid — 'customer_id' exists
        "SELECT x.nonexistent_col FROM customers x;",    # hallucinated — made-up column
    ]

    for sql in tests:
        valid, problems = check_hallucination(sql)
        mark = "✅" if valid else "🚫"
        print(f"{mark}  {sql}")
        for p in problems:
            print(f"     → {p}")