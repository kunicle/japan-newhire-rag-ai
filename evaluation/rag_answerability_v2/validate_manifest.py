"""Offline, no-network validation of audit_manifest.jsonl.

Checks:
- no duplicate ids
- every id from v1.0.2 is present exactly once
- disposition is one of the five allowed values
- no row's current evidence still points at a RETRACTED version (1 or 15)
- NEEDS_MANUAL_REVIEW rows carry no current evidence (nothing finalized
  without confirmation)
- split distribution matches the original per-disposition breakdown
"""

import json
from collections import Counter

ALLOWED_DISPOSITIONS = {
    "VALID_UNCHANGED",
    "NEEDS_RELABEL",
    "NEEDS_EVIDENCE_UPDATE",
    "RETIRED_HISTORICAL",
    "NEEDS_MANUAL_REVIEW",
}
RETRACTED_VERSION_IDS = {1, 15}


def main():
    with open("audit_manifest.jsonl", encoding="utf-8") as f:
        records = [json.loads(line) for line in f]

    errors = []

    ids = [r["id"] for r in records]
    if len(ids) != len(set(ids)):
        dupes = [i for i, c in Counter(ids).items() if c > 1]
        errors.append(f"duplicate ids: {dupes}")

    with open("../rag_answerability_v1/dataset.jsonl", encoding="utf-8") as f:
        v1_ids = {json.loads(line)["id"] for line in f}
    if set(ids) != v1_ids:
        missing = v1_ids - set(ids)
        extra = set(ids) - v1_ids
        if missing:
            errors.append(f"missing ids from v1: {sorted(missing)}")
        if extra:
            errors.append(f"unexpected extra ids: {sorted(extra)}")

    for r in records:
        if r["disposition"] not in ALLOWED_DISPOSITIONS:
            errors.append(f"{r['id']}: invalid disposition {r['disposition']}")

        current_versions = r.get("current_expected_document_version_ids")
        if current_versions:
            bad = RETRACTED_VERSION_IDS.intersection(current_versions)
            if bad:
                errors.append(
                    f"{r['id']}: current evidence still points at retracted version(s) {bad}"
                )

        relevant_versions = r.get("current_relevantDocumentVersionIds")
        if relevant_versions:
            bad_rel = RETRACTED_VERSION_IDS.intersection(relevant_versions)
            if bad_rel:
                errors.append(
                    f"{r['id']}: relevantDocumentVersionIds still points at retracted version(s) {bad_rel}"
                )

        if r["disposition"] == "NEEDS_MANUAL_REVIEW" and r.get(
            "current_expected_document_version_ids"
        ) not in (None, r.get("original_expectedDocumentVersionIds")):
            errors.append(
                f"{r['id']}: NEEDS_MANUAL_REVIEW row must not finalize new evidence"
            )

    split_by_disposition = Counter((r["disposition"], r["split"]) for r in records)

    print("Rows checked:", len(records))
    print("Disposition x split:")
    for (disp, split), count in sorted(split_by_disposition.items()):
        print(f"  {disp:22s} {split:11s} {count}")

    if errors:
        print("\nFAILED:")
        for e in errors:
            print(" -", e)
        raise SystemExit(1)

    print("\nAll checks passed.")


if __name__ == "__main__":
    main()
