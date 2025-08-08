# alden.py
from email.mime.text import MIMEText
import smtplib
import feeds

from dotenv import load_dotenv
import os, smtplib, ssl
from email.mime.text import MIMEText

load_dotenv()

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))
# Support both SMTP_* and EMAIL_* names
email_user = os.getenv("SMTP_USER") or os.getenv("EMAIL_USER")
email_pass = os.getenv("SMTP_PASS") or os.getenv("EMAIL_PASS")
email_to   = os.getenv("TO_EMAIL")  or os.getenv("EMAIL_TO")
email_from = os.getenv("FROM_EMAIL", email_user)

assert email_user, "Missing SMTP_USER/EMAIL_USER"
assert email_pass, "Missing SMTP_PASS/EMAIL_PASS"
assert email_to,   "Missing TO_EMAIL/EMAIL_TO"

# Step 1: Get all articles
articles = feeds.get_all_titles()
print(f"✅ Fetched {len(articles)} articles")

# Step 2: Load feedback and pick relevant article links
feedback = feeds.load_feedback()
print(f"Loaded feedback with {len(feedback['sources'])} sources and {len(feedback['keywords'])} keywords.")

selected_links = feeds.choose_relevant_articles(articles, feedback)
print(f"🧠 GPT selected {len(selected_links)} article links for summarization.")

# Step 3: Match selected articles by link
selected_articles = [a for a in articles if a["link"] in selected_links]
print(f"🔍 Matched {len(selected_articles)} articles from fetched list.")

# Step 4: Summarize selected articles
summaries = feeds.summarize_articles(selected_articles)
print(f"📝 Generated {len(summaries)} summaries.")

# Step 5: Generate styled HTML
html_content = feeds.generate_email_html(summaries)
print("📨 Generated email HTML.")

# Step 6: Send email
msg = MIMEText(html_content, "html")
msg["Subject"] = "Your Daily Briefing – Alden"
msg["From"] = email_from
msg["To"] = email_to

context = ssl.create_default_context()
with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=context) as server:
    server.login(email_user, email_pass)
    server.send_message(msg)

print("✅ Alden has delivered your stylish summary.")