# RAG_EVAL_V2 — v2.0.0

This directory does not modify `evaluation/rag_answerability_v1/`, which
remains the frozen historical baseline (v1.0.2). Nothing here has been
uploaded, re-embedded, or used to change production threshold/config.

## Frozen baseline

**Frozen on 2026-09-10.** This v2.0.0 baseline contains 200 rows:
TEST 60, TRAIN 100, and VALIDATION 40. All rows have a human-approved
disposition and value. RAG_EVAL_V1 v1.0.2 remains the immutable
historical baseline. The access-scope question is resolved by architecture
(2026-09-10, final): the canonical dataset stays pure ground truth
(`inPrimaryMetrics` and `globalAnswerable` unchanged in meaning, no new
schema fields), and the 11 MENTOR rows needing v2/chunk2 are tracked in
a separate, explicitly-non-ground-truth sidecar file
(`runtime_access_snapshot.jsonl`) instead.

The canonical dataset retains the exact v1.0.2 schema contract. Although
early planning referred to it as a 17-field schema, the source schema has
18 required fields; v2.0.0 preserves all 18 rather than dropping a required
field. `additionalProperties: false` remains enforced.

## Corpus facts used for this audit

Reported by A-dam-dangja via a read-only production DB check on
2026-09-09; not independently re-queried by this audit (the automated
read-only API path was blocked by the sandbox classifier during this
session — see conversation record).

- Active versions (ACTIVE document + PUBLIC/isActive version + within
  effective/expiration window): 2, 3, 4, 6, 7, 8, 9, 10, 11, 13, 14, 16.
- Retracted (`publicationStatus=RETRACTED`, `isActive=0`): **v1** (MENTOR
  topic in v1.0.2) and **v15** (WELCOME topic in v1.0.2). v15 was
  retracted through this session's own tracked lifecycle work
  (PR #41/#42); v1's retraction was not part of any task in this
  session and was confirmed separately by A-dam-dangja.
- New MENTOR-topic evidence (reported 2026-09-10, replacing v1):
  v2/chunk2 (title "테스트 회사 신입사원 멘토링 규정", access_scope NULL —
  **not assumed to be ALL**), v3/chunk3 and v4/chunk4 (ALL, equivalent
  content), v6/chunk6 (ALL, duration only). v7/v8/v9 confirmed to have
  no MENTOR content. Only v2 specifies the 5-business-day assignment
  window and who submits the completion report; every other fact (6
  weeks, weekly meeting, same-department senior mentor) is also present
  in the ALL-access v3/v4, which this audit prefers as evidence whenever
  a fact is available in both, precisely to minimize how much of the
  dataset depends on v2's missing access-rule configuration. Career-hire
  applicability is unspecified in all four documents.
- Access scope: v13, v16 = ALL; v10, v11, v14 = RESTRICTED; v2 has no
  access-rule row. Per this dataset's own `globalAnswerable`
  semantics (an evaluator with full access to the *complete* corpus,
  same treatment already given to RESTRICTED v10/v11/v14 in v1.0.2),
  v2 counts as "in the corpus" for the global label regardless of its
  access value. The resulting runtime retrieval block is tracked
  separately in `runtime_access_snapshot.jsonl` and does not alter the
  corpus-wide label.
- v16 (new WELCOME-topic anchor), chunk16: 82,000 points, payable within
  14 days of hire date, target = new employees, usable only in the
  internal benefits mall, not refundable for cash, header scope = all
  employees, department = **인사운영팀** (chunk16's own canonical
  expression, used verbatim — not translated to an English name the way
  v15's evidence was phrased as "People Experience Team"),
  **explicitly labeled in the document itself as a synthetic/test
  document, not a real company policy** — i.e. it carries the exact
  same long-term-fragility risk that v1.0.2's README already flagged
  for v15 ("not guaranteed to remain permanently"). Treating v16 as a
  stable long-term anchor without addressing that risk would repeat
  the v15 mistake.
- Versions 2, 3, 4, and 6 were inspected for the approved MENTOR remap;
  versions 7, 8, and 9 were confirmed not to contain MENTOR evidence.

## Label semantics (unchanged from v1.0.2, confirmed against its README)

**Decision (2026-09-10): v2.0.0 does not add an `accessScope` or
`roleScopedAnswerability` field.** `globalAnswerable` keeps exactly its
v1.0.2 meaning — corpus-wide, not user/role-scoped: "at least one
accessible document in the **complete evaluation corpus**", i.e. an
evaluator with full access across all access-scope levels, not a
specific employee role. This audit does not extend or reinterpret that
meaning.

**Limitation, recorded here rather than as a schema change:** a real
RAG query is always run as a specific user with a specific role/
department/job-grade, and `DocumentAccessScopeService` filters
candidates down to what that user can actually see (see the NULL
access-rule finding below for one concrete way this diverges from the
corpus-wide label). Because v10/v11/v14 are RESTRICTED and v13/v16 are
ALL, a real deployed evaluation run scoped to a specific role can get
`NO_ACCESSIBLE_DOCUMENT` for a globally-answerable question purely from
lacking access — a different failure mode than `LOW_SIMILARITY`. Neither
v1.0.2 nor this v2 baseline tests that distinction; user-scoped
answerability evaluation is left as a follow-up version or a separate
dataset, not something this dataset's schema covers.

## v2/chunk2 NULL access-rule: runtime behavior (code-verified 2026-09-10)

Verdict: **B — NULL means inaccessible, to every user, not ALL.**

Evidence, read-only, from `japan-newhire-rag-backend`:

- `DocumentAccessRule` (`document/access/entity/DocumentAccessRule.java`):
  `access_scope` is `@Column(nullable = false)`, and both the `create()`
  and `reconfigure()` factory/mutator methods throw
  `IllegalArgumentException` if `accessScope == null`. A
  `DocumentAccessRule` **row**, if one exists, can never itself carry a
  null `access_scope` value. So "access_scope came back NULL" cannot
  mean "a rule row exists with a null scope" — it can only mean **no
  `DocumentAccessRule` row exists for v2 at all** (consistent with a
  read-only query surfacing NULL via an outer join to a table with no
  matching row).
- `DocumentAccessScopeService.filterAccessibleDocumentVersionIds()`
  (`document/access/service/DocumentAccessScopeService.java`) calls
  `documentAccessRuleRepository.findByDocumentVersion_DocumentVersionIdIn(candidateVersionIds)`
  and then only adds a version to `accessibleVersionIds` by iterating
  over the returned rule *rows*. A version with no row simply never
  enters that loop — it is excluded before any role/department/job-grade
  check ever runs. This is fail-closed by construction, not a
  RESTRICTED-with-zero-matching-roles case.
- `DocumentAccessRule` rows are created only through
  `DocumentAccessRuleManagementService`
  (`document/access/service/DocumentAccessRuleManagementService.java`,
  wired to its own `DocumentAccessRuleController`), a separate, explicit
  configuration step — not something document upload or publish creates
  automatically. So "a PUBLIC/active document version with no access
  rule yet" is a normal, reachable state, not a data-integrity error.

Practical consequence for this audit: v2/chunk2's content is valid
*offline* corpus evidence for the `globalAnswerable` label (per the
label-semantics section above), but **as currently configured, v2 is
not retrievable through the real RAG pipeline for any user, including
HR_MANAGER/SYSTEM_ADMIN** — `DocumentVersionCandidateService` would
still surface it as a *candidate* (it only checks document/version
status, not access rules), but `DocumentAccessScopeService` drops it
before it ever reaches Qdrant search. Concretely, the 11 of 22 MENTOR
rows whose evidence is v2/chunk2 (the 5-business-day assignment and
completion-report facts) would fail with `NO_ACCESSIBLE_DOCUMENT` if run
against the live pipeline today, not because they're unanswerable, but
because v2 has no access rule configured. This does not change any
`globalAnswerable` label in this audit — it is an operational caveat for
whoever actually executes these rows against the running system, and a
separate, non-blocking note that v2 likely needs an access rule
configured (probably ALL, matching v3/v4/v6, but that is A-dam-dangja's
call, not this audit's) before it is usable end-to-end.

## Disposition definitions

- `VALID_UNCHANGED` — question, label, and evidence pointer are still
  correct against the current active corpus. Reused as-is in v2.
- `NEEDS_RELABEL` — the topic still has current evidence, but the
  specific fact/value the question tests has changed (new number, new
  name, or the derived answer flips). Requires a new `requiredFacts`
  value.
- `NEEDS_EVIDENCE_UPDATE` — the fact itself is unchanged, only the
  evidence pointer (`expectedDocumentVersionIds`/`expectedChunkIds`)
  needs to move from the retracted version to its replacement.
- `RETIRED_HISTORICAL` — the fact no longer exists anywhere in the
  active corpus and no replacement was found; kept out of v2, remains
  only as v1.0.2 historical record. **0 rows** — every fact tested by
  the original 200 rows was confirmed present somewhere in the active
  corpus, so nothing needed retiring this round.
- `NEEDS_MANUAL_REVIEW` — cannot be classified without information this
  audit does not have. Excluded from the v2 count until resolved.
  Never guessed into `VALID_UNCHANGED` or `RETIRED_HISTORICAL`. **0 rows
  as of 2026-09-10** (the 23 MENTOR rows held here previously are now
  resolved — see "MENTOR resolution" below).

## MENTOR resolution (2026-09-10)

All 23 previously-pending MENTOR rows are resolved now that v2/v3/v4/v6
content is known:

- 22 answerable rows: every `requiredFacts` value used across these
  rows (6 weeks, within 5 business days, at least once per week, senior
  employee in the same department, completion report / HR team / new
  hire and mentor) is confirmed present, unchanged, in the active
  corpus → all 22 are `NEEDS_EVIDENCE_UPDATE` (pointer only, from
  v1/chunk1 to whichever of v2/v3/v6 minimally supports that row's
  facts — see `audit_manifest.jsonl` for the per-row choice).
- `RAG-EVAL-0119` ("경력 입사자도 6주 멘토링을 받나요?"): the embedded
  "6 weeks" is confirmed still current (not stale), and career-hire
  applicability remains unspecified in every active MENTOR document
  just as it was for v1 → `VALID_UNCHANGED`.

No MENTOR row required facts split across multiple documents, so no row
needed more than one evidence document.

**Human approval, 2026-09-10:** all 22 evidence reassignments and the
`RAG-EVAL-0119` resolution above are approved as-is.

### v2-only rows (need v2/chunk2 specifically, not satisfiable by v3/v4/v6 alone)

11 of the 22 rows require a fact that exists **only** in v2/chunk2 —
`within 5 business days` (assignment window) or the completion-report
cluster (`completion report`/`HR team`/`new hire and mentor`, i.e. who
submits it). v3/v4/v6 do not mention either. These 11 keep
`globalAnswerable=true` and evidence `[2]`/`[2]` exactly as before —
that part is unaffected by the access-rule question. What it affects is
whether they're currently *executable* against the live pipeline; see
"Primary-metrics exclusion" below.

| id | split | requiredFacts |
|---|---|---|
| RAG-EVAL-0002 | TEST | within 5 business days |
| RAG-EVAL-0003 | TEST | HR team |
| RAG-EVAL-0007 | TEST | completion report, HR team |
| RAG-EVAL-0008 | TEST | within 5 business days |
| RAG-EVAL-0010 | TEST | completion report |
| RAG-EVAL-0030 | TEST | within 5 business days |
| RAG-EVAL-0060 | TEST | new hire and mentor |
| RAG-EVAL-0063 | TRAIN | within 5 business days |
| RAG-EVAL-0064 | TRAIN | within 5 business days |
| RAG-EVAL-0069 | TRAIN | completion report |
| RAG-EVAL-0070 | TRAIN | new hire and mentor |

The other 11 MENTOR `NEEDS_EVIDENCE_UPDATE` rows (6-week duration,
weekly meeting, same-department senior mentor) are fully satisfiable by
v3/v4/v6 (ALL access) and are unaffected by the v2 access-rule gap.

### `inPrimaryMetrics`: confirmed NOT the right mechanism (final, 2026-09-10)

An earlier draft of this audit considered marking the 11 v2-only rows
`inPrimaryMetrics=false` so current production-like retrieval/gate
metrics runs skip rows that can't actually be retrieved today. Checked
against v1.0.2's own definition (`../rag_answerability_v1/README.md`,
"Primary metrics" section) before applying it, per instruction not to
guess:

> "All current rows are standalone and have `inPrimaryMetrics=true`.
> Rows requiring conversational context or having unresolved ambiguity
> must be marked `inPrimaryMetrics=false` in future versions."

`schema.json` types it as a plain boolean with no further constraint,
so the README prose is the only definition available. That definition
is scoped to a property of the **question itself** — needing prior
conversational turns, or being ambiguous — paired with the sibling field
`requiresConversationContext`. It says nothing about retrievability
under a specific runtime access-rule configuration. The 11 v2-only rows
are standalone, unambiguous questions with a fully valid corpus-level
answer; the only problem is an operational access-rule gap on v2. Using
`inPrimaryMetrics=false` for that would silently repurpose an existing,
documented field to mean something it was never defined to mean.

**Final decision (2026-09-10): `inPrimaryMetrics` is left untouched for
every row, including these 11 — no field is repurposed, and no new
ground-truth field (`accessScope`, `retrievableUnderCurrentAccessConfig`,
etc.) is added to the canonical dataset either**, for the same reason:
current DocumentAccessRule configuration is a transient runtime fact,
not part of the dataset's ground truth, and folding it into the dataset
schema would mean re-versioning the dataset every time an operational
access rule changes. Instead, retrievability lives entirely in the
separate `runtime_access_snapshot.jsonl` sidecar — see below.

## Canonical dataset (ground truth only)

`dataset.jsonl`, built by `build_dataset_v2.py` from
`audit_manifest.jsonl`, is the frozen v2.0.0 dataset. It contains exactly
v1.0.2's 18 required fields and nothing else (`additionalProperties: false` in
`schema.json`, checked and passing — see Validation plan below): no
`accessScope`, no `retrievableUnderCurrentAccessConfig`, no audit-only
fields. Every row keeps `globalAnswerable` and `inPrimaryMetrics`
exactly as decided per-row above; only `question` (for the 3 rewritten
WELCOME rows), `expectedDocumentVersionIds`/`expectedChunkIds`,
`requiredFacts` (where the fact value changed), `relevantDocumentVersionIds`,
and `notes` (a short migration note appended for changed rows) differ
from the corresponding v1.0.2 row.

## Runtime access snapshot (sidecar, NOT ground truth)

`runtime_access_snapshot.jsonl`, built by
`build_runtime_access_snapshot.py`, is an **operational snapshot**, not
part of the dataset. It answers a different question than
`globalAnswerable` does: not "does the corpus contain the fact" but "is
the required evidence retrievable by the live pipeline under today's
access-rule configuration." One record per row:

```json
{"id": "RAG-EVAL-0002", "snapshotDate": "2026-09-10", "retrievableUnderCurrentAccessConfig": false, "blockingReason": "NO_DOCUMENT_ACCESS_RULE", "requiredDocumentVersionIds": [2]}
```

Rules used to build it (see file docstring for the confirmed-vs-guessed
distinction):
- Negative rows (no required evidence) → always `true`, `blockingReason: null`
  — there is no specific evidence access to be blocked on.
- Required evidence in {3, 4, 6, 10, 11, 13, 14, 16} (confirmed to have
  an actual `DocumentAccessRule` row — ALL or RESTRICTED alike) → `true`.
- Required evidence includes v2 → `false`, `blockingReason: "NO_DOCUMENT_ACCESS_RULE"`
  (code-verified, see the section above).
- Anything not confirmed either way → `false`,
  `blockingReason: "UNCONFIRMED_ACCESS_CONFIG"` (never guessed `true`).
  **0 rows fell into this bucket** — every row's required evidence was
  either confirmed configured or confirmed absent.

Result: 189 `true`, 11 `false` (all `NO_DOCUMENT_ACCESS_RULE`, exactly
the 11 rows listed above). This file is expected to go stale the moment
someone configures v2's access rule or changes any other document's
access rule — that is by design; re-running
`build_runtime_access_snapshot.py` regenerates it from the same
confirmed facts, without touching the canonical dataset or bumping its
version.

## Metric cohorts

Two independent evaluation layers, so retrieval/gate results are never
misread as generation quality or vice versa, and an access-config gap is
never confused with `LOW_SIMILARITY`:

**A. Corpus-level evaluation** — uses `dataset.jsonl` alone.
`globalAnswerable` is the ground truth, independent of any current
access configuration. All 200 rows included; nothing removed for access
reasons. This is the dataset's permanent, versioned benchmark.

**B. Production-like retrieval evaluation** — joins the canonical
dataset with `runtime_access_snapshot.jsonl` on `id`, and restricts the
retrieval/gate *primary* cohort to rows where
`retrievableUnderCurrentAccessConfig=true` (189 rows currently). The 11
`ACCESS_BLOCKED` rows are **not deleted or relabeled** — they stay in
the corpus-level set (A) and can still be reported separately as an
`ACCESS_BLOCKED` count, distinct from `RETRIEVABLE`. Running them
against the live pipeline today would surface `NO_ACCESSIBLE_DOCUMENT`
(an access-config failure), which must be tallied separately from
`LOW_SIMILARITY` (an evidence-threshold failure) — conflating the two
would misattribute an operational gap to retrieval/embedding quality.

| Cohort | Rows | Source |
|---|---:|---|
| Corpus-level (A) | 200 | `dataset.jsonl` |
| Production-like RETRIEVABLE (B) | 189 | join filtered to `retrievableUnderCurrentAccessConfig=true` |
| ACCESS_BLOCKED (reported separately, not a metrics failure) | 11 | join filtered to `retrievableUnderCurrentAccessConfig=false` |

## Files

- `audit_v1_to_v2.py` — generates `audit_manifest.jsonl` from
  `../rag_answerability_v1/dataset.jsonl` plus the corpus facts above.
  Read-only; does not touch v1.0.2 files.
- `audit_manifest.jsonl` — one record per original v1.0.2 row: id,
  topic, split, original label/evidence, disposition, reason, current
  (approved) evidence pointer, approved `requiredFacts`/question text
  where applicable, and MENTOR v2-dependency flags.
- `validate_manifest.py` — offline checks: no duplicate/missing ids
  versus v1.0.2, disposition values are valid, no row's current
  evidence/relevant-versions still point at a retracted version,
  split-by-disposition counts.
- `build_dataset_v2.py` / `dataset.jsonl` — deterministic frozen canonical
  dataset (ground truth only, v1.0.2 field contract exactly).
- `schema.json` / `validate_dataset.py` — validates the frozen dataset,
  exact ID/split contract, v1 label semantics, evidence consistency,
  runtime-field isolation, and retracted-version exclusion.
- `build_runtime_access_snapshot.py` / `runtime_access_snapshot.jsonl` —
  operational sidecar, not ground truth (see above).
- `validate_v2_freeze_readiness.py` — cross-checks that the canonical
  dataset and the sidecar each stay inside their own responsibility:
  same id set, sidecar carries no ground-truth-shaped fields, the
  ACCESS_BLOCKED set matches exactly the 11 expected ids, and those 11
  rows' `globalAnswerable`/evidence in the canonical dataset are
  untouched by their access-blocked status.

## Question-text vs. label changes (WELCOME)

Re-checked all 21 WELCOME `NEEDS_EVIDENCE_UPDATE`/`NEEDS_RELABEL` rows
against chunk16's actual facts. Three sub-cases, now distinguished in
`audit_manifest.jsonl` via `question_text_review_needed`:

- 7 rows: fact identical in v15 and v16 (no cash refund, benefits-mall
  only) → pointer swap only, no text or label change.
- 10 rows: fact value changed (amount, days, department name) but the
  question is asked generically ("얼마인가요?" / "어디인가요?") → only
  `requiredFacts` needs a new value, question text is fine as-is.
- 5 rows (`RAG-EVAL-0053`, `0054`, `0094`, `0096`, `0160`) bake a numeric
  value* directly into the question as a yes/no confirmation or a
  boundary comparison.

**Human decisions, 2026-09-10 (final, recorded in `audit_manifest.jsonl`
as `final_question_text`/`question_text_changed`/`stale_premise_regression_case`):**

| id | 처리 | 최종 질문 | 최종 requiredFacts |
|---|---|---|---|
| `RAG-EVAL-0053` | 문구 재작성(승인) | "입사한 지 15일인데 포인트가 안 들어왔다면 지급 기준을 넘긴 건가요?" | within 14 days; 15 days exceeds the window (정답: 예, 원본과 동일 극성) |
| `RAG-EVAL-0054` | **문구 유지(승인)** — stale-premise 환불 정책 회귀 케이스 | "지급받은 7만3천 포인트를 돈으로 돌려받을 수 있나요?" (변경 없음) | not refundable for cash — 철회된 과거 금액이 섞여 있어도 현재 환불 정책을 적용하는지 검증 |
| `RAG-EVAL-0096` | 문구 재작성(승인) | "입사 14일 안에 포인트가 들어오는 정책인가요?" | within 14 days |
| `RAG-EVAL-0160` | 문구 재작성(승인) | "경력 입사자도 82,000포인트를 받나요?" | (negative, 라벨/hardNegativeType 불변) |
| `RAG-EVAL-0094` | **문구 유지(승인)** — stale-premise 회귀 케이스로 의도적 보존 | "신입 복지 포인트 금액이 7만3천 포인트인가요?" (변경 없음) | 82000 points — 정답은 "아니오, 현재 근거는 82,000점"; 질문의 옛 수치(73,000)를 그대로 두어 철회된 문서의 수치를 현재값과 혼동하지 않는지 검증하는 대조 케이스로 유지 |

`RAG-EVAL-0094`는 옛 금액을 현재 82,000점과 직접 대조하는 사례다.
`RAG-EVAL-0054`는 옛 금액이 premise에 섞여 있어도 현재의 현금 환불
불가 정책을 올바르게 적용하는지를 보는 별도 stale-premise 사례다.

## Inherited test and leakage limitations

The v2.0.0 TEST split is not a fully blind test. Many rows are inherited
from v1.0.2 and were exposed to earlier threshold, reranker, NLI, and QA
experiments, so their results are regression evidence and must not be
reported as performance on a previously unused holdout set.

Known cross-split near-duplicate and semantic leakage limitations also
remain inherited from v1.0.2. For example, `RAG-EVAL-0056` and
`RAG-EVAL-0158` are near-equivalent questions about the same WELCOME
expiration fact. This limitation should be considered when interpreting
TEST, TRAIN, and VALIDATION results; v2.0.0 does not claim to eliminate it.

## Reproduce and validate

Run from this directory, without network access or production services:

```bash
python3 audit_v1_to_v2.py
python3 validate_manifest.py
python3 build_dataset_v2.py
python3 validate_dataset.py
python3 build_runtime_access_snapshot.py
python3 validate_v2_freeze_readiness.py
```

Re-running both builders must leave `dataset.jsonl` and
`runtime_access_snapshot.jsonl` byte-for-byte unchanged.

## Follow-up

1. ~~Approve WELCOME 21-row changes and 4 question-text decisions~~ **완료 (2026-09-10)**.
2. ~~Approve MENTOR 22-row evidence reassignment and `RAG-EVAL-0119`~~ **완료 (2026-09-10)**.
3. ~~Decide the primary-metrics/access-gap mechanism~~ **완료 (2026-09-10)** — resolved architecturally: no schema change, sidecar file instead (`runtime_access_snapshot.jsonl`), two-cohort metric design (see above).
4. Optionally configure an access rule for v2/chunk2 (operational, not
   a dataset change) so the 11 MENTOR rows relying on it become
   retrievable end-to-end. Not required to freeze v2.0.0 — the corpus-
   level benchmark (cohort A) is valid either way; only cohort B's
   RETRIEVABLE count would change (189 → 200).
5. No net-new questions needed — every original fact survived with
   either the same or an updated value; no row became `RETIRED_HISTORICAL`.
6. The v2.0.0 freeze is complete. Future evidence, access-snapshot, or
   label changes require an explicit subsequent dataset version.
