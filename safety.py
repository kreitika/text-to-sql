import re
import sqlparse

def clean_sql(raw):
    """Strip markdown fences and surrounding whitespace the model sometimes adds."""
    text = raw.strip()
    # Remove ```sql ... ``` or ``` ... ``` fences if present
    text = re.sub(r"^```(?:sql)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()




BLOCKED = {"INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE",
           "CREATE", "GRANT", "REVOKE", "REPLACE"}

def validate_sql(sql):
    """Return (is_safe, reason). Blocks anything that isn't a lone SELECT."""
    parsed = sqlparse.parse(sql)

    if len(parsed) != 1:
        return False, "Multiple statements are not allowed."

    statement = parsed[0]
    first_keyword = statement.token_first(skip_cm=True)

    if first_keyword is None or first_keyword.normalized != "SELECT":
        return False, "Only SELECT queries are allowed."

    upper = sql.upper()
    for word in BLOCKED:
        if re.search(rf"\b{word}\b", upper):
            return False, f"Blocked keyword found: {word}"

    return True, "OK"


if __name__ == "__main__":
    tests = [
        "```sql\nSELECT * FROM customers;\n```",   # fenced — cleaner should fix
        "SELECT COUNT(*) FROM orders;",             # safe
        "DROP TABLE customers;",                    # must block
        "SELECT 1; DELETE FROM orders;",            # injection — must block
    ]
    for t in tests:
        cleaned = clean_sql(t)
        safe, reason = validate_sql(cleaned)
        print(f"{'✅' if safe else '🚫'}  {reason:35}  <- {cleaned[:40]}")