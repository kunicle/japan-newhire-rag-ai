# RAG Answerability-Gate Experiment — Final Conclusion

**Outcome: the separate LLM answerability-gate experiment was stopped and rejected as a runtime component.**

## Why the experiment started

Production's `rag.evidence-threshold=0.7` (a max-similarity-score gate on retrieved
evidence) was found to cause near-total false-rejection of valid, answerable
questions. Offline analysis (`analyze_gate_quality.py`, `compute_threshold_sweep.py`)
showed the underlying signal — max retrieval similarity score — has weak
answerable/unanswerable discrimination (ROC-AUC ~0.67, near-total score-distribution
overlap between answerable and unanswerable questions). Retrieval quality itself was
never the problem: Recall@3 stayed ≥0.93 across every cohort evaluated in this
experiment. The problem was gating generation on a single scalar score.

## What was tried

1. **Prompt-only LLM judge (Prompt 1 → 3E)**: a single structured-output call classifying
   `answerable`/`supportStatus` from the question + top-3 retrieved evidence. Iterated
   through six variants on a fixed 28-row TRAIN dev cohort. Prompt 3E (built as two
   minimal, assert-guarded patches on Prompt 3C's full instruction) reached 0 FP / 0 FN
   on that cohort but still carried one persistent false positive
   (`RAG-EVAL-0146`) that four consecutive prompt-only iterations could not fix.

2. **Two-stage judge + positive-only verifier**: Prompt 3E's output reused unchanged,
   plus a second, narrower verifier call that vetoes only Stage-1 positives. This
   eliminated the last TRAIN dev FP (0 FP / 0 FN on the 29-row dev+regression cohort)
   and was frozen as the candidate for blind evaluation.

3. **One-shot blind evaluation (`blind_holdout_v1`, 40 rows, new synthetic corpus,
   rigorous leakage prevention)**: the frozen two-stage candidate **failed** —
   precision 0.85, recall 0.85, specificity 0.85, all below the 0.90 acceptance bar.
   Errors split into three classes: an evidence-window miss (gold evidence outside the
   top-3 window given to the judge), a contradiction-recognition failure (two
   stale-premise questions misjudged despite rank-1 evidence), and a scope-grounding
   failure (three false positives where the judge and verifier both accepted an
   unstated population/actor/timing scope as if it were explicit).

4. **Four-stage successor architecture (`successor_v1`)**: proposition extraction →
   batched structured evidence comparison → deterministic code aggregation → structured
   positive verifier, widened to top-5 evidence. Designed specifically to fix all three
   `blind_holdout_v1` failure classes by moving the scope/condition/contradiction rule
   out of prompt text and into a boolean gate no model call could skip. The deterministic
   aggregation layer worked exactly as designed — **0 invariant violations**, confirmed
   both by construction and by independent re-derivation from raw output. But the
   upstream LLM extraction and comparison stages continued to fabricate explicit
   scope/condition matches that were not actually present in the evidence, and continued
   to miss genuine contradictions even at evidence rank 1. On the same 28-row TRAIN dev
   cohort where both Prompt 3B and the two-stage candidate had reached a clean 0 FP / 0
   FN, `successor_v1` regressed to 2 FP. On `blind_holdout_v1` (used diagnostically, not
   blind), it resolved 2 of the 6 known errors but introduced 2 new regressions of the
   same failure classes on previously-correct rows — net error count unchanged.

## Why the experiment was stopped

Two independent architectures — a single-pass judge+verifier and a four-stage
extraction/comparison/deterministic-aggregation/verifier pipeline — both plateaued
around 0.85 precision/recall/specificity with different, non-converging error patterns.
The deterministic layer was proven sound in both attempts; the unresolved errors were
consistently in upstream LLM scope/condition/contradiction judgments, and splitting the
reasoning into more stages relocated rather than reduced those errors. Per the
predefined stop condition (no more than one successor architecture attempt after the
first blind failure), the experiment concluded here rather than continuing into a third
architecture or further prompt iteration.

## What replaced it

Runtime does not use a separate pre-generation semantic gate. The simplified flow is:

```
access filtering → retrieval (top5) → evidence-only generation → citation validation
  → ANSWERED | INSUFFICIENT_EVIDENCE | API_ERROR
```

Generation is evidence-grounded by prompt instruction (the same anti-inference rules
this experiment converged on: no population/actor/absence/condition inference), and its
own structured `status` output plus backend-side citation validation determine whether
an answer is returned — not a pre-generation similarity score. This trades the
architectural rigor pursued in this experiment for a simpler, cheaper runtime with fewer
failure points; the regression test suite added alongside this change (not a
blind/generalization claim) is the ongoing safety net.

## Artifacts preserved

Nothing in `evaluation/rag_answerability_v2/` was deleted or rewritten. This includes
the threshold-sweep and gate-quality analyses, every prompt version's scripts and
results (1, 2, 3, 3B, 3C, 3D, 3E and their dev/validation/test/regression runs), the
positive verifier, `blind_holdout_v1/` (frozen dataset, retrieval environment, one-shot
manifest, and the failed blind-evaluation results/analysis), and `successor_v1/` (the
four stage modules, its dev-run results, and its analysis). They remain the record of
why this approach was rejected, for anyone who later reconsiders an LLM-based
answerability gate.
