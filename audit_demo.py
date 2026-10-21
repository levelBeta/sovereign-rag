"""Audit tamper demo for Sovereign RAG. ALL DATA IS SYNTHETIC.
Writes 4 pipeline entries to a temp log, edits entry 2, and shows the break cascade."""
import json
import os
import tempfile
import agent
import audit


def main():
    col, chunks = agent.build()
    path = os.path.join(tempfile.mkdtemp(), "audit_demo.jsonl")
    for q in ("What is the capital of France?", "Who won the football grand final?",
              "What is on the cafeteria lunch menu?", "How do I bake sourdough bread?"):
        agent.analyse(col, chunks, q, "analyst", audit_path=path)
    print("before tamper:", audit.verify(path))
    lines = open(path, encoding="utf-8").read().splitlines()
    entry = json.loads(lines[1])
    entry["data"]["status"] = "answered"
    lines[1] = json.dumps(entry, sort_keys=True)
    open(path, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
    print("after editing entry 2:", audit.verify(path))


if __name__ == "__main__":
    main()
