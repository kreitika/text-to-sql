import streamlit as st
import pandas as pd
from run_query import answer_question

# ---- Page setup ----
st.set_page_config(page_title="Ask Your Database", page_icon="🛢️", layout="centered")

st.title("Ask Your Database")
st.caption("Type a question in plain English. Every answer is checked for safety and reliability before you see it.")

# ---- The confidence badge: our signature element ----
def show_confidence(label, score):
    colors = {"HIGH": "#1a7f37", "MEDIUM": "#9a6700", "LOW": "#cf222e"}
    color = colors.get(label, "#57606a")
    st.markdown(
        f"""
        <div style="display:inline-block; padding:6px 14px; border-radius:999px;
                    background:{color}; color:white; font-weight:600; font-size:0.9rem;">
            {label} confidence · {score}/100
        </div>
        """,
        unsafe_allow_html=True,
    )

# ---- Input ----
question = st.text_input("Your question", placeholder="How many customers signed up this year?")

if st.button("Ask", type="primary") and question:
    with st.spinner("Generating SQL, checking safety, running query…"):
        result = answer_question(question)

    # ---- Refusal / validation failure ----
    if not result.get("sql"):
        st.error(f"Couldn't answer this one. {result.get('detail', '')}")
    else:
        show_confidence(result["label"], result["confidence"])

        st.subheader("Generated SQL")
        st.code(result["sql"], language="sql")

        # ---- Why this score ----
        with st.expander("Why this confidence level?"):
            for r in result.get("reasons", []):
                st.write(f"• {r}")
            if result.get("hallucination_problems"):
                for p in result["hallucination_problems"]:
                    st.write(f"⚠️ {p}")

        # ---- Results ----
        st.subheader("Result")
        if result["ok"] and result["rows"]:
            df = pd.DataFrame(result["rows"])
            st.dataframe(df, use_container_width=True)
        elif result["ok"]:
            st.info("The query ran successfully but returned no rows.")
        else:
            st.error(f"Execution failed: {result.get('exec_error', 'unknown error')}")