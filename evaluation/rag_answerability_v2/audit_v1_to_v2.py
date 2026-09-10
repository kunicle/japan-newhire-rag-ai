"""Read-only audit of RAG_EVAL_V1 (v1.0.2) against the current active corpus.

Does not modify evaluation/rag_answerability_v1/. Produces
audit_manifest.jsonl describing, for every original row, whether it is
still valid, needs relabeling, needs an evidence pointer update, is
retired to historical-only status, or needs manual review because the
current corpus content for its topic has not been confirmed.

Source of the "current corpus facts" below: A-dam-dangja read-only
production DB check reported in-conversation on 2026-09-09. Not
independently re-verified against the database by this script.
"""

import json

V1_PATH = "../rag_answerability_v1/dataset.jsonl"
OUT_PATH = "audit_manifest.jsonl"

# Confirmed retracted (publicationStatus=RETRACTED, isActive=false)
RETRACTED_VERSION_IDS = {1, 15}

# Confirmed still ACTIVE/PUBLIC as of the audit (versions actually
# referenced by RAG_EVAL_V1 rows): 10, 11, 13, 14, 16.
UNCHANGED_ACTIVE_VERSION_IDS = {10, 11, 13, 14}

# New anchor for the WELCOME topic, replacing v15.
NEW_WELCOME_VERSION_ID = 16
NEW_WELCOME_CHUNK_ID = 16

# New MENTOR-topic evidence, confirmed by A-dam-dangja's follow-up
# read-only DB check (2026-09-10). v7/v8/v9 confirmed to have no
# MENTOR content. None of v2/v3/v4/v6 specify career-hire applicability.
MENTOR_REPLACEMENT_VERSION_IDS = {2, 3, 4, 6}

# fact string -> (versionId, chunkId) chosen as minimal sufficient
# evidence. Facts available in multiple documents prefer the ALL-access
# ones (v3) over the access_scope=NULL one (v2), per explicit
# instruction not to assume v2's NULL access means ALL; v2 is used only
# for facts that exist nowhere else.
MENTOR_FACT_EVIDENCE = {
    "6 weeks": (6, 6),
    "within 5 business days": (2, 2),  # only v2 specifies this
    "at least once per week": (3, 3),
    "senior employee in the same department": (3, 3),
    "completion report": (2, 2),  # only v2 specifies submission detail
    "HR team": (2, 2),
    "new hire and mentor": (2, 2),  # only v2 specifies who submits
}

# Confirmed chunk16 facts (from A-dam-dangja's report). Department name
# uses chunk16's own canonical Korean expression verbatim -- not
# translated or guessed, per explicit instruction not to invent an
# English equivalent the way v15's "People Experience Team" was phrased.
CHUNK16_FACTS = {
    "amount": "82000 points",
    "payment_window": "within 14 days of hire date",
    "target": "new employees",
    "usage": "internal benefits mall only",
    "refund": "not refundable for cash",
    "applies_to_header": "all employees",
    "department": "인사운영팀",
    "is_synthetic_test_document": True,
}

# requiredFacts value -> proposed v2 value, only for facts that actually
# changed between v15 and v16. Facts not listed here are unchanged.
WELCOME_FACT_MIGRATION = {
    "73000 points": ("82000 points", "NEEDS_RELABEL", "금액 변경(73,000 -> 82,000)"),
    "within 7 days": ("within 14 days", "NEEDS_RELABEL", "지급 기한 변경(7일 -> 14일)"),
    "People Experience Team": (
        "인사운영팀",
        "NEEDS_RELABEL",
        "담당 부서명 변경(People Experience Team -> 인사운영팀; chunk16의 canonical 한글 표현 그대로 사용, 번역/추측 아님)",
    ),
    "not refundable for cash": (
        "not refundable for cash",
        "NEEDS_EVIDENCE_UPDATE",
        "사실 동일, 근거만 v15->v16으로 교체",
    ),
    "internal benefits mall only": (
        "internal benefits mall only",
        "NEEDS_EVIDENCE_UPDATE",
        "사실 동일, 근거만 v15->v16으로 교체",
    ),
    "internal benefits mall": (
        "internal benefits mall only",
        "NEEDS_EVIDENCE_UPDATE",
        "사실 동일(표현만 상이), 근거만 v15->v16으로 교체",
    ),
}

# RAG-EVAL-0119 ("경력 입사자도 6주 멘토링을 받나요?") previously held as
# NEEDS_MANUAL_REVIEW because "6 weeks" looked stale after v1's
# retraction. Resolved 2026-09-10: v3/v4/v6 confirm 6 weeks is still the
# current duration, so the number is current, not stale. Career-hire
# applicability remains unspecified in every active MENTOR document, so
# the negative label is unaffected -> VALID_UNCHANGED, just needs its
# relevantDocumentVersionIds pointer refreshed (handled generically
# below for every MENTOR/WELCOME row).

# WELCOME rows whose *question text itself* (not just requiredFacts)
# needed rewriting, because it poses a yes/no confirmation against the
# old value or an edge-case comparison that no longer sits near the new
# boundary. Distinct from a pure requiredFacts value swap.
#
# Human-approved final text, 2026-09-10:
QUESTION_TEXT_REVIEW_NEEDED = {
    "RAG-EVAL-0053": (
        "질문이 '입사 8일째'를 구 기준(7일) 초과 여부로 묻는데, 신 기준(14일)에서는 "
        "8일이 경계에서 멀어 edge-case로서 의미가 없음 - 15일(14일 경계 바로 다음 값)로 "
        "질문 자체를 재작성함(승인됨)"
    ),
    "RAG-EVAL-0096": (
        "질문이 '입사 일주일 안에 들어오나요?'라는 확인형 문구 - 신 기준은 14일이므로 "
        "'일주일 이내 보장'은 확인 불가한 주장이 됨 - 14일로 질문 자체를 재작성함(승인됨)"
    ),
    "RAG-EVAL-0160": (
        "질문 문구에 구 포인트 금액(73,000) 인용 - 82,000으로 갱신함(승인됨). "
        "라벨은 UNSUPPORTED_ATTRIBUTE/negative로 유지"
    ),
}

# Final approved question text for the three rows above (id -> new text).
WELCOME_FINAL_QUESTION_TEXT = {
    "RAG-EVAL-0053": "입사한 지 15일인데 포인트가 안 들어왔다면 지급 기준을 넘긴 건가요?",
    "RAG-EVAL-0096": "입사 14일 안에 포인트가 들어오는 정책인가요?",
    "RAG-EVAL-0160": "경력 입사자도 82,000포인트를 받나요?",
}

# RAG-EVAL-0094: human decision (2026-09-10) is to KEEP the original
# question text verbatim ("신입 복지 포인트 금액이 7만3천 포인트인가요?") as
# a deliberate stale-premise regression/contrast case: the question still
# cites the retracted document's old figure, and the correct current
# answer is "No, the current evidence is 82,000 points" -- testing
# whether the system correctly contradicts an outdated premise rather
# than confirming it. Not the same treatment as the three rows above.
STALE_PREMISE_REGRESSION_NOTES = {
    "RAG-EVAL-0054": (
        "철회된 과거 금액 73,000을 의도적으로 포함하지만, "
        "현재 정책의 환불 가능 여부를 검증하는 stale-premise 회귀 케이스"
    ),
    "RAG-EVAL-0094": (
        "철회된 과거 금액 73,000과 현재 금액 82,000을 직접 대조하는 "
        "stale-premise 회귀 케이스"
    ),
}
STALE_PREMISE_REGRESSION_IDS = set(STALE_PREMISE_REGRESSION_NOTES)


def classify(row):
    topic = row.get("documentTopic")
    expected = row.get("expectedDocumentVersionIds", [])
    row_id = row["id"]

    if topic not in ("MENTOR", "WELCOME"):
        return {
            "disposition": "VALID_UNCHANGED",
            "reason": f"근거 문서 {expected} PUBLIC/active 유지 확인(A담당자 read-only 조회)",
            "current_expected_document_version_ids": expected,
            "current_expected_chunk_ids": row.get("expectedChunkIds", []),
            "proposed_required_facts": None,
        }

    if topic == "MENTOR":
        if expected == [1]:
            facts = row.get("requiredFacts", [])
            unmapped = [f for f in facts if f not in MENTOR_FACT_EVIDENCE]
            if unmapped:
                return {
                    "disposition": "NEEDS_MANUAL_REVIEW",
                    "reason": f"미매핑 requiredFacts 값: {unmapped}",
                    "current_expected_document_version_ids": None,
                    "current_expected_chunk_ids": None,
                    "proposed_required_facts": None,
                }
            evidence_pairs = {MENTOR_FACT_EVIDENCE[f] for f in facts}
            # Minimal sufficient evidence: if every required fact maps to
            # the same single document, use that one document/chunk. If
            # a row needs facts split across documents (none of this
            # round's 22 rows do), that would itself need manual review
            # rather than silently unioning sources.
            if len(evidence_pairs) != 1:
                return {
                    "disposition": "NEEDS_MANUAL_REVIEW",
                    "reason": (
                        f"requiredFacts가 서로 다른 문서에 흩어져 있음: {evidence_pairs} "
                        "- 단일 최소 근거로 좁혀지지 않아 수동 검토 필요"
                    ),
                    "current_expected_document_version_ids": None,
                    "current_expected_chunk_ids": None,
                    "proposed_required_facts": None,
                }
            version_id, chunk_id = next(iter(evidence_pairs))
            retrievable_now = version_id != 2
            return {
                "disposition": "NEEDS_EVIDENCE_UPDATE",
                "reason": (
                    f"v1 RETRACTED. 동일 사실이 v{version_id}(access={'ALL' if retrievable_now else 'NULL, ALL로 가정하지 않음'})"
                    f"에 그대로 존재 - 근거만 v1/chunk1 -> v{version_id}/chunk{chunk_id}로 교체, "
                    "requiredFacts 값 변경 없음"
                ),
                "current_expected_document_version_ids": [version_id],
                "current_expected_chunk_ids": [chunk_id],
                "proposed_required_facts": facts,
                "requires_v2_only_evidence": not retrievable_now,
                "retrievable_under_current_access_config": retrievable_now,
            }
        if row_id == "RAG-EVAL-0119":
            return {
                "disposition": "VALID_UNCHANGED",
                "reason": (
                    "재검토 결과 '6주'는 v3/v4/v6에서 현재도 확인되는 값이므로 stale이 "
                    "아님(2026-09-10 재확인). 경력 입사자 적용 여부는 활성 문서 어디에도 "
                    "명시되지 않아 UNSUPPORTED_ATTRIBUTE 라벨 그대로 유효"
                ),
                "current_expected_document_version_ids": expected,
                "current_expected_chunk_ids": row.get("expectedChunkIds", []),
                "proposed_required_facts": None,
            }
        return {
            "disposition": "VALID_UNCHANGED",
            "reason": "v1 철회와 무관한 UNSUPPORTED 속성/절차 질문 - 라벨 영향 없음",
            "current_expected_document_version_ids": expected,
            "current_expected_chunk_ids": row.get("expectedChunkIds", []),
            "proposed_required_facts": None,
        }

    # topic == WELCOME
    if expected == [15]:
        facts = row.get("requiredFacts", [])
        dispositions = []
        proposed_facts = []
        reasons = []
        for fact in facts:
            if fact not in WELCOME_FACT_MIGRATION:
                dispositions.append("NEEDS_MANUAL_REVIEW")
                reasons.append(f"미매핑 requiredFacts 값: {fact}")
                proposed_facts.append(fact)
                continue
            new_value, disp, reason = WELCOME_FACT_MIGRATION[fact]
            dispositions.append(disp)
            reasons.append(reason)
            proposed_facts.append(new_value)

        # RAG-EVAL-0053 is a derived comparison whose day count and
        # answer were both approved for rewrite 2026-09-10: question now
        # asks about day 15 (just past the new 14-day window), so the
        # answer is still "yes, exceeded" -- same polarity as the
        # original (day 8 exceeded the old 7-day window), just re-anchored
        # to the new boundary instead of flipping to "no".
        if row_id == "RAG-EVAL-0053":
            dispositions = ["NEEDS_RELABEL"]
            reasons = [
                "파생 비교 질문: 신 기준(14일) 경계 바로 다음 값인 15일로 재작성(승인됨) - "
                "15일은 14일을 초과하므로 정답은 원본과 동일하게 '예, 초과함'"
            ]
            proposed_facts = ["within 14 days; 15 days exceeds the window"]

        final_disposition = (
            "NEEDS_MANUAL_REVIEW"
            if "NEEDS_MANUAL_REVIEW" in dispositions
            else ("NEEDS_RELABEL" if "NEEDS_RELABEL" in dispositions else "NEEDS_EVIDENCE_UPDATE")
        )
        return {
            "disposition": final_disposition,
            "reason": "; ".join(reasons),
            "current_expected_document_version_ids": [NEW_WELCOME_VERSION_ID],
            "current_expected_chunk_ids": [NEW_WELCOME_CHUNK_ID],
            "proposed_required_facts": proposed_facts,
        }

    # WELCOME negative row
    if row_id in QUESTION_TEXT_REVIEW_NEEDED:
        return {
            "disposition": "NEEDS_RELABEL",
            "reason": QUESTION_TEXT_REVIEW_NEEDED[row_id],
            "current_expected_document_version_ids": expected,
            "current_expected_chunk_ids": row.get("expectedChunkIds", []),
            "proposed_required_facts": None,
        }
    return {
        "disposition": "VALID_UNCHANGED",
        "reason": (
            "v16(chunk16)의 확인된 사실(금액/기한/대상/사용처/환불/부서) 어디에도 "
            "해당 UNSUPPORTED 주장을 뒷받침하는 내용 없음 - 네거티브 라벨 유지"
        ),
        "current_expected_document_version_ids": expected,
        "current_expected_chunk_ids": row.get("expectedChunkIds", []),
        "proposed_required_facts": None,
    }


# v1->new MENTOR docs, v15->v16 for WELCOME. Applies to
# relevantDocumentVersionIds only (a metadata pointer refresh; never
# used to silently justify a label change).
RELEVANT_VERSION_REMAP = {1: sorted(MENTOR_REPLACEMENT_VERSION_IDS), 15: [NEW_WELCOME_VERSION_ID]}


def remap_relevant_versions(ids):
    remapped = []
    for v in ids:
        remapped.extend(RELEVANT_VERSION_REMAP.get(v, [v]))
    # de-duplicate, keep order
    seen = []
    for v in remapped:
        if v not in seen:
            seen.append(v)
    return seen


def main():
    with open(V1_PATH, encoding="utf-8") as f:
        rows = [json.loads(line) for line in f]

    counts = {}
    with open(OUT_PATH, "w", encoding="utf-8") as out:
        for row in rows:
            audit = classify(row)
            counts[audit["disposition"]] = counts.get(audit["disposition"], 0) + 1
            row_id = row["id"]
            original_question = row["question"]
            record = {
                "id": row_id,
                "documentTopic": row["documentTopic"],
                "split": row["split"],
                "original_globalAnswerable": row["globalAnswerable"],
                "original_question": original_question,
                "original_expectedDocumentVersionIds": row.get("expectedDocumentVersionIds", []),
                "original_requiredFacts": row.get("requiredFacts", []),
                **audit,
                "requires_v2_only_evidence": audit.get("requires_v2_only_evidence", False),
                "retrievable_under_current_access_config": audit.get(
                    "retrievable_under_current_access_config", True
                ),
                "current_relevantDocumentVersionIds": remap_relevant_versions(
                    row.get("relevantDocumentVersionIds", [])
                ),
                "question_text_review_needed": row_id in QUESTION_TEXT_REVIEW_NEEDED,
                "question_text_review_note": QUESTION_TEXT_REVIEW_NEEDED.get(row_id),
                "final_question_text": WELCOME_FINAL_QUESTION_TEXT.get(row_id, original_question),
                "question_text_changed": row_id in WELCOME_FINAL_QUESTION_TEXT,
                "stale_premise_regression_case": row_id in STALE_PREMISE_REGRESSION_IDS,
                "stale_premise_regression_note": STALE_PREMISE_REGRESSION_NOTES.get(row_id),
            }
            out.write(json.dumps(record, ensure_ascii=False) + "\n")

    print("Total rows:", len(rows))
    for k, v in sorted(counts.items()):
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
