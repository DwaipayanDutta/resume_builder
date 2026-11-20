import { z } from "zod";

export const verifiableSchema = z.object({
  value: z.string().default(""),
  source: z.enum(["user_provided", "ai_generated", "placeholder"]).default("user_provided"),
  verification_status: z.enum(["verified", "flagged", "pending"]).default("verified"),
});

export const experienceSchema = z.object({
  company: verifiableSchema,
  title: verifiableSchema,
  start_date: verifiableSchema,
  end_date: verifiableSchema,
  bullets: z.array(verifiableSchema).default([]),
  included: z.boolean().default(true),
});

export const resumeSchema = z.object({
  contact: z.object({
    name: verifiableSchema,
    email: verifiableSchema.optional(),
    phone: verifiableSchema.optional(),
    linkedin: verifiableSchema.optional(),
    location: verifiableSchema.optional(),
  }),
  summary: verifiableSchema.optional(),
  experience: z.array(experienceSchema).default([]),
  projects: z.array(z.any()).default([]),
  education: z.array(z.any()).default([]),
  skills: z.array(verifiableSchema).default([]),
  certifications: z.array(verifiableSchema).default([]),
  custom_sections: z.array(z.any()).default([]),
  section_order: z.array(z.string()).default([
    "summary", "experience", "projects", "education", "skills", "certifications",
  ]),
  template_id: z.string().default("ats_classic"),
});

export type Resume = z.infer<typeof resumeSchema>;