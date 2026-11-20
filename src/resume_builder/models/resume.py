from __future__ import annotations
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class Source(str, Enum):
    USER = "user_provided"
    AI = "ai_generated"
    PLACEHOLDER = "placeholder"


class VerificationStatus(str, Enum):
    VERIFIED = "verified"
    FLAGGED = "flagged"
    PENDING = "pending"


class VerifiableField(BaseModel):
    value: str = ""
    source: Source = Source.USER
    verification_status: VerificationStatus = VerificationStatus.VERIFIED


class ContactInfo(BaseModel):
    name: VerifiableField = Field(default_factory=lambda: VerifiableField(value=""))
    email: Optional[VerifiableField] = None
    phone: Optional[VerifiableField] = None
    linkedin: Optional[VerifiableField] = None
    location: Optional[VerifiableField] = None


class Experience(BaseModel):
    company: VerifiableField = Field(default_factory=lambda: VerifiableField(value=""))
    title: VerifiableField = Field(default_factory=lambda: VerifiableField(value=""))
    start_date: VerifiableField = Field(default_factory=lambda: VerifiableField(value=""))
    end_date: VerifiableField = Field(default_factory=lambda: VerifiableField(value="Present"))
    bullets: list[VerifiableField] = Field(default_factory=list)
    included: bool = True  # Included status for rendering/export


class Project(BaseModel):
    name: VerifiableField = Field(default_factory=lambda: VerifiableField(value=""))
    description: Optional[VerifiableField] = None
    bullets: list[VerifiableField] = Field(default_factory=list)
    included: bool = True


class Education(BaseModel):
    institution: VerifiableField = Field(default_factory=lambda: VerifiableField(value=""))
    degree: VerifiableField = Field(default_factory=lambda: VerifiableField(value=""))
    details: list[VerifiableField] = Field(default_factory=list)
    included: bool = True


class CustomSection(BaseModel):
    name: str = ""
    items: list[VerifiableField] = Field(default_factory=list)
    included: bool = True


class ResumeData(BaseModel):
    contact: ContactInfo = Field(default_factory=ContactInfo)
    summary: Optional[VerifiableField] = None
    experience: list[Experience] = Field(default_factory=list)
    projects: list[Project] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    skills: list[VerifiableField] = Field(default_factory=list)
    certifications: list[VerifiableField] = Field(default_factory=list)
    custom_sections: list[CustomSection] = Field(default_factory=list)
    section_order: list[str] = Field(
        default_factory=lambda: [
            "summary", "experience", "projects", "education", "skills", "certifications"
        ]
    )
    template_id: str = "ats_classic"
