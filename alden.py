# alden.py
import feedparser
import openai
import os
import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv
load_dotenv()

# --- Load secrets from environment ---
openai.api_key = os.getenv("OPENAI_API_KEY")
email_user = os.getenv("EMAIL_USER")
email_pass = os.getenv("EMAIL_PASS")
email_to = os.getenv("EMAIL_TO")

# --- Fetch top news ---
feed_url = "https://feeds.reuters.com/reuters/topNews"
feed = feedparser.parse(feed_url)

articles = []
for entry in feed.entries[:5]:
    title = entry.title
    summary = entry.summary
    articles.append(f"Title: {title}\nSummary: {summary}")

prompt = f"Alden, summarize the following news in clear, calm language with 3-5 concise bullet points:\n\n" + "\n\n".join(articles)

# --- Summarize via GPT-4o ---
response = openai.ChatCompletion.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": prompt}],
    max_tokens=500
)

summary = response.choices[0].message.content.strip()

# --- Email it ---
msg = MIMEText(summary)
msg['Subject'] = "Your Daily Briefing – Alden"
msg['From'] = email_user
msg['To'] = email_to

with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
    server.login(email_user, email_pass)
    server.sendmail(email_user, email_to, msg.as_string())

print("✅ Alden has delivered your summary.")
