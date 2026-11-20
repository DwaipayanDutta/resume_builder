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
    返回一个副本：每条 AI 生成的字段都被标记为 verified / flagged / pending。
    flagged 的字段会被前端高亮，用户在导出前必须逐条确认或编辑。
    """
    result = deepcopy(tailored)
    master_text = master.model_dump_json()

    def inspect(field: VerifiableField, label: str) -> None:
        if field.source != Source.AI:
            return
        if not field.value.strip():
            field.verification_status = VerificationStatus.PENDING
            return
        # 数字必须在原始档案中出现，或标记为待核实
        for num in _METRIC_RE.findall(field.value):
            if num not in master_text:
                field.verification_status = VerificationStatus.FLAGGED
                return
        # 非数字内容：如果整句完全未在原始数据中出现，标记待核实
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