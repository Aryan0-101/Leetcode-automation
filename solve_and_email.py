"""
Fetches LeetCode's daily challenge, asks Claude to solve it,
and emails the problem + solution.
"""

import os
import smtplib
import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import requests
from bs4 import BeautifulSoup
import openai


# ---------- 1. Fetch today's LeetCode problem ----------

def get_daily_problem():
    query = """
    query questionOfToday {
      activeDailyCodingChallengeQuestion {
        date
        link
        question {
          title
          titleSlug
          difficulty
          content
        }
      }
    }
    """
    resp = requests.post(
        "https://leetcode.com/graphql",
        json={"query": query},
        headers={"Content-Type": "application/json"},
        timeout=20,
    )
    resp.raise_for_status()
    data = resp.json()["data"]["activeDailyCodingChallengeQuestion"]

    # LeetCode's content field is HTML — strip it to clean text
    soup = BeautifulSoup(data["question"]["content"], "html.parser")
    data["question"]["content_text"] = soup.get_text("\n")
    data["full_link"] = "https://leetcode.com" + data["link"]
    return data


# ---------- 2. Ask Claude to solve it ----------

def solve_problem(problem):
    # Support third-party base URLs using the OPENAI_BASE_URL environment variable
    client = openai.OpenAI(
        api_key=os.environ["OPENAI_API_KEY"],
        base_url=os.environ.get("OPENAI_BASE_URL")
    )

    prompt = f"""Solve the following LeetCode problem in Python.

Title: {problem['question']['title']}
Difficulty: {problem['question']['difficulty']}

Problem description:
{problem['question']['content_text']}

Requirements:
- Provide a complete, correct, efficient solution.
- Include the time and space complexity.
- Briefly explain the approach (3-5 sentences) before the code.
- Format the code in a Python code block.
"""
    
    # Allows setting a custom model, default to gpt-4o
    model = os.environ.get("OPENAI_MODEL", "gpt-4o")

    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content


# ---------- 3. Email the result ----------

def send_email(problem, solution_text):
    sender = os.environ["EMAIL_SENDER"]
    password = os.environ["EMAIL_APP_PASSWORD"]
    recipient = os.environ["EMAIL_RECIPIENT"]

    today = datetime.date.today().isoformat()
    subject = f"[LeetCode Daily] {today} — {problem['question']['title']}"

    body = f"""Today's LeetCode Daily Challenge
Date: {today}
Difficulty: {problem['question']['difficulty']}
Link: {problem['full_link']}

{'-' * 50}
SOLUTION
{'-' * 50}

{solution_text}
"""

    msg = MIMEMultipart()
    msg["From"] = sender
    msg["To"] = recipient
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(sender, password)
        server.sendmail(sender, recipient, msg.as_string())


# ---------- Main ----------

if __name__ == "__main__":
    problem = get_daily_problem()
    solution = solve_problem(problem)
    send_email(problem, solution)
    print(f"Emailed solution for: {problem['question']['title']}")
