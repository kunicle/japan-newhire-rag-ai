"""Cross-check that the frozen canonical dataset and the runtime access
snapshot each stay inside their own responsibility, and agree with each
other where they must.

Canonical dataset (dataset.jsonl): ground truth only --
globalAnswerable, evidence, requiredFacts, etc. Never touched by
runtime/access-config facts.

Runtime access snapshot (runtime_access_snapshot.jsonl): operational
retrievability only. Never carries globalAnswerable, requiredFacts, or
any other ground-truth field, and never changes them.
"""

import json

CANONICAL_PATH = "dataset.jsonl"
SNAPSHOT_PATH = "runtime_access_snapshot.jsonl"

SNAPSHOT_ALLOWED_FIELDS = {
    "id", "snapshotDate", "retrievableUnderCurrentAccessConfig",
    "blockingReason", "requiredDocumentVersionIds",
}

EXPECTED_ACCESS_BLOCKED_IDS = {
    "RAG-EVAL-0002", "RAG-EVAL-0003", "RAG-EVAL-0007", "RAG-EVAL-0008",
    "RAG-EVAL-0010", "RAG-EVAL-0030", "RAG-EVAL-0060", "RAG-EVAL-0063",
    "RAG-EVAL-0064", "RAG-EVAL-0069", "RAG-EVAL-0070",
}


def main():
    with open(CANONICAL_PATH, encoding="utf-8") as f:
        canonical = {r["id"]: r for r in (json.loads(line) for line in f)}
    with open(SNAPSHOT_PATH, encoding="utf-8") as f:
        snapshot = {r["id"]: r for r in (json.loads(line) for line in f)}

    errors = []

    if set(canonical) != set(snapshot):
        errors.append(
            f"id set mismatch: canonical-only={set(canonical)-set(snapshot)}, "
            f"snapshot-only={set(snapshot)-set(canonical)}"
        )

    for row_id, srow in snapshot.items():
        extra = set(srow) - SNAPSHOT_ALLOWED_FIELDS
        if extra:
            errors.append(f"{row_id}: snapshot row has ground-truth-shaped fields {extra}")
        if not isinstance(srow["retrievableUnderCurrentAccessConfig"], bool):
            errors.append(f"{row_id}: retrievableUnderCurrentAccessConfig is not boolean")
        if srow["retrievableUnderCurrentAccessConfig"] and srow["blockingReason"] is not None:
            errors.append(f"{row_id}: retrievable=true but blockingReason is set")
        if not srow["retrievableUnderCurrentAccessConfig"] and srow["blockingReason"] is None:
            errors.append(f"{row_id}: retrievable=false but blockingReason is missing")
        if srow.get("snapshotDate") != "2026-09-10":
            errors.append(f"{row_id}: snapshotDate must be 2026-09-10")

    actual_blocked_ids = {
        row_id for row_id, srow in snapshot.items()
        if not srow["retrievableUnderCurrentAccessConfig"]
    }
    if actual_blocked_ids != EXPECTED_ACCESS_BLOCKED_IDS:
        errors.append(
            f"ACCESS_BLOCKED set mismatch: expected={EXPECTED_ACCESS_BLOCKED_IDS}, "
            f"actual={actual_blocked_ids}"
        )

    # Ground truth (globalAnswerable, expectedDocumentVersionIds) for the
    # 11 blocked rows must be untouched by the access-blocked status --
    # they stay globalAnswerable=true with v2/chunk2 as evidence.
    for row_id in EXPECTED_ACCESS_BLOCKED_IDS:
        crow = canonical[row_id]
        if crow["globalAnswerable"] is not True:
            errors.append(f"{row_id}: expected globalAnswerable=true, corpus-wide label untouched")
        if crow["expectedDocumentVersionIds"] != [2]:
            errors.append(
                f"{row_id}: expected evidence [2] (v2/chunk2) unchanged, "
                f"got {crow['expectedDocumentVersionIds']}"
            )
        if crow["expectedChunkIds"] != [2]:
            errors.append(
                f"{row_id}: expected chunk evidence [2] unchanged, "
                f"got {crow['expectedChunkIds']}"
            )

    retrievable_count = sum(
        1 for srow in snapshot.values() if srow["retrievableUnderCurrentAccessConfig"]
    )
    blocked_count = len(snapshot) - retrievable_count
    no_rule_count = sum(
        1 for srow in snapshot.values()
        if srow["blockingReason"] == "NO_DOCUMENT_ACCESS_RULE"
    )
    unconfirmed_count = sum(
        1 for srow in snapshot.values()
        if srow["blockingReason"] == "UNCONFIRMED_ACCESS_CONFIG"
    )

    print("Canonical rows:", len(canonical))
    print("Snapshot rows:", len(snapshot))
    print("RETRIEVABLE count:", retrievable_count)
    print("ACCESS_BLOCKED count:", blocked_count)
    print("NO_DOCUMENT_ACCESS_RULE count:", no_rule_count)
    print("UNCONFIRMED_ACCESS_CONFIG count:", unconfirmed_count)

    if retrievable_count != 189 or blocked_count != 11:
        errors.append("expected 189 retrievable and 11 access-blocked rows")
    if no_rule_count != 11 or unconfirmed_count != 0:
        errors.append("runtime blocking-reason counts do not match the approved snapshot")

    if errors:
        print("\nFAILED:")
        for e in errors:
            print(" -", e)
        raise SystemExit(1)

    print("\nAll cross-checks passed: canonical and snapshot stay in their own lanes.")


if __name__ == "__main__":
    main()
