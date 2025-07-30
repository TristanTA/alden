# alden.py
import feedparser
import openai
import os
import smtplib
import requests
from bs4 import BeautifulSoup
from email.mime.text import MIMEText
from dotenv import load_dotenv
load_dotenv()


client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# --- Load secrets from environment ---
openai.api_key = os.getenv("OPENAI_API_KEY")
email_user = os.getenv("EMAIL_USER")
email_pass = os.getenv("EMAIL_PASS")
email_to = os.getenv("EMAIL_TO")

# --- Fetch top news ---
feed_url = "https://feeds.npr.org/1001/rss.xml"
feed = feedparser.parse(feed_url)

def get_full_article_text(url):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        paragraphs = soup.find_all("p")
        text = "\n".join(p.get_text() for p in paragraphs)
        return text.strip()
    except Exception as e:
        print(f"⚠️ Failed to fetch full article from {url}: {e}")
        return None

articles = []

for entry in feed.entries[:5]:
    title = entry.title
    print(f"🔍 Fetching: {title}")
    
    full_text = get_full_article_text(entry.link)
    if not full_text or len(full_text) < 300:
        print("⚠️ Using RSS summary instead.")
        full_text = BeautifulSoup(entry.summary, "html.parser").get_text()  # clean HTML tags

    articles.append(f"Title: {title}\nContent: {full_text[:1000]}")

prompt = f"Alden, summarize the following news in clear, calm language with 3-5 concise bullet points:\n\n" + "\n\n".join(articles)

# --- Debugging output ---
print("\nAlden INPUT:\n" + prompt[:2000])


# --- Summarize via GPT-4o ---
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": prompt}],
    max_tokens=500
)

summary = response.choices[0].message.content.strip()

print("\nAlden OUTPUT:\n" + summary[:2000])

# --- Email it ---
msg = MIMEText(summary)
msg['Subject'] = "Your Daily Briefing – Alden"
msg['From'] = email_user
msg['To'] = email_to

with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
    server.login(email_user, email_pass)
    server.sendmail(email_user, email_to, msg.as_string())

print("✅ Alden has delivered your summary.")
