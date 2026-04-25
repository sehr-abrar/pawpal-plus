# Model Card — PawPal+ Pet Care Assistant

## System Overview

PawPal+ uses Retrieval-Augmented Generation to answer pet care questions. A keyword-based retriever selects the 2 most relevant sections from a local knowledge base of 28 pet care document sections, then passes them as grounded context to Gemini 2.0 Flash Lite to generate an answer. The model is explicitly instructed to answer only from the retrieved documents and to recommend consulting a veterinarian when the documents are insufficient.

---

## 1. System Design

### Original Architecture

I designed four classes with clear, separated responsibilities:

- **Task** (dataclass) — a single care activity. Holds the what (`description`), when (`time`, `due_date`), how long (`duration_minutes`), importance (`priority`), and cadence (`frequency`). Keeps its own `completed` flag and one method: `mark_complete()`.
- **Pet** (dataclass) — a named animal. Owns a list of `Task` objects and provides `add_task`/`remove_task` helpers so the rest of the system never directly mutates `pet.tasks`.
- **Owner** — manages a roster of `Pet` objects. `get_all_tasks()` aggregates every task across every pet and is the primary entry point for the Scheduler.
- **Scheduler** — the algorithmic brain. Provides sorting, filtering, conflict detection, recurring-task generation, and today's schedule. Keeping this logic out of `Owner` and `Pet` follows the single-responsibility principle and makes the scheduler easy to test in isolation.

### Key Design Change

An early design placed recurrence logic inside `Task.mark_complete()`, requiring a `Task` to know which `Pet` it belonged to — a circular dependency. Moving recurrence into `Scheduler.mark_task_complete()` kept `Task` a pure data object and gave the Scheduler exclusive control over side effects.

### RAG Extension Design

The RAG pipeline was added as a fully separate module (`src/rag.py`) with no dependency on the scheduler. This means the original 19 tests pass unchanged and the AI layer can be swapped without touching the scheduling logic.

---

## 2. Limitations and Biases

**Retrieval quality:** The retriever uses keyword overlap, not semantic similarity. It can miss relevant content if the user's vocabulary differs from the knowledge base (e.g., "jab" won't match "vaccine"). Uncommon questions that use different terminology may return low-relevance chunks.

**Knowledge base scope:** The knowledge base covers only dogs, cats, rabbits, and birds. Questions about reptiles, fish, guinea pigs, or exotic pets will return no relevant results and the AI will say so. Documents reflect general best practices as of their writing date and may not reflect the latest veterinary guidelines.

**No medical authority:** The system is informational only. It is biased toward general population advice (e.g., "feed twice a day") and cannot account for individual health conditions, breed-specific variations, or a specific vet's instructions.

**Model limitations:** Gemini 2.0 Flash Lite is a small, fast model optimized for low cost. It occasionally adds details not present in the source documents. The system prompt instructs it to stay within the provided documents, but this is not perfectly enforceable.

**Free-tier reliability:** The Google AI free tier enforces strict rate limits (15 requests/minute). High usage can cause 429 errors even with retry logic, temporarily making the assistant unavailable.

---

## 3. Potential Misuse and Safeguards

**Risk:** A user follows AI-generated advice for a sick pet instead of calling a vet, causing harm through delayed treatment.

**Safeguards built in:**
- The system prompt explicitly instructs the model: *"If the documents do not contain enough information to answer confidently, say so clearly and recommend consulting a licensed veterinarian."*
- Retrieved source documents are shown under every answer so the user can read the original material and verify before acting.
- The knowledge base itself consistently includes "consult a vet" language for anything beyond routine care.

**Risk:** The knowledge base contains incorrect information that the AI presents confidently.

**Safeguard:** All knowledge-base documents are human-authored from established pet care guidelines. The retriever returns the raw source text alongside every answer so users can cross-reference it. The system does not generate knowledge-base content dynamically.

**What is not mitigated:** There is no persistent UI disclaimer reminding users this is not veterinary advice. Adding a banner would be a meaningful improvement for a production system.

---

## 4. Testing and Reliability

### What Was Tested

- **19 automated pytest tests** covering the full scheduler — task completion, recurrence, sorting, filtering, conflict detection, and today's schedule logic. All pass.
- **RAG retrieval test harness** (`scripts/test_harness.py`): 6 predefined queries with expected source documents, verifying the retriever returns relevant chunks without requiring any API call.
- **Manual end-to-end testing:** 10+ questions through the Streamlit UI across all five knowledge-base files, verifying answers were grounded in retrieved sources and that the model recommended vet consultation when context was thin.

### Confidence Rating: ★★★★☆

Core scheduling and retrieval behaviors are well covered. The test harness does not evaluate LLM generation quality — that remains a manual review step. A future improvement would be a human-evaluation rubric scoring each answer for accuracy, groundedness, and appropriateness.

### What Surprised Me During Testing

The most surprising finding was how much **chunk size affected API quota** rather than request count. Sending three full knowledge-base sections per query was consuming 3,000+ tokens per request and hitting the daily token limit before the per-minute request limit. Truncating each chunk to 800 characters reduced token consumption by ~70% and resolved most quota exhaustion without meaningfully degrading answer quality.

The second surprise was **model availability inconsistency**: `gemini-1.5-flash` is widely documented as free-tier available, but returned a 404 for this account. Listing available models programmatically was necessary — documentation alone was not reliable.

---

## 5. AI Collaboration

### How AI Was Used

AI assisted at every stage: designing class responsibilities, scaffolding dataclass stubs, proposing the `sorted(tasks, key=lambda t: t.time)` sorting pattern, drafting initial pytest functions, and writing the retry/backoff logic for rate limiting. The most useful prompt pattern was framing questions as design decisions ("which class should own recurrence logic, and why?") rather than code requests.

### One Helpful Suggestion

When the app was returning 429 errors, AI suggested implementing **exponential backoff retry logic** — starting at a 5-second delay and doubling on each retry up to four attempts. This was the right call: it resolved transient rate limit errors without overwhelming the API, and the Streamlit spinner keeps the UI intact while retrying. The suggestion came with a clean, directly usable implementation.

### One Flawed Suggestion

AI recommended using `gemini-1.5-flash` as the model, describing it as the most stable free-tier option. This was incorrect — the model returned a 404 NOT_FOUND error at runtime. The correct fix required writing a script to call `client.models.list()` and check which models were actually available for this API key. The AI's suggestion was based on general documentation rather than verified availability for this specific account and region.

**Lesson:** AI suggestions about external service availability should always be verified against the live API. Trusting documentation without runtime verification is a reliability risk.

### Key Takeaway

AI accelerates implementation but is a poor architect and an unreliable source of truth for external service behavior. The AI was most valuable when I had already decided *what* to build and needed the *how* produced quickly. Judgment about design, correctness, and real-world constraints remained entirely a human responsibility.

---

## 6. Scheduling Logic Tradeoffs

**Conflict detection** uses exact `HH:MM` string matching. A more sophisticated approach would compare time ranges (`[start, start + duration]`) so overlapping tasks are also flagged. Exact-match was chosen for simplicity and correctness within the project scope.

**Retrieval scoring** is O(n) over all chunks on every query — fine for 28 sections, would not scale to thousands of documents. A vector index (e.g., FAISS) is the appropriate upgrade path.

**Priority** is a filter but does not reorder tasks within the same time slot. A fully priority-aware scheduler would use it as a secondary sort key.
