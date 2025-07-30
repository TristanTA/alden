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
You are Alden, a personal assistant. Your job is to select 5–8 news headlines to summarize for a user who:
1. Wants content relevant to their preferences.
2. Also values new, diverse, or opposing perspectives to avoid echo chambers.

User Preferences:
Sources: {source_prefs}
Keywords: {keyword_prefs}

Here are today’s headlines:
{headline_list}

Return ONLY the exact headlines (no summaries, no commentary) that should be summarized today.
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
Summarize the following article in 3–5 bullet points with clear context and concise tone. Include why the article might matter to the reader at the end.

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
    html = "<h2>Alden's Daily Brief</h2>"
    for i, summary in enumerate(summaries):
        title = summary['title']
        content = summary['summary'].replace('\n', '<br>')
        link = summary['link']
        html += f"""
        <div style='margin-bottom:20px;'>
            <h3>{title}</h3>
            <p>{content}</p>
            <p><a href='{link}'>Read more</a></p>
            <p>
                <a href='https://example.com/feedback?article={i}&vote=up'>👍</a>
                <a href='https://example.com/feedback?article={i}&vote=down'>👎</a>
            </p>
        </div>
        """
    html += "<hr><p style='text-align:center;'>Brief delivered. Perspective gained. Your move, universe. </p>"
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