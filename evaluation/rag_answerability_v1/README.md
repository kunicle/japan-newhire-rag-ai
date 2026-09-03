# RAG Evaluation Dataset v1

`RAG_EVAL_V1` is a versioned, corpus-global benchmark for evaluating retrieval ranking separately from evidence answerability.

## Version and snapshot

- Dataset version: `1.0.2`
- Created: `2026-09-03`
- Corpus snapshot date: `2026-09-03`
- Evaluation rows: 200
- Ground-truth embedding independence: labels do not depend on an embedding model
- Retrieval comparison metadata: OpenAI `text-embedding-3-small`, 1536 dimensions

The corpus contains synthetic/test policy documents only. No credentials, employee records, or confidential source text are copied into the dataset.

## Ground-truth semantics

`globalAnswerable=true` means at least one accessible document in the complete evaluation corpus explicitly contains sufficient evidence for the requested information. Direct paraphrase and simple, explicitly supported comparison are allowed.

`globalAnswerable=false` means no document in the evaluation corpus explicitly contains sufficient information. Topic similarity, company vocabulary, outside knowledge, and merely plausible inference are insufficient.

`expectedDocumentVersionIds`, `expectedChunkIds`, and `requiredFacts` describe evidence sufficiency for answerable rows. Negative rows keep those fields empty and record their topically relevant documents separately in `relevantDocumentVersionIds`.

Retrieval relevance and global answerability are independent. A question is not negative merely because it was originally written for another document. Eight such rows from the original experiment were retained verbatim and corrected only in the separate global label.

## Corpus

| Topic | Version | Chunk | DB category | State | Access | Evaluation dependency |
|---|---:|---:|---|---|---|---|
| MENTOR | 1 | 1 | ONBOARDING | ACTIVE/PUBLIC/current/embedded | ALL | CURRENT |
| LEAVE | 10 | 10 | BENEFITS | ACTIVE/PUBLIC/current/embedded | RESTRICTED | CURRENT |
| REMOTE | 11 | 11 | BENEFITS | ACTIVE/PUBLIC/current/embedded | RESTRICTED | CURRENT |
| CAFE | 13 | 13 | BENEFITS | ACTIVE/PUBLIC/current/embedded | ALL | CURRENT |
| HR_BUDGET | 14 | 14 | BENEFITS | ACTIVE/PUBLIC/current/embedded | RESTRICTED | CURRENT |
| WELCOME | 15 | 15 | BENEFITS | ACTIVE/PUBLIC/current/embedded | ALL | TEMPORARY |

The database category taxonomy is narrower than the six actual business topics. Access-restricted documents are evaluation-accessible only within the explicitly scoped offline corpus.

WELCOME uses `documentVersionId=15`, a disposable synthetic document originally created for RAG E2E verification. It is not guaranteed to remain permanently in shared RDS/Qdrant, and 38 dataset rows depend on it. Removing that document would invalidate those evidence references. Before treating v1 as a long-term stable benchmark, the team must either promote version 15 to permanent evaluation-corpus status or replace/re-anchor the WELCOME rows to an intentionally permanent document in a future dataset version. This dataset patch does not mutate the document.

## Known corpus gaps

- `TOPIC_DIVERSITY_GAP`: six distinct topics are available; the preferred target was eight.
- `MULTI_CHUNK_CORPUS_GAP`: every eligible distinct-topic document has one chunk.
- No synthetic document was uploaded to fill either gap.
- `MULTI_HOP` and true multi-chunk evidence cases are therefore not represented in v1.
- `PARAPHRASE_SKEW`: 152/200 rows (76%) are PARAPHRASE. This is useful for natural-language robustness but is not a balanced question-style distribution.
- `NEGATION` has 1 row and `COMPARISON` has 3 rows; both require broader v2 coverage.

## Splits and leakage prevention

| Split | Rows | Purpose |
|---|---:|---|
| TRAIN | 100 | Future model fitting only |
| VALIDATION | 40 | Threshold/model selection |
| TEST | 60 | Immutable original regression set |

All original 60 questions remain verbatim in `TEST`; none may be used for future training or threshold selection. Their document-relative labels are not stored as the benchmark target, but provenance and global-label correction notes are retained.

The v1 `TEST` split is an exposed regression/historical benchmark, not a blind final test set. Before v1 freeze, these 60 questions were already used in vector-threshold calibration, multi-document retrieval calibration, reranker evaluation, NLI evaluation, QA/no-answer evaluation, and architecture decisions. Results on them must not be presented as unbiased production generalization.

Cross-split semantic leakage also exists between `TEST` and `TRAIN`/`VALIDATION`. A known near-twin is `RAG-EVAL-0056` versus `RAG-EVAL-0158`; they differ minimally and test the same WELCOME expiration fact. REMOTE normal-working-hours facts likewise appear as semantically repeated questions across the exposed test and development splits. Consequently, TRAIN/VALIDATION performance is not independent evidence of generalization to TEST rows with close semantic counterparts.

Because the original regression set spans four of six topics, strict document-held-out splitting is not possible without weakening regression preservation. Future v2 expansion should add at least two new multi-chunk topics and hold those entire topics out for validation/test.

Future v2 must introduce a genuinely held-out document/topic `BLIND_TEST`, prevent semantic twins across development and test splits, and run deterministic plus human leakage review before freeze.

## Primary metrics

All current rows are standalone and have `inPrimaryMetrics=true`. Rows requiring conversational context or having unresolved ambiguity must be marked `inPrimaryMetrics=false` in future versions.

Evaluate independently:

1. Vector retrieval Top1/Top3/Top5 recall.
2. Reranker expected-document Top1 accuracy.
3. Corpus-global answerability precision, recall, specificity, accuracy, F1, FPR, and FNR.

Do not tune labels after observing model scores.

## Validation

Run without model or network access:

```sh
python3 evaluation/rag_answerability_v1/validate_dataset.py
```

The validator uses the already-available `jsonschema` package to validate all 200 rows against `schema.json`, including `additionalProperties` and every enum. It also checks row count, unique IDs/questions, evidence-field invariants, split counts, regression preservation, and class balance. Cross-split near-duplicate detection is warning-only because string similarity is not a reliable semantic equivalence test.

## Versioning policy

Version 1.0.2 is an annotation-only micro-patch over 1.0.1; stable IDs, questions, labels, evidence references, and splits are unchanged. After review, any question, label, fact, evidence reference, or split change requires a new dataset version and a documented migration. Typographical corrections must also be recorded rather than silently rewriting historical benchmark results.
