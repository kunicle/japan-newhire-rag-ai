import json
import re
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).parent
DATASET = ROOT / "dataset.jsonl"

QUESTION_STYLES = {"LITERAL", "PARAPHRASE", "INDIRECT", "CONTEXT_OMITTED", "COMPARISON", "NEGATION", "MULTI_HOP", "AMBIGUOUS"}
ANSWER_TYPES = {"NUMERIC", "DATE_TIME", "DURATION", "BOOLEAN", "PERSON_ROLE", "DEPARTMENT", "LOCATION_CHANNEL", "PROCEDURE", "ELIGIBILITY", "LIMIT", "TEXT_FACT", "MULTI_FACT"}
NEGATIVE_TYPES = {"UNSUPPORTED_ATTRIBUTE", "UNSUPPORTED_ELIGIBILITY", "UNSUPPORTED_PROCESS", "UNSUPPORTED_EXCEPTION", "UNSUPPORTED_TIMING", "UNSUPPORTED_PERSON", "SAME_TOPIC_HALLUCINATION_TRAP", "CROSS_DOCUMENT_CONFUSION", "OUT_OF_CORPUS"}
SPLITS = {"TRAIN", "VALIDATION", "TEST"}


def main():
    rows = [json.loads(line) for line in DATASET.read_text().splitlines() if line.strip()]
    schema = json.loads((ROOT / "schema.json").read_text())
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    schema_errors = [
        f"{row.get('id', '<missing-id>')}: {error.message}"
        for row in rows
        for error in validator.iter_errors(row)
    ]
    assert not schema_errors, "schema validation failed:\n" + "\n".join(schema_errors)
    ids = [row["id"] for row in rows]
    questions = [row["question"] for row in rows]

    assert len(rows) == 200
    assert len(ids) == len(set(ids)), "duplicate IDs"
    assert len(questions) == len(set(questions)), "duplicate questions"
    assert set(row["questionStyle"] for row in rows) <= QUESTION_STYLES
    assert set(row["answerType"] for row in rows) <= ANSWER_TYPES
    assert set(row["split"] for row in rows) <= SPLITS

    for row in rows:
        if row["globalAnswerable"]:
            assert row["expectedDocumentVersionIds"]
            assert row["expectedChunkIds"]
            assert row["requiredFacts"]
            assert row["hardNegativeType"] is None
        else:
            assert row["expectedDocumentVersionIds"] == []
            assert row["expectedChunkIds"] == []
            assert row["requiredFacts"] == []
            assert row["hardNegativeType"] in NEGATIVE_TYPES

    assert Counter(row["split"] for row in rows) == {"TRAIN": 100, "VALIDATION": 40, "TEST": 60}
    regression = [row for row in rows if row["source"] == "ORIGINAL_60_REGRESSION"]
    assert len(regression) == 60
    assert all(row["split"] == "TEST" for row in regression)
    assert sum(row["globalAnswerable"] for row in regression) == 48
    assert sum(not row["globalAnswerable"] for row in regression) == 12
    assert sum(row["globalAnswerable"] for row in rows) == 100
    assert sum(not row["globalAnswerable"] for row in rows) == 100

    def normalized(question):
        return re.sub(r"[^가-힣a-z0-9]", "", question.lower())

    cross_split_candidates = []
    for index, left in enumerate(rows):
        for right in rows[index + 1:]:
            if left["split"] == right["split"]:
                continue
            ratio = SequenceMatcher(
                None, normalized(left["question"]), normalized(right["question"])
            ).ratio()
            if ratio >= 0.88:
                cross_split_candidates.append((left["id"], right["id"], ratio))

    print("RAG_EVAL_V1 valid: schema 200/200; 100 answerable; 100 not-answerable")
    if cross_split_candidates:
        preview = ", ".join(
            f"{left}<->{right} ({ratio:.2f})"
            for left, right, ratio in cross_split_candidates[:10]
        )
        print(
            "WARNING: cross-split near-duplicate candidates detected: "
            f"{len(cross_split_candidates)}; {preview}"
        )


if __name__ == "__main__":
    main()
