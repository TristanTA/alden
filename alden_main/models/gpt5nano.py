# gpt5nano_model.py
from __future__ import annotations
from typing import List, Dict, Any
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

def run_gpt5nano(messages: List[Dict[str, str]], *, debug: bool = False) -> str:
    """
    Minimal wrapper for GPT-5-nano.
    Accepts a messages list, returns raw model output (string).
    """
    if debug:
        print(f"[GPT5-NANO] Messages: {messages}")

    # ---- LIVE CALL----
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY_5NANO"))
    resp = client.chat.completions.create(
        model="gpt-5-nano",
        messages=messages
    )
    output_text = resp.choices[0].message.content
    return output_text