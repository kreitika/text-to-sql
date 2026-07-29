import os
import psycopg2
from dotenv import load_dotenv
from generate_sql import generate_sql
from safety import clean_sql, validate_sql
from hallucination import check_hallucination
from confidence import score_confidence, confidence_label

load_dotenv()

def answer_question(question):
    raw = generate_sql(question)
    sql = clean_sql(raw)

    if sql.strip() == "CANNOT_ANSWER":
        return {"ok": False, "stage": "generation", "confidence": 0,
                "label": "LOW", "detail": "Model could not answer."}

    safe, reason = validate_sql(sql)
    if not safe:
        return {"ok": False, "stage": "validation", "confidence": 0,
                "label": "LOW", "detail": reason, "sql": sql}

    # Hallucination check (before execution)
    valid, problems = check_hallucination(sql)

    # Execute as read-only user
    executed_ok = False
    rows = []
    exec_error = None
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
        executed_ok = True
        cur.close()
        conn.close()
    except Exception as e:
        exec_error = str(e)

    score, reasons = score_confidence(sql, executed_ok, len(rows), problems)

    return {
        "ok": executed_ok,
        "sql": sql,
        "rows": rows,
        "confidence": score,
        "label": confidence_label(score),
        "reasons": reasons,
        "hallucination_problems": problems,
        "exec_error": exec_error,
    }




if __name__ == "__main__":
    questions = [
        "How many customers are there?",              # simple, should be HIGH
        "Which category earned the most revenue?",    # 3 joins, should dip to MEDIUM
        "How many orders were completed?",            # maps to delivered — interesting
        "List customers from Atlantis",               # real column, impossible value
    ]
    for q in questions:
        print(f"\nQ: {q}")
        r = answer_question(q)
        print(f"   [{r['label']} {r['confidence']}]  {r.get('sql', '')[:60]}")
        for reason in r.get("reasons", []):
            print(f"      - {reason}")
        print(f"   rows: {r.get('rows', [])[:3]}")