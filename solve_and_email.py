"""
Fetches LeetCode's daily challenge, asks AI to solve it,
submits the solution to LeetCode, and emails the result.
"""

import os
import re
import time
import smtplib
import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import requests
from bs4 import BeautifulSoup
from google import genai


# ---------- 1. Fetch today's LeetCode problem ----------

def get_daily_problem():
    query = """
    query questionOfToday {
      activeDailyCodingChallengeQuestion {
        date
        link
        question {
          questionId
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

    soup = BeautifulSoup(data["question"]["content"], "html.parser")
    data["question"]["content_text"] = soup.get_text("\n")
    data["full_link"] = "https://leetcode.com" + data["link"]
    return data


# ---------- 2. Ask AI to solve it ----------

def solve_problem(problem, previous_code=None, error_feedback=None):
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    prompt = f"""Solve the following LeetCode problem in Python3.

Title: {problem['question']['title']}
Difficulty: {problem['question']['difficulty']}

Problem description:
{problem['question']['content_text']}

Requirements:
- Provide a complete, correct, efficient solution.
- The solution MUST be wrapped in a python code block (```python ... ```).
- Follow the exact class and method signature expected by LeetCode.
"""
    
    if error_feedback:
        prompt += f"""
---
IMPORTANT: Your previous attempt failed! 
Here is the error feedback from LeetCode:
{error_feedback}

Here was your previous code:
```python
{previous_code}
```

Please analyze the error, fix the bugs in your code, and provide the corrected solution.
"""

    model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

    response = client.models.generate_content(
        model=model,
        contents=prompt,
    )
    return response.text

def extract_code(solution_text):
    match = re.search(r'```python\n(.*?)\n```', solution_text, re.DOTALL)
    if match:
        return match.group(1).strip()
    # Fallback to returning the raw text if no code block is found
    return solution_text.strip()


# ---------- 3. Submit to LeetCode ----------

def submit_to_leetcode(problem, code):
    session = os.environ.get("LEETCODE_SESSION")
    csrf = os.environ.get("LEETCODE_CSRF")
    
    if not session or not csrf:
        return {"status_msg": "Not Submitted (Missing LeetCode Credentials)"}
    
    submit_url = f"https://leetcode.com/problems/{problem['question']['titleSlug']}/submit/"
    
    headers = {
        "Cookie": f"LEETCODE_SESSION={session}; csrftoken={csrf}",
        "X-CSRFToken": csrf,
        "Referer": f"https://leetcode.com/problems/{problem['question']['titleSlug']}/",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }
    
    payload = {
        "lang": "python3",
        "question_id": problem['question']['questionId'],
        "typed_code": code
    }
    
    print(f"Submitting to {submit_url}...")
    resp = requests.post(submit_url, json=payload, headers=headers)
    
    if resp.status_code != 200:
        return {"status_msg": f"Submission Failed (HTTP {resp.status_code})", "details": resp.text}
        
    data = resp.json()
    submission_id = data.get("submission_id")
    
    if not submission_id:
        return {"status_msg": "Submission Failed (No submission_id returned)", "details": str(data)}
    
    print(f"Submission ID: {submission_id}. Polling for results...")
    check_url = f"https://leetcode.com/submissions/detail/{submission_id}/check/"
    
    for _ in range(15):
        time.sleep(2)
        check_resp = requests.get(check_url, headers=headers)
        if check_resp.status_code == 200:
            result = check_resp.json()
            state = result.get("state")
            if state == "SUCCESS":
                return result
    
    return {"status_msg": "Timeout while grading"}


# ---------- 4. Email the result ----------

def send_email(problem, solution_text, submission_result):
    sender = os.environ["EMAIL_SENDER"]
    password = os.environ["EMAIL_APP_PASSWORD"]
    recipient = os.environ["EMAIL_RECIPIENT"]

    today = datetime.date.today().isoformat()
    status = submission_result.get("status_msg", "Unknown")

    subject = f"[LeetCode Daily] {status} — {problem['question']['title']}"

    body = f"""Today's LeetCode Daily Challenge
Date: {today}
Difficulty: {problem['question']['difficulty']}
Link: {problem['full_link']}

Submission Status: {status}
Runtime: {submission_result.get('status_runtime', 'N/A')}
Memory: {submission_result.get('status_memory', 'N/A')}

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

MAX_RETRIES = 3

if __name__ == "__main__":
    try:
        problem = get_daily_problem()
        print(f"Fetched problem: {problem['question']['title']}")
        
        error_feedback = None
        previous_code = None
        
        for attempt in range(MAX_RETRIES):
            print(f"--- Attempt {attempt + 1} of {MAX_RETRIES} ---")
            solution_text = solve_problem(problem, previous_code, error_feedback)
            print("Generated solution.")
            
            raw_code = extract_code(solution_text)
            
            submission_result = submit_to_leetcode(problem, raw_code)
            status = submission_result.get("status_msg", "Unknown")
            print(f"Submission result: {status}")
            
            if status == "Accepted":
                print("Solution Accepted!")
                break
                
            print("Failed. Generating feedback for AI...")
            error_feedback = f"Status: {status}\n"
            if status == "Compile Error":
                error_feedback += f"Compile Error: {submission_result.get('compile_error', '')}\n"
            elif status == "Runtime Error":
                error_feedback += f"Runtime Error: {submission_result.get('full_runtime_error', '')}\n"
            elif status in ["Wrong Answer", "Time Limit Exceeded"]:
                error_feedback += f"Last Testcase Input: {submission_result.get('last_testcase', '')}\n"
                error_feedback += f"Your Output: {submission_result.get('code_output', '')}\n"
                error_feedback += f"Expected Output: {submission_result.get('expected_output', '')}\n"
                
            previous_code = raw_code
            time.sleep(3) # Small delay before retrying
            
        send_email(problem, solution_text, submission_result)
        print(f"Emailed final solution for: {problem['question']['title']}")
        
    except Exception as e:
        print(f"A critical error occurred: {e}")
        # Send an emergency email about the failure
        error_problem = {
            "question": {
                "title": "Script Execution Error",
                "difficulty": "N/A"
            },
            "full_link": "N/A"
        }
        error_submission_result = {
            "status_msg": "CRITICAL SCRIPT ERROR",
            "status_runtime": "N/A",
            "status_memory": "N/A"
        }
        error_solution_text = f"The automation failed to run today. Here is the technical error:\n\n{str(e)}\n\nYou may need to top up your API balance or fix your credentials."
        
        try:
            send_email(error_problem, error_solution_text, error_submission_result)
        except Exception as inner_e:
            print(f"Could not send error email: {inner_e}")
