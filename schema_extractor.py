# ============================================================
# schema_extractor.py — reads the database's own structure and
# formats it as text the LLM can understand.
# ============================================================

import psycopg2

conn = psycopg2.connect(dbname="ecommerce")
cur = conn.cursor()


# ------------------------------------------------------------
# 1. List every table in our database
# ------------------------------------------------------------

cur.execute("""
    SELECT table_name
    FROM information_schema.tables
    WHERE table_schema = 'public'      -- 'public' = OUR tables, not Postgres internals
    ORDER BY table_name;
""")

# fetchall() returns a list of row tuples: [('categories',), ('customers',), ...]
# This comprehension pulls the first item out of each tuple.
tables = [row[0] for row in cur.fetchall()]


# ------------------------------------------------------------
# 2. Get the columns of a given table
# ------------------------------------------------------------

def get_columns(table_name):
    cur.execute("""
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = %s
        ORDER BY ordinal_position;    -- declared order, not alphabetical (reads naturally)
    """, (table_name,))               # %s parameterized — safe habit even on system tables
    return cur.fetchall()


# ------------------------------------------------------------
# 3. Get the foreign keys (the relationships between tables)
# ------------------------------------------------------------

def get_foreign_keys():
    # Postgres splits FK info across three system views, so we JOIN them
    # back together on constraint_name. Same 3-table JOIN pattern as practice.
    cur.execute("""
        SELECT
            tc.table_name,                          -- the table holding the FK
            kcu.column_name,                        -- the FK column itself
            ccu.table_name  AS foreign_table,       -- the table it points AT
            ccu.column_name AS foreign_column       -- the column it points at
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
            ON tc.constraint_name = kcu.constraint_name
        JOIN information_schema.constraint_column_usage ccu
            ON tc.constraint_name = ccu.constraint_name
        WHERE tc.constraint_type = 'FOREIGN KEY'
            AND tc.table_schema = 'public';
    """)
    return cur.fetchall()


# ------------------------------------------------------------
# 4. Format everything into LLM-readable text
# ------------------------------------------------------------

def build_schema_text():
    fks = get_foreign_keys()
    lines = []

    for t in tables:
        lines.append(f"Table: {t}")
        for col, dtype, nullable in get_columns(t):
            # Flag nullable columns so the model knows to handle NULLs (IS NULL, not !=)
            null_note = "" if nullable == "NO" else " (nullable)"
            lines.append(f"  - {col}: {dtype}{null_note}")
        lines.append("")                      # blank line between tables

    lines.append("Relationships:")
    for table, col, ftable, fcol in fks:
        lines.append(f"  - {table}.{col} -> {ftable}.{fcol}")

    return "\n".join(lines)


# Only runs when this file is executed directly — not when imported elsewhere.
if __name__ == "__main__":
    print(build_schema_text())




