# alden/feedback_handler.py

import json
import os
from urllib.parse import parse_qs, urlparse

FEEDBACK_FILE = os.getenv(
    "FEEDBACK_FILE",
    os.path.join(os.path.dirname(__file__), "feedback.json")
)



def load_feedback():
    if not os.path.exists(FEEDBACK_FILE):
        feedback = {"sources": {}, "keywords": {}}
        with open(FEEDBACK_FILE, "w") as f:
            json.dump(feedback, f, indent=2)
        return feedback
    with open(FEEDBACK_FILE, "r") as f:
        return json.load(f)


def save_feedback(feedback):
    with open(FEEDBACK_FILE, "w") as f:
        json.dump(feedback, f, indent=2)


def update_feedback(article, vote):
    feedback = load_feedback()

    # Boost or penalize source
    source = article.get("source")
    if source:
        feedback["sources"].setdefault(source, 0)
        feedback["sources"][source] += 1 if vote == "up" else -1

    # Boost or penalize keywords in title
    title_keywords = article["title"].lower().split()
    for kw in title_keywords:
        if len(kw) > 3:
            feedback["keywords"].setdefault(kw, 0)
            feedback["keywords"][kw] += 1 if vote == "up" else -1

    save_feedback(feedback)


def handle_feedback_url(feedback_url, articles):
    # Simulate feedback like: https://example.com/feedback?article=1&vote=up
    query = parse_qs(urlparse(feedback_url).query)
    article_index = int(query.get("article", [0])[0])
    vote = query.get("vote", ["up"])[0]

    if 0 <= article_index < len(articles):
        update_feedback(articles[article_index], vote)
        print(f"Updated feedback: article {article_index} -> {vote}")
    else:
        print("Invalid article index.")
