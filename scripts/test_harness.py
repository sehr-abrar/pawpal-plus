"""RAG retrieval test harness — evaluates PawPal+ retrieval reliability.

Runs predefined queries through the retriever and checks that the expected
knowledge-base source appears in the top results. No API call is made.

Usage:
    python3 scripts/test_harness.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.rag import retrieve

TESTS = [
    {
        "description": "Dog feeding frequency",
        "query": "how often should I feed my dog",
        "expected_source": "dogs",
    },
    {
        "description": "Cat vaccination schedule",
        "query": "what vaccines does my cat need",
        "expected_source": "cats",
    },
    {
        "description": "Rabbit emergency signs",
        "query": "rabbit not eating emergency gi stasis",
        "expected_source": "rabbits",
    },
    {
        "description": "Bird grooming and nail care",
        "query": "bird nail trim grooming how often",
        "expected_source": "birds",
    },
    {
        "description": "General flea medication schedule",
        "query": "flea tick prevention monthly medication topical",
        "expected_source": "general",
    },
    {
        "description": "Dog exercise walk duration",
        "query": "how long should I walk my dog exercise breed",
        "expected_source": "dogs",
    },
]


def run():
    passed = 0
    failed = 0
    results = []

    print("=" * 62)
    print("  PawPal+ RAG Retrieval Test Harness")
    print("=" * 62)

    for i, test in enumerate(TESTS, 1):
        chunks = retrieve(test["query"])
        sources = [c["source"] for c in chunks]
        ok = test["expected_source"] in sources
        status = "PASS" if ok else "FAIL"
        passed += ok
        failed += not ok

        results.append((status, test["description"], test["expected_source"], sources))
        print(f"  [{status}]  {test['description']}")
        print(f"         Query    : {test['query']}")
        print(f"         Expected : {test['expected_source']}")
        print(f"         Got      : {sources}")
        print()

    total = passed + failed
    score = passed / total

    print("=" * 62)
    print(f"  Result : {passed}/{total} passed")
    print(f"  Score  : {score:.0%} retrieval accuracy")
    if score == 1.0:
        print("  Status : ALL TESTS PASSED")
    elif score >= 0.8:
        print("  Status : MOSTLY PASSING — review failed cases")
    else:
        print("  Status : NEEDS ATTENTION — retrieval may be misconfigured")
    print()
    print("  Note: keyword overlap has no stemming; 'dog' will not match 'dogs'.")
    print("  Known limitation — semantic/embedding search would improve recall.")
    print("=" * 62)

    return passed, failed


if __name__ == "__main__":
    passed, failed = run()
    sys.exit(0 if passed / len(TESTS) >= 0.8 else 1)
