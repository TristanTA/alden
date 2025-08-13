# alden/feedback_server.py

from flask import Flask, request, jsonify
from feedback_handler import handle_feedback_url, load_feedback
from feeds import get_all_titles

app = Flask(__name__)

# Cache latest articles to use in feedback reference
LATEST_ARTICLES = get_all_titles()

@app.route("/feedback", methods=["GET"])
def feedback():
    feedback_url = request.url
    try:
        handle_feedback_url(feedback_url, LATEST_ARTICLES)
        return jsonify({"status": "success"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
