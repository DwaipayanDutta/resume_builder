from __future__ import annotations
import json
import re
from typing import Protocol
from ..models.resume import ResumeData, VerifiableField, Source


class LLMBackend(Protocol):
    def complete(self, prompt: str) -> str: ...


def _build_prompt(master: ResumeData, job_description: str) -> str:
    master_json = master.model_dump_json(indent=2)
    return f"""You are a resume tailoring engine. Rewrite the resume to better match the job description.

STRICT RULES:
- You may ONLY use employers, titles, dates, degrees, and projects that appear in MASTER below.
- You may rephrase bullets, reorder them, select a subset, and adjust emphasis.
- You may NOT invent new employers, dates, degrees, certifications, or metrics.
- If a bullet would benefit from a metric that does not exist in MASTER, keep the text without the metric and append [ADD METRIC].
- Return ONLY valid JSON matching the ResumeData schema. No markdown fences.

JOB DESCRIPTION:
{job_description}

MASTER:
{master_json}
"""


def _extract_json(text: str) -> dict:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("No JSON object found in model response")
    return json.loads(text[start:end + 1])


def tailor_resume(
    master: ResumeData,
    job_description: str,
    backend: LLMBackend,
) -> ResumeData:
    raw = backend.complete(_build_prompt(master, job_description))
    data = _extract_json(raw)
    tailored = ResumeData.model_validate(data)

    # Force restore identity fields that must not be changed by AI
    tailored.contact = master.contact
    for i, exp in enumerate(tailored.experience):
        if i < len(master.experience):
            exp.company = master.experience[i].company
            exp.start_date = master.experience[i].start_date
    for field in [tailored.summary] if tailored.summary else []:
        field.source = Source.AI
    for exp in tailored.experience:
        for b in exp.bullets:
            b.source = Source.AI
    return tailored
