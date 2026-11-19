import React from "react";
import {
  DndContext,
  closestCenter,
  PointerSensor,
  useSensor,
  useSensors,
} from "@dnd-kit/core";
import {
  SortableContext,
  verticalListSortingStrategy,
  useSortable,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { useResumeStore } from "../store";

// ---------------------------------------------------------------------------
// Draggable Bullet Component
// ---------------------------------------------------------------------------
interface SortableBulletProps {
  id: string;
  value: string;
  flagged: boolean;
  onChange: (v: string) => void;
  onDelete: () => void;
}

function SortableBullet({
  id,
  value,
  flagged,
  onChange,
  onDelete,
}: SortableBulletProps) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } =
    useSortable({ id });

  return (
    <div
      ref={setNodeRef}
      style={{
        transform: CSS.Transform.toString(transform),
        transition,
        opacity: isDragging ? 0.4 : 1,
      }}
      className={`bullet-row ${flagged ? "flagged" : ""}`}
    >
      <button
        type="button"
        className="drag-handle"
        {...attributes}
        {...listeners}
        aria-label="Drag to reorder bullet"
      >
        ⋮⋮
      </button>
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        rows={2}
        className="bullet-textarea"
        placeholder="Describe an achievement or responsibility..."
      />
      <button
        type="button"
        className="btn-icon btn-danger"
        onClick={onDelete}
        title="Delete bullet"
        aria-label="Delete bullet"
      >
        ✕
      </button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Experience Form
// ---------------------------------------------------------------------------
export function ExperienceSectionForm() {
  const experience = useResumeStore((s) => s.resume.experience);
  const addExperience = useResumeStore((s) => s.addExperience);
  const deleteExperience = useResumeStore((s) => s.deleteExperience);
  const updateExperienceField = useResumeStore((s) => s.updateExperienceField);
  const toggleIncluded = useResumeStore((s) => s.toggleExperienceIncluded);
  const addBullet = useResumeStore((s) => s.addBullet);
  const deleteBullet = useResumeStore((s) => s.deleteBullet);
  const updateBullet = useResumeStore((s) => s.updateBullet);
  const reorderBullets = useResumeStore((s) => s.reorderBullets);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } })
  );

  return (
    <div className="section-form experience-form">
      <div className="section-header">
        <h3>Work Experience</h3>
        <button type="button" className="btn btn-primary" onClick={addExperience}>
          + Add Role
        </button>
      </div>

      {experience.length === 0 ? (
        <div className="empty-state">
          <p>No work experience added yet.</p>
          <button type="button" className="btn btn-secondary" onClick={addExperience}>
            Add First Role
          </button>
        </div>
      ) : (
        experience.map((exp, expIdx) => (
          <div key={expIdx} className={`card entry-card ${!exp.included ? "excluded" : ""}`}>
            <div className="entry-header">
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  checked={exp.included}
                  onChange={() => toggleIncluded(expIdx)}
                />
                Include in resume
              </label>
              <button
                type="button"
                className="btn-danger btn-sm"
                onClick={() => deleteExperience(expIdx)}
              >
                Delete Role
              </button>
            </div>

            <div className="grid-2">
              <div className="form-group">
                <label>Job Title</label>
                <input
                  type="text"
                  value={exp.title.value}
                  onChange={(e) =>
                    updateExperienceField(expIdx, "title", e.target.value)
                  }
                  placeholder="e.g. Senior Software Engineer"
                />
              </div>
              <div className="form-group">
                <label>Company</label>
                <input
                  type="text"
                  value={exp.company.value}
                  onChange={(e) =>
                    updateExperienceField(expIdx, "company", e.target.value)
                  }
                  placeholder="e.g. Acme Systems"
                />
              </div>
            </div>

            <div className="grid-2">
              <div className="form-group">
                <label>Start Date</label>
                <input
                  type="text"
                  value={exp.start_date.value}
                  onChange={(e) =>
                    updateExperienceField(expIdx, "start_date", e.target.value)
                  }
                  placeholder="e.g. 03/2021"
                />
              </div>
              <div className="form-group">
                <label>End Date</label>
                <input
                  type="text"
                  value={exp.end_date.value}
                  onChange={(e) =>
                    updateExperienceField(expIdx, "end_date", e.target.value)
                  }
                  placeholder="e.g. Present"
                />
              </div>
            </div>

            <div className="bullets-section">
              <div className="bullets-header">
                <label>Bullet Points (Drag ⋮⋮ to reorder)</label>
                <button
                  type="button"
                  className="btn-link"
                  onClick={() => addBullet(expIdx, "")}
                >
                  + Add Bullet
                </button>
              </div>

              <DndContext
                sensors={sensors}
                collisionDetection={closestCenter}
                onDragEnd={({ active, over }) => {
                  if (!over || active.id === over.id) return;
                  const from = exp.bullets.findIndex((_, i) => `exp-${expIdx}-b-${i}` === active.id);
                  const to = exp.bullets.findIndex((_, i) => `exp-${expIdx}-b-${i}` === over.id);
                  if (from !== -1 && to !== -1) {
                    reorderBullets(expIdx, from, to);
                  }
                }}
              >
                <SortableContext
                  items={exp.bullets.map((_, i) => `exp-${expIdx}-b-${i}`)}
                  strategy={verticalListSortingStrategy}
                >
                  {exp.bullets.map((b, bIdx) => (
                    <SortableBullet
                      key={bIdx}
                      id={`exp-${expIdx}-b-${bIdx}`}
                      value={b.value}
                      flagged={b.verification_status === "flagged"}
                      onChange={(val) => updateBullet(expIdx, bIdx, val)}
                      onDelete={() => deleteBullet(expIdx, bIdx)}
                    />
                  ))}
                </SortableContext>
              </DndContext>
            </div>
          </div>
        ))
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Summary Form
// ---------------------------------------------------------------------------
export function SummarySectionForm() {
  const summary = useResumeStore((s) => s.resume.summary?.value ?? "");
  const isFlagged = useResumeStore(
    (s) => s.resume.summary?.verification_status === "flagged"
  );
  const updateSummary = useResumeStore((s) => s.updateSummary);

  return (
    <div className="section-form summary-form">
      <div className="section-header">
        <h3>Professional Summary</h3>
      </div>
      <div className="form-group">
        <label>Executive Summary (3–4 sentences)</label>
        <textarea
          rows={5}
          className={`summary-textarea ${isFlagged ? "flagged" : ""}`}
          value={summary}
          onChange={(e) => updateSummary(e.target.value)}
          placeholder="Briefly highlight your core expertise, career highlights, and top achievements..."
        />
        {isFlagged && (
          <span className="badge-warning">Flagged by fact-checker for review</span>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Contact Form
// ---------------------------------------------------------------------------
export function ContactSectionForm() {
  const contact = useResumeStore((s) => s.resume.contact);
  const updateContact = useResumeStore((s) => s.updateContact);

  return (
    <div className="section-form contact-form">
      <div className="section-header">
        <h3>Contact Information</h3>
      </div>
      <div className="form-group">
        <label>Full Name</label>
        <input
          type="text"
          value={contact.name.value}
          onChange={(e) => updateContact("name", e.target.value)}
          placeholder="e.g. Alex Morgan"
        />
      </div>
      <div className="grid-2">
        <div className="form-group">
          <label>Email</label>
          <input
            type="email"
            value={contact.email?.value ?? ""}
            onChange={(e) => updateContact("email", e.target.value)}
            placeholder="e.g. alex@example.com"
          />
        </div>
        <div className="form-group">
          <label>Phone</label>
          <input
            type="tel"
            value={contact.phone?.value ?? ""}
            onChange={(e) => updateContact("phone", e.target.value)}
            placeholder="e.g. +1 555-0100"
          />
        </div>
      </div>
      <div className="grid-2">
        <div className="form-group">
          <label>Location</label>
          <input
            type="text"
            value={contact.location?.value ?? ""}
            onChange={(e) => updateContact("location", e.target.value)}
            placeholder="e.g. San Francisco, CA"
          />
        </div>
        <div className="form-group">
          <label>LinkedIn / Portfolio URL</label>
          <input
            type="text"
            value={contact.linkedin?.value ?? ""}
            onChange={(e) => updateContact("linkedin", e.target.value)}
            placeholder="e.g. https://linkedin.com/in/alex-morgan"
          />
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Education Form
// ---------------------------------------------------------------------------
export function EducationSectionForm() {
  const education = useResumeStore((s) => s.resume.education);
  const addEducation = useResumeStore((s) => s.addEducation);
  const deleteEducation = useResumeStore((s) => s.deleteEducation);
  const updateEducationField = useResumeStore((s) => s.updateEducationField);
  const toggleIncluded = useResumeStore((s) => s.toggleEducationIncluded);

  return (
    <div className="section-form education-form">
      <div className="section-header">
        <h3>Education</h3>
        <button type="button" className="btn btn-primary" onClick={addEducation}>
          + Add Education
        </button>
      </div>

      {education.length === 0 ? (
        <div className="empty-state">
          <p>No education entries added yet.</p>
          <button type="button" className="btn btn-secondary" onClick={addEducation}>
            Add First Entry
          </button>
        </div>
      ) : (
        education.map((edu, idx) => (
          <div key={idx} className={`card entry-card ${!edu.included ? "excluded" : ""}`}>
            <div className="entry-header">
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  checked={edu.included}
                  onChange={() => toggleIncluded(idx)}
                />
                Include in resume
              </label>
              <button
                type="button"
                className="btn-danger btn-sm"
                onClick={() => deleteEducation(idx)}
              >
                Delete Entry
              </button>
            </div>

            <div className="grid-2">
              <div className="form-group">
                <label>Degree / Certificate</label>
                <input
                  type="text"
                  value={edu.degree.value}
                  onChange={(e) => updateEducationField(idx, "degree", e.target.value)}
                  placeholder="e.g. B.S. in Computer Science"
                />
              </div>
              <div className="form-group">
                <label>Institution / University</label>
                <input
                  type="text"
                  value={edu.institution.value}
                  onChange={(e) =>
                    updateEducationField(idx, "institution", e.target.value)
                  }
                  placeholder="e.g. Stanford University"
                />
              </div>
            </div>
          </div>
        ))
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Skills Form
// ---------------------------------------------------------------------------
export function SkillsSectionForm() {
  const skills = useResumeStore((s) => s.resume.skills);
  const addSkill = useResumeStore((s) => s.addSkill);
  const deleteSkill = useResumeStore((s) => s.deleteSkill);
  const updateSkill = useResumeStore((s) => s.updateSkill);
  const [newSkillText, setNewSkillText] = React.useState("");

  const handleAdd = (e: React.FormEvent) => {
    e.preventDefault();
    if (newSkillText.trim()) {
      addSkill(newSkillText.trim());
      setNewSkillText("");
    }
  };

  return (
    <div className="section-form skills-form">
      <div className="section-header">
        <h3>Skills & Competencies</h3>
      </div>

      <form onSubmit={handleAdd} className="add-skill-form">
        <input
          type="text"
          value={newSkillText}
          onChange={(e) => setNewSkillText(e.target.value)}
          placeholder="Type a skill and press Enter (e.g. Python, Docker)..."
        />
        <button type="submit" className="btn btn-primary">
          Add Skill
        </button>
      </form>

      <div className="skills-grid">
        {skills.map((skill, idx) => (
          <div key={idx} className="skill-chip">
            <input
              type="text"
              value={skill.value}
              onChange={(e) => updateSkill(idx, e.target.value)}
              className="skill-input"
            />
            <button
              type="button"
              className="skill-delete"
              onClick={() => deleteSkill(idx)}
              aria-label="Remove skill"
            >
              ✕
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Master Section Form Router
// ---------------------------------------------------------------------------
export function SectionForm() {
  const selected = useResumeStore((s) => s.selectedSection);

  switch (selected) {
    case "contact":
      return <ContactSectionForm />;
    case "summary":
      return <SummarySectionForm />;
    case "experience":
      return <ExperienceSectionForm />;
    case "education":
      return <EducationSectionForm />;
    case "skills":
      return <SkillsSectionForm />;
    default:
      return <ExperienceSectionForm />;
  }
}
