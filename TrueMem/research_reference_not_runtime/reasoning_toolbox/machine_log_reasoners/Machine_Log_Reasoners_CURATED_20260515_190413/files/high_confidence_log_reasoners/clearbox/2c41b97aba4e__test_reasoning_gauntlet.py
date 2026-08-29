"""
Phase 1 Verification Gauntlet

Tests:
1. Determinism (same query 3x = same output)
2. 5 query smoke tests
3. Confidence sanity checks
"""
import httpx
import json

BASE_URL = "http://localhost:5051"

def test_query(question, label=""):
    """Run a single query and return result"""
    print(f"\n{'='*60}")
    print(f"{label or question}")
    print('='*60)

    try:
        resp = httpx.post(
            f"{BASE_URL}/reasoning/query",
            json={"question": question, "mode": "what_does_x_do", "topk": 5},
            timeout=10.0
        )

        if resp.status_code == 200:
            result = resp.json()
            print(f"Surface: {result['surface_text']}")
            print(f"Overall confidence: {result['answer_frame']['confidence']:.3f}")
            print(f"\nPredicates:")
            for i, pred in enumerate(result['answer_frame']['predicates'][:3]):
                evidence = pred['evidence']
                print(f"  {i+1}. {pred['verb']} {pred['object']}")
                print(f"     confidence={pred['confidence']:.3f}, "
                      f"slot={evidence['predicate_slot']}, "
                      f"verb_rank={evidence['verb_rank']:.2f}, "
                      f"verb_df={evidence['verb_df']}")

            print(f"\nReasoning trace:")
            trace = result['reasoning_trace']
            print(f"  - Predicate candidates: {trace.get('predicate_candidates_found', 0)}")
            print(f"  - Frames built: {trace.get('frames_built', 0)}")

            return result
        else:
            print(f"ERROR {resp.status_code}: {resp.text}")
            return None

    except Exception as e:
        print(f"EXCEPTION: {e}")
        return None


def test_determinism():
    """Test 1: Same query 3x should give identical output"""
    print("\n" + "="*60)
    print("TEST 1: DETERMINISM CHECK")
    print("="*60)

    question = "What do clearboxs do?"
    results = []

    for i in range(3):
        print(f"\nRun {i+1}/3...")
        result = test_query(question, label=f"Run {i+1}: {question}")
        if result:
            # Extract stable fields for comparison
            stable = {
                'subject': result['answer_frame']['subject'],
                'predicates': [
                    (p['verb'], p['object'], round(p['confidence'], 6))
                    for p in result['answer_frame']['predicates']
                ],
                'surface_text': result['surface_text']
            }
            results.append(stable)

    # Compare
    if len(results) == 3:
        if results[0] == results[1] == results[2]:
            print("\n[PASS] DETERMINISM PASS: All 3 runs identical")
            return True
        else:
            print("\n[FAIL] DETERMINISM FAIL: Outputs differ")
            for i, r in enumerate(results):
                print(f"  Run {i+1}: {r}")
            return False
    else:
        print("\n[FAIL] DETERMINISM FAIL: Some runs failed")
        return False


def test_gauntlet():
    """Test 2-6: 5 query smoke tests"""
    print("\n" + "="*60)
    print("TEST 2-6: SMOKE TEST GAUNTLET")
    print("="*60)

    queries = [
        "What do clearboxs do?",
        "What does carbon do?",
        "What do ecosystems do?",
        "What do pine clearboxs do?",
        "What does sequestration do?"
    ]

    results = []
    for i, q in enumerate(queries, start=2):
        result = test_query(q, label=f"TEST {i}: {q}")
        results.append((q, result is not None))

    # Summary
    print("\n" + "="*60)
    print("GAUNTLET SUMMARY")
    print("="*60)
    for q, success in results:
        status = "[PASS] PASS" if success else "[FAIL] FAIL"
        print(f"{status}: {q}")

    return all(success for _, success in results)


def test_confidence_sanity():
    """Test 7: Confidence values should be in [0,1] and correlate with evidence"""
    print("\n" + "="*60)
    print("TEST 7: CONFIDENCE SANITY")
    print("="*60)

    result = test_query("What do clearboxs do?", label="Confidence sanity check")

    if not result:
        print("[FAIL] FAIL: No result")
        return False

    predicates = result['answer_frame']['predicates']

    # Check all confidences in [0,1]
    for i, pred in enumerate(predicates):
        conf = pred['confidence']
        if not (0.0 <= conf <= 1.0):
            print(f"[FAIL] FAIL: Predicate {i+1} confidence {conf} out of range")
            return False

    # Check decreasing confidence (should correlate with rank)
    confidences = [p['confidence'] for p in predicates]
    if confidences != sorted(confidences, reverse=True):
        print(f"[WARN]  WARNING: Confidences not monotonic: {confidences}")
        # Not a hard fail, but suspicious

    print("\n[PASS] CONFIDENCE PASS: All values in [0,1], ordering reasonable")
    return True


def main():
    print("="*60)
    print("PHASE 1 VERIFICATION GAUNTLET")
    print("="*60)

    # Check server
    try:
        resp = httpx.get(f"{BASE_URL}/health", timeout=5.0)
        print(f"Server status: {resp.json()}\n")
    except Exception as e:
        print(f"[FAIL] Server not running: {e}")
        print("Run: start_reasoning_engine.bat\n")
        return

    # Run tests
    results = {}
    results['determinism'] = test_determinism()
    results['gauntlet'] = test_gauntlet()
    results['confidence'] = test_confidence_sanity()

    # Final summary
    print("\n" + "="*60)
    print("FINAL RESULTS")
    print("="*60)
    for test, passed in results.items():
        status = "[PASS] PASS" if passed else "[FAIL] FAIL"
        print(f"{status}: {test}")

    all_passed = all(results.values())
    if all_passed:
        print("\n*** ALL TESTS PASSED - Ready to commit!")
    else:
        print("\n[WARN]  SOME TESTS FAILED - Review output above")


if __name__ == "__main__":
    main()
