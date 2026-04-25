"""RAG pipeline for PawPal+: retrieves pet care docs then queries Gemini."""

import logging
import os
import re
import time
from pathlib import Path
from typing import List, Tuple

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

# --------------------------------------------------------------------------- #
# Logging — all RAG activity written to pawpal.log                            #
# --------------------------------------------------------------------------- #
logging.basicConfig(
    filename="pawpal.log",
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

KB_DIR = Path(__file__).parent.parent / "knowledge_base"

STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "must", "can", "to", "of", "in", "for",
    "on", "with", "at", "by", "from", "and", "or", "but", "not", "my",
    "i", "it", "its", "this", "that", "how", "what", "when", "where",
    "which", "who", "why", "often", "should", "need", "give",
}


# --------------------------------------------------------------------------- #
# Document loading                                                             #
# --------------------------------------------------------------------------- #

def _load_documents() -> List[dict]:
    """Split every knowledge-base markdown file into per-section chunks."""
    docs: List[dict] = []
    if not KB_DIR.exists():
        logger.warning("knowledge_base/ directory not found at %s", KB_DIR)
        return docs

    for path in sorted(KB_DIR.glob("*.md")):
        raw = path.read_text(encoding="utf-8")
        # Split on level-2 headers (## ...) while keeping the header text
        parts = re.split(r"\n(?=## )", raw)
        for part in parts:
            part = part.strip()
            if part:
                docs.append({"source": path.stem, "content": part})

    logger.info("Loaded %d chunks from %d knowledge-base files", len(docs), len(list(KB_DIR.glob("*.md"))))
    return docs


# --------------------------------------------------------------------------- #
# Retrieval                                                                    #
# --------------------------------------------------------------------------- #

def _score(chunk: str, query: str) -> float:
    """Keyword overlap score, ignoring stopwords."""
    def keywords(text: str) -> set:
        return {w for w in re.findall(r"[a-z]+", text.lower()) if w not in STOPWORDS}

    q_words = keywords(query)
    if not q_words:
        return 0.0
    c_words = keywords(chunk)
    return len(q_words & c_words) / len(q_words)


def retrieve(query: str, top_k: int = 2) -> List[dict]:
    """Return the top-k most relevant document chunks for a query."""
    docs = _load_documents()
    scored = sorted(docs, key=lambda d: _score(d["content"], query), reverse=True)
    top = [d for d in scored[:top_k] if _score(d["content"], query) > 0]

    logger.info(
        "Retrieval | query='%s' | returned %d chunk(s): %s",
        query[:80],
        len(top),
        [d["source"] for d in top],
    )
    return top


# --------------------------------------------------------------------------- #
# Generation                                                                   #
# --------------------------------------------------------------------------- #

SYSTEM_PROMPT = (
    "You are PawPal+, a knowledgeable and friendly pet care assistant. "
    "Answer the user's question using ONLY the reference documents provided below. "
    "If the documents do not contain enough information to answer confidently, say so clearly "
    "and recommend consulting a licensed veterinarian. "
    "Be concise, practical, and use bullet points where helpful."
)


def ask(query: str, pet_context: str = "") -> Tuple[str, List[dict]]:
    """Run the full RAG pipeline: retrieve → build prompt → call Gemini.

    Returns:
        (answer_text, retrieved_chunks)

    Raises:
        EnvironmentError: if GOOGLE_API_KEY is not set.
    """
    api_key = os.environ.get("GOOGLE_API_KEY", "").strip()
    if not api_key:
        raise EnvironmentError("GOOGLE_API_KEY environment variable is not set.")

    chunks = retrieve(query)

    CHUNK_LIMIT = 800  # chars per chunk — keeps prompt small on free tier
    if chunks:
        context_block = "\n\n---\n\n".join(
            f"[Source: {c['source']}]\n{c['content'][:CHUNK_LIMIT]}" for c in chunks
        )
    else:
        context_block = "No relevant documents were found in the knowledge base."

    pet_line = f"The owner's pets: {pet_context}\n\n" if pet_context else ""

    user_message = (
        f"Reference documents:\n{context_block}\n\n"
        f"{pet_line}"
        f"Question: {query}"
    )

    logger.info("Gemini API call (gemini-2.0-flash-lite) | query='%s'", query[:80])

    client = genai.Client(api_key=api_key)
    max_retries = 4
    delay = 5  # seconds; doubles on each retry
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model="gemini-2.0-flash-lite",
                contents=user_message,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    max_output_tokens=600,
                ),
            )
            answer: str = response.text
            logger.info(
                "Gemini API success | %d input tokens, %d output tokens",
                response.usage_metadata.prompt_token_count,
                response.usage_metadata.candidates_token_count,
            )
            return answer, chunks
        except Exception as exc:
            is_rate_limit = "429" in str(exc) or "Resource" in str(exc) or "quota" in str(exc).lower()
            if is_rate_limit and attempt < max_retries - 1:
                logger.warning("Rate limit hit (attempt %d/%d), retrying in %ds", attempt + 1, max_retries, delay)
                time.sleep(delay)
                delay *= 2
            else:
                logger.error("Gemini API error: %s", exc)
                raise
