# alden.py
import os
from dotenv import load_dotenv
from email.mime.text import MIMEText
import smtplib
import feeds

load_dotenv()

# Load secrets
openai_key = os.getenv("OPENAI_API_KEY")
email_user = os.getenv("EMAIL_USER")
email_pass = os.getenv("EMAIL_PASS")
email_to = os.getenv("EMAIL_TO")

# Step 1: Get all articles
articles = feeds.get_all_titles()
print(f"✅ Fetched {len(articles)} articles")

# Step 2: Load feedback and pick relevant articles
feedback = feeds.load_feedback()
selected_titles = feeds.choose_relevant_articles(articles, feedback)
selected_articles = [a for a in articles if a["title"] in selected_titles]

# Step 3: Summarize selected articles
summaries = feeds.summarize_articles(selected_articles)

# Step 4: Generate styled HTML
html_content = feeds.generate_email_html(summaries)

# Step 5: Send email
msg = MIMEText(html_content, "html")
msg['Subject'] = "Your Daily Briefing – Alden"
msg['From'] = email_user
msg['To'] = email_to

with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
    server.login(email_user, email_pass)
    server.sendmail(email_user, email_to, msg.as_string())

print("✅ Alden has delivered your stylish summary.")