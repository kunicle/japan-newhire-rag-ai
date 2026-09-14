"""Build the frozen RAG_EVAL_V2 v2.0.0 dataset deterministically."""

import json

V1_PATH = "../rag_answerability_v1/dataset.jsonl"
MANIFEST_PATH = "audit_manifest.jsonl"
OUT_PATH = "dataset.jsonl"

CANONICAL_FIELDS = [
    "id", "question", "globalAnswerable", "answerType", "questionStyle",
    "difficulty", "expectedDocumentVersionIds", "expectedChunkIds",
    "requiredFacts", "hardNegativeType", "relevantDocumentVersionIds",
    "requiresConversationContext", "inPrimaryMetrics", "split", "source",
    "notes", "documentTopic", "documentCategory",
]


def build_row(v1_row, audit_row):
    row = dict(v1_row)
    row["question"] = audit_row["final_question_text"]
    row["expectedDocumentVersionIds"] = (
        audit_row["current_expected_document_version_ids"] or []
    )
    row["expectedChunkIds"] = audit_row["current_expected_chunk_ids"] or []
    row["relevantDocumentVersionIds"] = (
        audit_row["current_relevantDocumentVersionIds"]
    )
    if audit_row["proposed_required_facts"] is not None:
        row["requiredFacts"] = audit_row["proposed_required_facts"]

    if audit_row["disposition"] in ("NEEDS_RELABEL", "NEEDS_EVIDENCE_UPDATE"):
        migration_note = (
            f" [v2.0.0: {audit_row['disposition']} - {audit_row['reason']}]"
        )
        row["notes"] = (row.get("notes") or "") + migration_note

    stale_premise_note = audit_row.get("stale_premise_regression_note")
    if stale_premise_note:
        row["notes"] += f" [v2.0.0: {stale_premise_note}]"

    return {field: row[field] for field in CANONICAL_FIELDS}


def main():
    with open(V1_PATH, encoding="utf-8") as source:
        v1_rows = {row["id"]: row for row in map(json.loads, source)}
    with open(MANIFEST_PATH, encoding="utf-8") as manifest:
        audit_rows = [json.loads(line) for line in manifest]

    with open(OUT_PATH, "w", encoding="utf-8") as output:
        for audit_row in audit_rows:
            output.write(json.dumps(
                build_row(v1_rows[audit_row["id"]], audit_row),
                ensure_ascii=False,
            ) + "\n")

    print(f"Wrote {len(audit_rows)} frozen rows to {OUT_PATH}")


if __name__ == "__main__":
    main()
