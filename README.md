# Sovereign RAG

A local question-answering prototype over synthetic policy documents. It answers only when every claim is backed by a verified citation, enforces role-based access at retrieval, and refuses otherwise. It runs on one machine with a local model server (Ollama) and a local vector store (Chroma). All data is synthetic and written for this project.

## Why it exists

Many RAG demos show a model answering from documents. This one shows the controls around the model: access control, citation checking, refusal and an audit trail. Many controls were tested by breaking them on purpose and watching a test or the eval fail: chunk count, TFN checksum, role flags, the in-code role re-check, verbatim quotes, number checks, the verification gate, label mapping, the confidence gate and the eval itself. Not every control was break-tested: Medicare and card checksums, the retrieved-only check and the role-permission check inside the verifier have passing tests but no break test.

## What it checks

Detection and access decisions are deterministic code. The model only drafts a cited answer.

- PII redaction on the query first (email, AU phone, TFN, Medicare, card). TFN, Medicare and card matches are checksum-validated. Only counts are logged, never values.
- Role-filtered retrieval (analyst, manager, ciso). The filter runs inside the vector query, and every hit is re-checked in code.
- Hybrid retrieval: BM25 plus vector search, fused with reciprocal rank fusion.
- Confidence gate: refuse when the best vector distance is above 0.45.
- Citation-or-refuse: each citation must be a retrieved, role-permitted passage with a verbatim quote, and every number in the answer must appear in the cited text.
- One retry that tells the model why it was rejected, then a labelled refusal.

## Architecture

- Question
- -> PII redaction
- -> hybrid retrieval, filtered by role, then re-checked in code
- -> confidence gate
- -> local model drafts a cited answer (passages are labelled P1, P2, ...)
- -> code maps each label back to a chunk ID
- -> verifier (retrieved, permitted, verbatim quote, numbers)
- -> answer, or a labelled refusal
- -> hash-chained audit entry, with a process-scoped sovereignty check around the whole call

Modules: chunker.py, pii.py, vstore.py, retrieval.py, answer.py, verify.py, agent.py, audit.py, sovereignty.py, app.py (Streamlit UI), eval.py, audit_demo.py.

## Corpus

13 synthetic documents (6 public, 4 internal, 3 restricted), split into 49 chunks with stable IDs such as syn-doc-001#02. Each chunk carries its classification and the roles allowed to read it. One public document contains an injected instruction and a canary string, used to test prompt injection.

## Governance

- Audit log: hash-chained JSONL. Each entry stores the role, model, PII counts, retrieved and filtered chunk IDs, best distance, status, cited IDs and the sovereignty result. It never stores the question text or matched values. `python audit_demo.py` writes 4 entries, edits entry 2, and shows the break cascade: before the edit `ok: True`, after it `ok: False` with bad lines 2, 3 and 4.
- Sovereignty check: samples TCP connections of this process and its children while the work runs and reports whether any went to a non-loopback address. The claim is "no external TCP connection observed in N samples". It is not proof, it covers TCP only, it is snapshot-sampled, and it covers this process tree and not the whole machine. It was tested with a positive control: a real loopback connection is seen, and a faked external address is flagged.
- Compliance wording: nothing here is claimed to be compliant with any standard.

## Measured results (CPU only, one machine)

Eval (`python eval.py`): 25 of 25 checks passed in 73 to 91 seconds across runs. Model-dependent checks run 3 times each.

- recall@5: 8 of 8 questions, with the expected chunk ranked first every time
- role-denied: 3 of 3 cases, no restricted chunk retrieved
- answer and cite: 8 of 8 questions, 3 of 3 runs each, with the expected chunk cited
- refusals at the confidence gate: 2 of 2 questions, 3 of 3 runs
- role-denied question refused by the model: 3 of 3 runs
- PII: counts and a near-miss TFN kept
- canary with the poisoned chunk in the context: 0 leaks in 6 runs (3 on qwen2.5:3b, 3 on qwen2.5:7b)

The eval was shown to fail when the role flags were loosened (21 of 24 passed at that time), when the confidence gate was opened (23 of 25), and when one expected chunk was changed (24 of 25).

Model comparison (`python eval.py --speed`, 24 calls per model, two runs):

| Model | Seconds per call | Answered | Correct citation |
|---|---|---|---|
| llama3.2:3b | 2.3 to 2.6 | 15 of 24 | 15 |
| qwen2.5:3b | 2.5 | 24 of 24 | 24 |
| qwen2.5:7b | 4.7 to 4.9 | 24 of 24 | 24 |

qwen2.5:3b is the default. The first call per model includes load time, and the per-call time includes retrieval, retries and the sampler, not only the model.

Tests: 54 pass (`python -m pytest`).

## How to run

Requirements: Python 3.12, Ollama with `nomic-embed-text`, `qwen2.5:3b`, `qwen2.5:7b` and `llama3.2:3b` pulled.

    python -m venv .venv
    .venv\Scripts\Activate.ps1
    python -m pip install -r requirements.txt
    python eval.py
    python -m pytest
    python -m streamlit run app.py --server.address 127.0.0.1 --browser.gatherUsageStats false

Always pass `--server.address 127.0.0.1`. Without it Streamlit listens on all network interfaces.

## Limitations

This is a prototype. Read these before relying on anything above.

- The verifier proves a citation is real, permitted and verbatim, and that numbers appear in the cited text. It cannot verify that the answer reasons correctly from that text. A verbatim quote of the wrong sentence would pass.
- Prompt injection is mitigated, not solved. The prompt tells the model passages are untrusted, and the canary did not leak in 6 runs with the poisoned chunk in context (one benign question, two models). The canary did appear when a user directly asked for the secret code, because the verifier checks grounding and not intent. There is no pattern-based quarantine.
- The 0.45 distance threshold was chosen from 12 questions. One unanswerable question scored 0.4556, a margin of 0.0056. The model also declined those questions on its own when the gate was opened, so the gate and the model overlap.
- Role-denied questions that pass the gate are refused only because the model declines or the verifier rejects the answer.
- Small samples: 8 answerable questions, 2 refusal questions, one benign canary question. Speed numbers come from two runs on one CPU-only machine and are not a benchmark.
- llama3.2:3b answered 15 of 24 under the strict citation rules. qwen2.5:3b is the default.
- A 3B model sometimes shortens chunk IDs, which is why passages are cited by short labels that code maps back to IDs.
- Number checking covers digits only, not number words such as "ninety".
- PII redaction is regex-based, AU formats only, and does not detect names or addresses.
- The sovereignty check is TCP only, snapshot-sampled, covers this process tree and not the machine, and matches the process name ollama.exe, so it is Windows-specific. Chroma telemetry was set off in settings and no external connection was observed, but that is not proof. The Streamlit server itself is outside the check.
- The UI was tested by hand on four scenarios. It is not covered by automated tests.
- Chunk IDs are stable only while document lines do not move.
- The corpus is 13 short synthetic documents. Nothing here is validated at enterprise scale.
