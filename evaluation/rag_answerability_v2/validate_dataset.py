"""Validate the frozen v2.0.0 dataset and its v1 migration contract."""

import json
from collections import Counter

import jsonschema

DATASET_PATH = "dataset.jsonl"
SCHEMA_PATH = "schema.json"
V1_PATH = "../rag_answerability_v1/dataset.jsonl"
RETRACTED_VERSION_IDS = {1, 15}
EXPECTED_SPLITS = {"TEST": 60, "TRAIN": 100, "VALIDATION": 40}
RUNTIME_ONLY_FIELDS = {
    "snapshotDate", "retrievableUnderCurrentAccessConfig", "blockingReason",
    "requiredDocumentVersionIds", "requires_v2_only_evidence",
    "retrievable_under_current_access_config",
}


def load_rows(path):
    with open(path, encoding="utf-8") as source:
        return [json.loads(line) for line in source]


def main():
    rows = load_rows(DATASET_PATH)
    v1_rows = {row["id"]: row for row in load_rows(V1_PATH)}
    with open(SCHEMA_PATH, encoding="utf-8") as source:
        schema = json.load(source)

    errors = []
    ids = [row["id"] for row in rows]
    if len(rows) != 200:
        errors.append(f"expected 200 rows, got {len(rows)}")
    if len(ids) != len(set(ids)):
        errors.append("duplicate ids detected")
    if set(ids) != set(v1_rows):
        errors.append("v2 id set does not match v1.0.2")
    splits = Counter(row["split"] for row in rows)
    if dict(splits) != EXPECTED_SPLITS:
        errors.append(f"split mismatch: {dict(splits)}")

    validator = jsonschema.Draft202012Validator(schema)
    for row in rows:
        errors.extend(
            f"{row['id']}: schema violation - {error.message}"
            for error in validator.iter_errors(row)
        )
        leaked = set(row).intersection(RUNTIME_ONLY_FIELDS)
        if leaked:
            errors.append(f"{row['id']}: runtime-only fields leaked: {sorted(leaked)}")
        version_refs = (
            set(row["expectedDocumentVersionIds"])
            | set(row["relevantDocumentVersionIds"])
        )
        if version_refs.intersection(RETRACTED_VERSION_IDS):
            errors.append(f"{row['id']}: references retracted evidence")
        if not set(row["expectedDocumentVersionIds"]).issubset(
            row["relevantDocumentVersionIds"]
        ):
            errors.append(f"{row['id']}: expected evidence is not relevant evidence")
        if len(row["expectedDocumentVersionIds"]) != len(row["expectedChunkIds"]):
            errors.append(f"{row['id']}: expected version/chunk cardinality mismatch")
        original = v1_rows.get(row["id"])
        if original and row["globalAnswerable"] != original["globalAnswerable"]:
            errors.append(f"{row['id']}: globalAnswerable changed")
        if original and row["inPrimaryMetrics"] != original["inPrimaryMetrics"]:
            errors.append(f"{row['id']}: inPrimaryMetrics changed")

    by_id = {row["id"]: row for row in rows}
    expected_questions = {
        "RAG-EVAL-0053": "입사한 지 15일인데 포인트가 안 들어왔다면 지급 기준을 넘긴 건가요?",
        "RAG-EVAL-0096": "입사 14일 안에 포인트가 들어오는 정책인가요?",
        "RAG-EVAL-0160": "경력 입사자도 82,000포인트를 받나요?",
    }
    for row_id, question in expected_questions.items():
        if by_id[row_id]["question"] != question:
            errors.append(f"{row_id}: approved question text mismatch")
    if by_id["RAG-EVAL-0094"]["question"] != v1_rows["RAG-EVAL-0094"]["question"]:
        errors.append("RAG-EVAL-0094 stale-premise question was not preserved")

    print("Rows:", len(rows))
    print("Canonical fields:", len(schema["required"]))
    print("Split distribution:", dict(splits))
    if errors:
        print("\nFAILED:")
        for error in errors:
            print(" -", error)
        raise SystemExit(1)
    print("\nAll frozen dataset checks passed.")


if __name__ == "__main__":
    main()
