import os
from openai import OpenAI
from dotenv import load_dotenv
from prompt_builder import build_prompt

load_dotenv()                                  # reads .env into the environment
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def generate_sql(question):
    system, user = build_prompt(question)

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0,
    )
    return response.choices[0].message.content


if __name__ == "__main__":
    questions = [
        "How many customers are there?",
        "Which category earned the most revenue?",
        "How many orders were completed?",
    ]
    for q in questions:
        print(f"\nQ: {q}")
        print(f"SQL: {generate_sql(q)}")