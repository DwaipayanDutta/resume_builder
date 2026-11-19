import { z } from "zod";

export const verifiableSchema = z.object({
  value: z.string().default(""),
  source: z.enum(["user_provided", "ai_generated", "placeholder"]).default("user_provided"),
  verification_status: z.enum(["verified", "flagged", "pending"]).default("verified"),
});

export const contactInfoSchema = z.object({
  name: verifiableSchema.default({ value: "", source: "user_provided", verification_status: "verified" }),
  email: verifiableSchema.optional(),
  phone: verifiableSchema.optional(),
  linkedin: verifiableSchema.optional(),
  location: verifiableSchema.optional(),
});

export const experienceSchema = z.object({
  company: verifiableSchema.default({ value: "", source: "user_provided", verification_status: "verified" }),
  title: verifiableSchema.default({ value: "", source: "user_provided", verification_status: "verified" }),
  start_date: verifiableSchema.default({ value: "", source: "user_provided", verification_status: "verified" }),
  end_date: verifiableSchema.default({ value: "Present", source: "user_provided", verification_status: "verified" }),
  bullets: z.array(verifiableSchema).default([]),
  included: z.boolean().default(true),
});

export const projectSchema = z.object({
  name: verifiableSchema.default({ value: "", source: "user_provided", verification_status: "verified" }),
  description: verifiableSchema.optional(),
  bullets: z.array(verifiableSchema).default([]),
  included: z.boolean().default(true),
});

export const educationSchema = z.object({
  institution: verifiableSchema.default({ value: "", source: "user_provided", verification_status: "verified" }),
  degree: verifiableSchema.default({ value: "", source: "user_provided", verification_status: "verified" }),
  details: z.array(verifiableSchema).default([]),
  included: z.boolean().default(true),
});

export const customSectionSchema = z.object({
  name: z.string().default(""),
  items: z.array(verifiableSchema).default([]),
  included: z.boolean().default(true),
});

export const resumeSchema = z.object({
  contact: contactInfoSchema.default({
    name: { value: "", source: "user_provided", verification_status: "verified" },
  }),
  summary: verifiableSchema.optional(),
  experience: z.array(experienceSchema).default([]),
  projects: z.array(projectSchema).default([]),
  education: z.array(educationSchema).default([]),
  skills: z.array(verifiableSchema).default([]),
  certifications: z.array(verifiableSchema).default([]),
  custom_sections: z.array(customSectionSchema).default([]),
  section_order: z.array(z.string()).default([
    "summary", "experience", "projects", "education", "skills", "certifications",
  ]),
  template_id: z.string().default("ats_classic"),
});

export type VerifiableField = z.infer<typeof verifiableSchema>;
export type ContactInfo = z.infer<typeof contactInfoSchema>;
export type Experience = z.infer<typeof experienceSchema>;
export type Project = z.infer<typeof projectSchema>;
export type Education = z.infer<typeof educationSchema>;
export type CustomSection = z.infer<typeof customSectionSchema>;
export type Resume = z.infer<typeof resumeSchema>;

export function createDefaultVerifiable(value = ""): VerifiableField {
  return {
    value,
    source: "user_provided",
    verification_status: "verified",
  };
}

export function createDefaultResume(): Resume {
  return {
    contact: {
      name: createDefaultVerifiable(""),
      email: createDefaultVerifiable(""),
      phone: createDefaultVerifiable(""),
      linkedin: createDefaultVerifiable(""),
      location: createDefaultVerifiable(""),
    },
    summary: createDefaultVerifiable(""),
    experience: [],
    projects: [],
    education: [],
    skills: [],
    certifications: [],
    custom_sections: [],
    section_order: ["summary", "experience", "projects", "education", "skills", "certifications"],
    template_id: "ats_classic",
  };
}
