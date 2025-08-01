import feedparser
from urllib.parse import urlparse
import os
import json
import time
import requests
from bs4 import BeautifulSoup

FEEDBACK_URL = os.getenv("FEEDBACK_URL", "https://alden-feedback.example.com/feedback")

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


def choose_relevant_articles(articles, feedback):
    from openai import OpenAI
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    source_weights = feedback.get("sources", {})
    keyword_weights = feedback.get("keywords", {})

    source_prefs = ", ".join([f"{k}: {v}" for k, v in source_weights.items()])
    keyword_prefs = ", ".join([f"{k}: {v}" for k, v in keyword_weights.items()])

    headline_list = "\n".join([f"- {a['title']} (source: {a['source']}) [link: {a['link']}]" for a in articles])

    prompt = f"""
You are Alden, a savvy and slightly cheeky assistant who helps a human stay informed without drowning in noise.
They want:
1. Personalized news that aligns with their preferences.
2. A mix of fresh or opposing viewpoints to escape the echo chamber.
3. Wit and conciseness, not boredom.

Preferences:
Sources: {source_prefs}
Keywords: {keyword_prefs}

Today's headlines:
{headline_list}

Pick 5–8 headlines for Alden to summarize. Choose based on relevance AND diversity.
Return only the exact URLs, one per line. No commentary.
"""
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=500
    )
    chosen_text = response.choices[0].message.content.strip()
    selected_links = [line.strip() for line in chosen_text.split("\n") if line.strip()]
    return selected_links


def get_article_content(url):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        paragraphs = soup.find_all("p")
        return "\n".join(p.get_text() for p in paragraphs[:10]).strip()
    except requests.exceptions.HTTPError as e:
        print(f"HTTP error fetching article: {url} – {e}")
        if e.response.status_code == 420:
            print("⚠️ Reddit rate-limited us. Skipping.")
        return ""
    except Exception as e:
        print(f"General error fetching article content from {url}: {e}")
        return ""


def summarize_articles(articles):
    from openai import OpenAI
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    summaries = []
    for article in articles:
        content = get_article_content(article["link"])
        if not content:
            continue

        prompt = f"""
You are Alden, a smart and entertaining assistant.
Summarize this article clearly in:
- A one-line TL;DR at the top
- 2–4 bullet points after that
- Keep it brief, insightful, and just snarky enough

End with a final note: “Why it matters.”

Title: {article['title']}

{content}
"""

        for attempt in range(3):
            try:
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=400
                )
                summary = response.choices[0].message.content.strip()
                summaries.append({
                    "title": article["title"],
                    "summary": summary,
                    "link": article["link"],
                    "category": article["category"],
                    "source": article["source"]
                })
                print(f"✅ Summarized: {article['title']}")
                break
            except Exception as e:
                print(f"❌ Failed to summarize article: {article['title']}: {e}")
                if "rate_limit_exceeded" in str(e) or "429" in str(e):
                    wait = 3 + attempt
                    print(f"⏳ Rate limit hit. Retrying in {wait}s...")
                    time.sleep(wait)
                else:
                    break
    return summaries


def generate_email_html(summaries):
    import random
    TAGLINES = [
        "Your inbox’s least annoying briefing.",
        "While others doomscroll, you just… know things.",
        "Coffee’s hot. The world’s not calm. Let’s begin.",
        "News. Filtered. For people who think.",
    ]
    tagline = random.choice(TAGLINES)

    html = f"""
    <html><body style='font-family:sans-serif; max-width:700px; margin:auto;'>
    <h2 style='color:#2b2b2b;'>🧠 Alden's Daily Brief</h2>
    <p>{tagline}</p><hr>
    """
    for i, summary in enumerate(summaries):
        title = summary['title']
        content = summary['summary'].replace('\n', '<br>')
        link = summary['link']
        feedback_up = f"{FEEDBACK_URL}?article={i}&vote=up"
        feedback_down = f"{FEEDBACK_URL}?article={i}&vote=down"

        html += f"""
        <div style='margin-bottom:30px;'>
            <h3 style='color:#003366;'>{title}</h3>
            <p>{content}</p>
            <p><a href='{link}'>Read full story</a></p>
            <p style='font-size:small;'>Was this summary helpful?</p>
            <p>
                <a href='{feedback_up}' target="_blank">👍</a>
                <a href='{feedback_down}' target="_blank">👎</a>
            </p>
        </div>
        """

    html += "<hr><p style='text-align:center; font-style:italic;'>Another day, another download of human happenings. Alden out. 🛰️</p></body></html>"
    return html