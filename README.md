# Daily LeetCode Solver

A fully automated tool that runs on GitHub Actions. Every day at 12:00 PM IST (06:55 AM UTC), it fetches the "Daily Coding Challenge" problem from LeetCode, asks an OpenAI-compatible LLM to write a clean, efficient Python solution for it, and emails the problem description and solution directly to your inbox.

No servers to maintain — it uses GitHub Actions' built-in cron scheduler!

## Features

- **Automated Fetching**: Retrieves the daily LeetCode challenge using their GraphQL API.
- **AI Solution Generation**: Leverages Google's Gemini API to generate efficient, well-documented Python solutions.
- **Auto-Submit to LeetCode**: Automatically submits the AI-generated code directly to your LeetCode account.
- **Email Delivery**: Uses standard SMTP to email you the daily problem, the AI's generated solution, and whether it was *Accepted* or *Failed*.
- **Serverless**: Entirely scheduled and run through GitHub Actions.

## Setup Instructions

### 1. Repository Setup
Push this code to your own GitHub repository.

### 2. Configure GitHub Secrets
Go to your repository settings on GitHub: **Settings** → **Secrets and variables** → **Actions** → **New repository secret**.

You need to add the following secrets:

| Secret Name | Description |
|---|---|
| `GEMINI_API_KEY` | Your Gemini API key from Google AI Studio. |
| `EMAIL_SENDER` | The Gmail address sending the emails. |
| `EMAIL_APP_PASSWORD` | A 16-character Google App Password (do not use your regular password). |
| `EMAIL_RECIPIENT` | The email address where you want to receive the solutions. |
| `LEETCODE_SESSION` | Your LeetCode session cookie (grab from your browser). |
| `LEETCODE_CSRF` | Your LeetCode `csrftoken` cookie (grab from your browser). |

*(Optional)* You can also add `GEMINI_MODEL` as an **Actions Variable** (under **Variables** tab next to Secrets) to specify the model name (defaults to `gemini-2.5-flash`).

### 3. How to get a Gmail App Password
1. Go to [Google Account Security](https://myaccount.google.com/security).
2. Ensure **2-Step Verification** is enabled.
3. Search for "App passwords".
4. Select App: "Mail", Device: "Other" (Name it "LeetCode Bot" or similar).
5. Click **Generate** and use the 16-character password provided as your `EMAIL_APP_PASSWORD`.

### 4. Testing
You don't have to wait until the scheduled time to test it:
1. Go to the **Actions** tab in your GitHub repository.
2. Click on the **Daily LeetCode Solver** workflow on the left sidebar.
3. Click the **Run workflow** dropdown and hit the green **Run workflow** button to test it immediately.

## Adjusting the Schedule
By default, the script runs every day at 6:25 AM IST (which is `55 0 * * *` in UTC time). If you want to change the delivery time, edit the cron expression inside `.github/workflows/daily-leetcode.yml`. Keep in mind that GitHub Actions runs on UTC time.
