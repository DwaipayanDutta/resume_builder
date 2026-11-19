from __future__ import annotations
import re
from copy import deepcopy
from ..models.resume import (
    ResumeData, VerifiableField, Source, VerificationStatus,
)

_METRIC_RE = re.compile(r"\b\d+(?:\.\d+)?%?\b")


def _normalize(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip().lower())


def _in_original(value: str, original_text: str) -> bool:
    return _normalize(value) in _normalize(original_text)


def check_tailored(tailored: ResumeData, master: ResumeData) -> ResumeData:
    """
    Returns a copy where every AI-generated field is inspected:
    marked as verified, flagged, or pending.
    Flagged fields are highlighted in the frontend and must be confirmed.
    """
    result = deepcopy(tailored)
    master_text = master.model_dump_json()

    def inspect(field: VerifiableField, label: str) -> None:
        if field.source != Source.AI:
            return
        if not field.value.strip():
            field.verification_status = VerificationStatus.PENDING
            return
        # Numbers must appear in the original profile, otherwise flagged
        for num in _METRIC_RE.findall(field.value):
            if num not in master_text:
                field.verification_status = VerificationStatus.FLAGGED
                return
        # Non-numeric content: if entire sentence is not in original text, mark pending
        if len(field.value) > 40 and not _in_original(field.value, master_text):
            field.verification_status = VerificationStatus.PENDING
        else:
            field.verification_status = VerificationStatus.VERIFIED

    for exp in result.experience:
        for f in (exp.company, exp.title, exp.start_date, exp.end_date):
            inspect(f, "experience")
        for b in exp.bullets:
            inspect(b, "experience_bullet")
    for proj in result.projects:
        for b in proj.bullets:
            inspect(b, "project_bullet")
    if result.summary:
        inspect(result.summary, "summary")
    for s in result.skills:
        inspect(s, "skill")
    return result
