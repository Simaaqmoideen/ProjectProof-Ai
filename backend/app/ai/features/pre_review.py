"""Submission pre-review AI feature — FR-EVL-3.

LLM checks whether submitted work satisfies each checklist item.
See docs/06-ai-modules-specification.md section 6.4.
"""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.ai import client as ai_client
from app.ai.schemas import PreReviewItem, PreReviewOutput

_MAX_SOURCE_CHARS = 30_000
_FEATURE = "pre_review"
_PROMPT_VERSION = "v1"


def review(
    *,
    db: Session,
    user_id: uuid.UUID,
    checklist: list[str],
    file_tree: list[str],
    readme: str,
    source_sample: str,
    company_notes: str = "",
) -> dict:
    """Pre-review a submission against its project's deliverables checklist.

    Checks (sec 6.4):
    - number of returned items must equal len(checklist)
    - every evidence and file must exist in supplied material; otherwise mark unclear
    """
    import json

    # Bound total source input
    combined_source = source_sample[:_MAX_SOURCE_CHARS]
    supplied_files = set(file_tree)
    input_text = f"{readme}\n{combined_source}"

    variables = {
        "CHECKLIST": json.dumps(checklist),
        "FILE_TREE": json.dumps(file_tree),
        "README": readme[:2000],
        "SOURCE": combined_source,
        "COMPANY_NOTES": company_notes[:500],
    }

    raw_result = ai_client.run(
        db=db,
        user_id=user_id,
        feature=_FEATURE,
        prompt_version=_PROMPT_VERSION,
        variables=variables,
        output_model=PreReviewOutput,
        input_text=input_text,
    )

    output: PreReviewOutput = raw_result["result"]

    # Align items with checklist length
    verified_items: list[dict] = []
    for i, checklist_item in enumerate(checklist):
        if i < len(output.items):
            item = output.items[i]
            # Check: file must exist in supplied file_tree
            file_ok = not item.file or item.file in supplied_files
            # Check: evidence must have some grounding in supplied text
            evidence_ok = (
                item.evidence.lower()[:30] in input_text.lower() if item.evidence else False
            )
            if not file_ok or not evidence_ok:
                verified_items.append(
                    PreReviewItem(
                        checklist_item=checklist_item,
                        status="unclear",
                        evidence=item.evidence,
                        file=item.file,
                    ).model_dump()
                )
            else:
                verified_items.append(
                    PreReviewItem(
                        checklist_item=checklist_item,
                        status=item.status,
                        evidence=item.evidence,
                        file=item.file,
                    ).model_dump()
                )
        else:
            # Missing item from LLM — mark unclear
            verified_items.append(
                PreReviewItem(
                    checklist_item=checklist_item,
                    status="unclear",
                    evidence="Not assessed by AI.",
                    file="",
                ).model_dump()
            )

    met_count = sum(1 for it in verified_items if it["status"] == "met")
    check_pass_rate = len([it for it in verified_items if it["status"] != "unclear"]) / max(
        len(checklist), 1
    )

    return {
        "ai": raw_result["ai"],
        "result": {
            "items": verified_items,
            "overall_note": output.overall_note,
            "summary": f"AI draft: {met_count} of {len(checklist)} checklist items met.",
        },
        "_check_pass_rate": check_pass_rate,
    }
