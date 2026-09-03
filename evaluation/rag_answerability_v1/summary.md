# RAG_EVAL_V1 summary

- Version: 1.0.2
- Total: 200
- Answerable: 100
- Not answerable: 100
- Same-topic unsupported negatives: 100
- Original regression test rows: 60
- Train/validation/test: 100/40/60
- Corpus topics: 6
- Multi-chunk documents: 0
- WELCOME temporary dependency rows: 38
- TEST interpretation: exposed regression set, not blind test

## Question styles

| Style | Count |
|---|---:|
| LITERAL | 32 |
| PARAPHRASE | 152 |
| INDIRECT | 12 |
| COMPARISON | 3 |
| NEGATION | 1 |

## Answer types

| Type | Count |
|---|---:|
| BOOLEAN | 42 |
| DATE_TIME | 19 |
| DEPARTMENT | 6 |
| DURATION | 7 |
| ELIGIBILITY | 23 |
| LIMIT | 13 |
| LOCATION_CHANNEL | 14 |
| NUMERIC | 42 |
| PERSON_ROLE | 2 |
| PROCEDURE | 11 |
| TEXT_FACT | 21 |

## Hard-negative types

| Type | Count |
|---|---:|
| UNSUPPORTED_ATTRIBUTE | 41 |
| UNSUPPORTED_ELIGIBILITY | 11 |
| UNSUPPORTED_EXCEPTION | 13 |
| UNSUPPORTED_PERSON | 8 |
| UNSUPPORTED_PROCESS | 18 |
| UNSUPPORTED_TIMING | 9 |

All 100 negative rows are same-topic unsupported cases; obvious out-of-corpus negatives were intentionally not used to inflate precision.

## Topic coverage

| Topic | Count |
|---|---:|
| MENTOR | 40 |
| LEAVE | 40 |
| REMOTE | 42 |
| WELCOME | 38 |
| CAFE | 20 |
| HR_BUDGET | 20 |

## Scope limitations

This is a partial v1 benchmark because the shared corpus does not yet provide eight distinct topics or any multi-chunk document. It is suitable for regression and initial answerability comparison, but production-quality model selection requires a future document-held-out, multi-chunk expansion.
