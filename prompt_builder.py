from schema_extractor import build_schema_text

SYSTEM_PROMPT = """You are a PostgreSQL expert. Convert the user's question into a single SQL query.

Rules:
- Output ONLY the SQL query. No explanation, no markdown fences.
- Use ONLY tables and columns listed in the schema below.
- Never write INSERT, UPDATE, DELETE, DROP, ALTER, or TRUNCATE. SELECT only.
- Always add LIMIT 100 unless the query is an aggregate.
- Columns marked (nullable) may contain NULL — use IS NULL / IS NOT NULL, never = NULL.
- If the question cannot be answered from this schema, output exactly: CANNOT_ANSWER
"""

from datetime import date

def build_prompt(question):
    schema = build_schema_text()
    today = date.today().isoformat()
    system = (
        f"{SYSTEM_PROMPT}\n\n"
        f"Today's date is {today}. Use this for any relative time references "
        f"like 'this year', 'last month', 'recent'.\n\n"
        f"DATABASE SCHEMA:\n{schema}"
    )
    return system, question

if __name__ == "__main__":
    system, user = build_prompt("How many customers are there?")
    print(system)
    print("---")
    print(user)


