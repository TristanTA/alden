# alden/feeds.py

import feedparser
from urllib.parse import urlparse
import os
import json
import openai
import requests
from bs4 import BeautifulSoup

# Define feeds by topic
RSS_FEEDS = {
    "tech": [
        "https://www.theverge.com/rss/index.xml",
        "https://techcrunch.com/tag/artificial-intelligence/feed/",
        "https://spectrum.ieee.org/rss/artificial-intelligence/fulltext",
    ],
    "space": [
        "https://www.space.com/feeds/all",
        "https://www.reddit.com/r/spacex/.rss",
        "https://www.nasa.gov/rss/dyn/breaking_news.rss"
    ],
    "elon": [
        "https://news.google.com/rss/search?q=Elon+Musk&hl=en-US&gl=US&ceid=US:en"
    ],
    "global": [
        "https://apnews.com/rss/apf-international",
        "http://feeds.bbci.co.uk/news/world/rss.xml"
    ],
    "funny": [
        "https://www.theonion.com/rss",
        "https://www.reddit.com/r/UpliftingNews/.rss",
        "https://www.goodnewsnetwork.org/feed/"
    ]
}

def get_all_titles():
    all_articles = []
    for category, urls in RSS_FEEDS.items():
        for url in urls:
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries:
                    article = {
                        "title": entry.title.strip(),
                        "link": entry.link.strip(),
                        "category": category,
                        "source": urlparse(entry.link).netloc
                    }
                    all_articles.append(article)
            except Exception as e:
                print(f"Failed to parse {url}: {e}")
    return all_articles

def load_feedback(filepath="feedback.json"):
    if not os.path.exists(filepath):
        feedback = {"sources": {}, "keywords": {}}
        with open(filepath, "w") as f:
            json.dump(feedback, f, indent=2)
        return feedback
    with open(filepath, "r") as f:
        return json.load(f)

def choose_relevant_articles(titles, feedback, openai_api_key):
    openai.api_key = openai_api_key
    source_weights = feedback.get("sources", {})
    keyword_weights = feedback.get("keywords", {})

    source_prefs = ", ".join([f"{k}: {v}" for k, v in source_weights.items()])
    keyword_prefs = ", ".join([f"{k}: {v}" for k, v in keyword_weights.items()])

    headline_list = "\n".join([f"- {a['title']} (source: {a['source']})" for a in titles])

    prompt = f"""
You are Alden, a witty, insightful assistant who delivers a news briefing each day.
Your goals:
1. Prioritize stories aligned with the user's preferences.
2. Include at least one surprising or diverse perspective to avoid echo chambers.
3. Keep it fresh. Keep it sharp.

User Preferences:
Sources: {source_prefs}
Keywords: {keyword_prefs}

Today’s headlines:
{headline_list}

Select 5–8 headlines to summarize. Return only the exact titles.
"""
    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=500
    )
    chosen_text = response.choices[0].message.content.strip()
    selected_titles = [line.strip("- ") for line in chosen_text.split("\n") if line.strip()]
    return selected_titles

def get_article_content(url):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        paragraphs = soup.find_all("p")
        return "\n".join(p.get_text() for p in paragraphs[:10]).strip()
    except Exception as e:
        print(f"Error fetching article content from {url}: {e}")
        return ""

def summarize_articles(articles, openai_api_key):
    openai.api_key = openai_api_key
    summaries = []
    for article in articles:
        content = get_article_content(article["link"])
        if not content:
            continue
        prompt = f"""
You are Alden, a clever and concise assistant summarizing today’s news.
Summarize the following article in 3–5 engaging bullet points that:
- Clearly explain what’s happening
- Add relevant context
- Mention why this matters (especially to a curious, tech-minded reader)
- Use a witty but respectful tone, not dry or robotic

Title: {article['title']}

{content}
"""
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=300
            )
            summary = response.choices[0].message.content.strip()
            summaries.append({"title": article["title"], "summary": summary, "link": article["link"]})
        except Exception as e:
            print(f"Failed to summarize article: {article['title']}: {e}")
    return summaries

def generate_email_html(summaries):
    html = """
    <html>
    <head>
        <style>
            body { font-family: 'Segoe UI', sans-serif; background: #f8f9fa; padding: 20px; color: #212529; }
            .container { max-width: 800px; margin: auto; background: #fff; border-radius: 8px; box-shadow: 0 0 10px rgba(0,0,0,0.05); padding: 20px; }
            h2 { text-align: center; color: #444; }
            .story { border-bottom: 1px solid #e0e0e0; padding-bottom: 16px; margin-bottom: 16px; }
            .story:last-child { border: none; }
            .title { font-size: 18px; font-weight: bold; }
            .summary { margin: 8px 0; line-height: 1.5; }
            .feedback { font-size: 14px; }
            .footer { text-align: center; margin-top: 30px; color: #888; font-size: 14px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h2>Alden's Daily Brief</h2>
    """
    for i, summary in enumerate(summaries):
        html += f"""
            <div class='story'>
                <div class='title'>{summary['title']}</div>
                <div class='summary'>{summary['summary'].replace('\n', '<br>')}</div>
                <div><a href='{summary['link']}'>Read more</a></div>
                <div class='feedback'>
                    <a href='https://example.com/feedback?article={i}&vote=up'>👍</a>
                    <a href='https://example.com/feedback?article={i}&vote=down'>👎</a>
                </div>
            </div>
        """
    html += """
            <div class='footer'>Brief delivered. Perspective gained. Your move, universe.</div>
        </div>
    </body>
    </html>
    """
    return html

if __name__ == "__main__":
    articles = get_all_titles()
    print(f"Fetched {len(articles)} articles.")

    feedback = load_feedback()
    selected_titles = choose_relevant_articles(articles, feedback, os.getenv("OPENAI_API_KEY"))
    selected_articles = [a for a in articles if a["title"] in selected_titles]

    summaries = summarize_articles(selected_articles, os.getenv("OPENAI_API_KEY"))
    email_html = generate_email_html(summaries)

    with open("daily_email_preview.html", "w", encoding="utf-8") as f:
        f.write(email_html)
    print("HTML email content written to daily_email_preview.html")
