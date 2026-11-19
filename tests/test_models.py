import json
import pytest
from pydantic import ValidationError
from resume_builder.models.resume import (
    ResumeData,
    VerifiableField,
    Source,
    VerificationStatus,
    ContactInfo,
    Experience,
    Education,
    Project,
)
from resume_builder.verification.fact_checker import check_tailored


def test_resume_data_defaults():
    resume = ResumeData()
    assert resume.contact.name.value == ""
    assert resume.contact.name.source == Source.USER
    assert resume.contact.name.verification_status == VerificationStatus.VERIFIED
    assert resume.section_order == ["summary", "experience", "projects", "education", "skills", "certifications"]
    assert resume.template_id == "ats_classic"


def test_resume_data_serialization():
    resume = ResumeData(
        contact=ContactInfo(
            name=VerifiableField(value="Alex Morgan"),
            email=VerifiableField(value="alex@example.com"),
        ),
        summary=VerifiableField(value="Experienced AI Engineer"),
        experience=[
            Experience(
                company=VerifiableField(value="Acme Corp"),
                title=VerifiableField(value="Staff Engineer"),
                start_date=VerifiableField(value="01/2020"),
                end_date=VerifiableField(value="Present"),
                bullets=[
                    VerifiableField(value="Built platform scaling to 10M users."),
                ],
            )
        ],
        skills=[VerifiableField(value="Python"), VerifiableField(value="FastAPI")],
    )

    data = resume.model_dump()
    assert data["contact"]["name"]["value"] == "Alex Morgan"
    assert len(data["experience"]) == 1
    assert data["experience"][0]["company"]["value"] == "Acme Corp"

    # Validate JSON round-trip
    json_str = resume.model_dump_json()
    loaded = ResumeData.model_validate_json(json_str)
    assert loaded.contact.name.value == "Alex Morgan"


def test_fact_checker_flags_new_metrics():
    master = ResumeData(
        contact=ContactInfo(name=VerifiableField(value="Alex")),
        experience=[
            Experience(
                company=VerifiableField(value="Acme"),
                title=VerifiableField(value="Dev"),
                start_date=VerifiableField(value="2020"),
                end_date=VerifiableField(value="2022"),
                bullets=[
                    VerifiableField(value="Improved latency by 15%."),
                ],
            )
        ],
    )

    # Tailored contains a fabricated metric 99%
    tailored = ResumeData(
        contact=ContactInfo(name=VerifiableField(value="Alex")),
        experience=[
            Experience(
                company=VerifiableField(value="Acme"),
                title=VerifiableField(value="Dev"),
                start_date=VerifiableField(value="2020"),
                end_date=VerifiableField(value="2022"),
                bullets=[
                    VerifiableField(value="Improved latency by 15%.", source=Source.AI),
                    VerifiableField(value="Increased revenue by 99%.", source=Source.AI),
                ],
            )
        ],
    )

    checked = check_tailored(tailored, master)
    # The 15% metric exists in master, so it is verified
    assert checked.experience[0].bullets[0].verification_status == VerificationStatus.VERIFIED
    # The 99% metric does not exist in master, so it must be flagged
    assert checked.experience[0].bullets[1].verification_status == VerificationStatus.FLAGGED
