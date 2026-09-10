"""Build runtime_access_snapshot.jsonl: an operational sidecar, NOT part
of the ground-truth dataset.

Records, per row, whether its required evidence is retrievable by the
live RAG pipeline under the CURRENT DocumentAccessRule configuration
(2026-09-10 snapshot). This is orthogonal to `globalAnswerable` (corpus-
wide ground truth) and to `inPrimaryMetrics` (question ambiguity/context
property) -- neither of those is touched by this file.

Only marks retrievableUnderCurrentAccessConfig=true where there is an
actual confirmed basis (a DocumentAccessRule row exists: reported ALL or
RESTRICTED access for v3/v4/v6/v10/v11/v13/v14/v16). Never guesses true
for anything unconfirmed. The 11 rows needing v2/chunk2 specifically are
recorded false, since v2 is confirmed (by code, see audit README) to
have no DocumentAccessRule row at all -> excluded for every user before
role evaluation ever runs.
"""

import json

MANIFEST_PATH = "audit_manifest.jsonl"
OUT_PATH = "runtime_access_snapshot.jsonl"
SNAPSHOT_DATE = "2026-09-10"

# Versions confirmed (2026-09-09/10, A-dam-dangja read-only DB check +
# 2026-09-10 backend code review) to have an actual DocumentAccessRule
# row configured (ALL or RESTRICTED alike -- both mean "a rule exists").
CONFIRMED_CONFIGURED_VERSION_IDS = {3, 4, 6, 10, 11, 13, 14, 16}

# v2 confirmed (code-level, DocumentAccessScopeService +
# DocumentAccessRule.access_scope NOT NULL constraint) to have no rule
# row at all -> excluded for every user, before role evaluation.
NO_RULE_VERSION_IDS = {2}


def assess(required_version_ids):
    if not required_version_ids:
        # Negative row: no specific evidence is required, so there is
        # nothing for an access gap to block. Evaluable regardless.
        return True, None

    blocked_on = NO_RULE_VERSION_IDS.intersection(required_version_ids)
    if blocked_on:
        return False, "NO_DOCUMENT_ACCESS_RULE"

    unconfirmed = set(required_version_ids) - CONFIRMED_CONFIGURED_VERSION_IDS
    if unconfirmed:
        # Never guess true for something we have not actually confirmed.
        return False, "UNCONFIRMED_ACCESS_CONFIG"

    return True, None


def main():
    with open(MANIFEST_PATH, encoding="utf-8") as f:
        audit_rows = [json.loads(line) for line in f]

    counts = {"true": 0, "false_no_rule": 0, "false_unconfirmed": 0}
    with open(OUT_PATH, "w", encoding="utf-8") as out:
        for row in audit_rows:
            required = row["current_expected_document_version_ids"] or []
            retrievable, reason = assess(required)
            if retrievable:
                counts["true"] += 1
            elif reason == "NO_DOCUMENT_ACCESS_RULE":
                counts["false_no_rule"] += 1
            else:
                counts["false_unconfirmed"] += 1

            record = {
                "id": row["id"],
                "snapshotDate": SNAPSHOT_DATE,
                "retrievableUnderCurrentAccessConfig": retrievable,
                "blockingReason": reason,
                "requiredDocumentVersionIds": required,
            }
            out.write(json.dumps(record, ensure_ascii=False) + "\n")

    print("Rows:", len(audit_rows))
    print("RETRIEVABLE (true):", counts["true"])
    print("ACCESS_BLOCKED - NO_DOCUMENT_ACCESS_RULE:", counts["false_no_rule"])
    print("ACCESS_BLOCKED - UNCONFIRMED_ACCESS_CONFIG:", counts["false_unconfirmed"])


if __name__ == "__main__":
    main()
