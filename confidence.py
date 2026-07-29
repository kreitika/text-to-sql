import sqlparse

def score_confidence(sql, executed_ok, row_count, hallucination_problems):
    """Combine signals into a 0-100 confidence score + human-readable reasons.
    This is a HEURISTIC, not a calibrated probability."""

    score = 100
    reasons = []

    # Hallucination is the strongest negative signal.
    if hallucination_problems:
        score -= 50
        reasons.append(f"Hallucination detected ({len(hallucination_problems)} issue(s)): -50")

    # A query that failed to execute is barely trustworthy.
    if not executed_ok:
        score -= 40
        reasons.append("Query failed to execute: -40")

    # Zero rows is ambiguous — could be empty-but-correct, could be silent failure.
    if executed_ok and row_count == 0:
        score -= 20
        reasons.append("Query returned no rows (ambiguous): -20")

    # Complexity penalty: more joins = more room for error.
    # Count JOINs robustly via token inspection, not fragile string matching.
    join_count = 0
    for token in sqlparse.parse(sql)[0].flatten():
        if token.ttype is sqlparse.tokens.Keyword and token.value.upper().endswith("JOIN"):
            join_count += 1

    if join_count >= 3:
        score -= 15
        reasons.append(f"High complexity ({join_count} joins): -15")
    elif join_count >= 1:
        score -= 5
        reasons.append(f"Moderate complexity ({join_count} join(s)): -5")

    # Clamp to 0-100.
    score = max(0, min(100, score))

    if not reasons:
        reasons.append("All checks passed cleanly.")

    return score, reasons


def confidence_label(score):
    """Turn the number into a plain-English trust level."""
    if score >= 80:
        return "HIGH"
    elif score >= 50:
        return "MEDIUM"
    else:
        return "LOW"