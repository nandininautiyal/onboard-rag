import json

results = json.load(open("eval/results/eval_results.json", encoding="utf-8"))

print("=== FALSE REFUSALS (answerable but system said no) ===")
for r in results:
    if r["answerable"] and not r["grounded"]:
        print(f"Q: {r['question']}")
        print(f"  top_score: {r['top_score']}")
        print(f"  expected: {r['expected_answer']}")
        print()

print("=== HALLUCINATIONS (unanswerable but system answered) ===")
for r in results:
    if not r["answerable"] and r["grounded"]:
        print(f"Q: {r['question']}")
        print(f"  top_score: {r['top_score']}")
        print(f"  system answer: {r['system_answer']}")
        print()