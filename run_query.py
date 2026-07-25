import os
import psycopg2
from dotenv import load_dotenv
from generate_sql import generate_sql
from safety import clean_sql, validate_sql

load_dotenv()

def answer_question(question):
    # 1. Generate SQL from English
    raw = generate_sql(question)

    # 2. Layer 1 — clean formatting
    sql = clean_sql(raw)

    # Model's explicit refusal
    if sql.strip() == "CANNOT_ANSWER":
        return {"ok": False, "stage": "generation", "detail": "Model could not answer."}

    # 3. Layer 2 — validate it's a safe read-only SELECT
    safe, reason = validate_sql(sql)
    if not safe:
        return {"ok": False, "stage": "validation", "detail": reason, "sql": sql}

    # 4. Layer 3 — execute as the READ-ONLY user
    try:
        conn = psycopg2.connect(
            dbname=os.getenv("DB_NAME"),
            user=os.getenv("DB_READONLY_USER"),
            password=os.getenv("DB_READONLY_PASSWORD"),
            host="localhost",
        )
        cur = conn.cursor()
        cur.execute(sql)
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return {"ok": True, "sql": sql, "rows": rows}
    except Exception as e:
        return {"ok": False, "stage": "execution", "detail": str(e), "sql": sql}





if __name__ == "__main__":
    for q in ["How many customers are there?",
              "Which category earned the most revenue?",
              "Delete all customers"]:
        print(f"\nQ: {q}")
        result = answer_question(q)
        print(result)