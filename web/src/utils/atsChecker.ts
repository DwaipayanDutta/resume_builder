import type { Resume } from "../schemas";

export interface KeywordMatchResult {
  term: string;
  isCritical: boolean;
  isMatched: boolean;
}

export interface AtsChecklistReport {
  keywords: {
    total: number;
    matchedCount: number;
    missingCount: number;
    items: KeywordMatchResult[];
  };
  pageCount: {
    pages: number;
    isOptimal: boolean;
    message: string;
  };
  actionVerbs: {
    totalBullets: number;
    verbBullets: number;
    isOptimal: boolean;
    percentage: number;
  };
  placeholders: {
    count: number;
    items: string[];
    isResolved: boolean;
  };
}

export const COMMON_ACTION_VERBS = new Set([
  "accelerated", "achieved", "analyzed", "architected", "automated", "built",
  "championed", "collaborated", "constructed", "created", "decreased", "delivered",
  "deployed", "designed", "developed", "devised", "directed", "drove",
  "engineered", "established", "executed", "expanded", "expedited", "formulated",
  "generated", "guided", "implemented", "improved", "increased", "initiated",
  "instituted", "integrated", "introduced", "launched", "lead", "led",
  "leveraged", "managed", "maximized", "mentored", "migrated", "minimized",
  "modernized", "negotiated", "operated", "optimized", "orchestrated", "organized",
  "overhauled", "oversaw", "partnered", "pioneered", "planned", "produced",
  "reduced", "refactored", "resolved", "restructured", "revamped", "saved",
  "scaled", "simplified", "spearheaded", "standardized", "streamlined", "supervised",
  "trained", "transformed", "unified", "upgraded", "validated",
]);

const STOP_WORDS = new Set([
  "about", "above", "across", "after", "again", "against", "all", "almost", "along",
  "also", "although", "always", "among", "and", "another", "any", "are", "around",
  "because", "been", "before", "being", "below", "between", "both", "but", "came",
  "can", "cannot", "come", "could", "did", "does", "doing", "done", "down", "during",
  "each", "early", "either", "else", "even", "ever", "every", "few", "first", "for",
  "from", "further", "had", "has", "have", "having", "here", "how", "into", "its",
  "just", "like", "made", "make", "many", "more", "most", "much", "must", "name",
  "next", "not", "now", "off", "often", "once", "one", "only", "other", "our", "out",
  "over", "own", "part", "per", "same", "see", "several", "shall", "she", "should",
  "since", "some", "still", "such", "than", "that", "the", "their", "them", "then",
  "there", "these", "they", "this", "those", "through", "too", "under", "until", "upon",
  "use", "used", "using", "very", "want", "was", "way", "well", "were", "what", "when",
  "where", "which", "while", "who", "whom", "will", "with", "would", "you", "your",
  "role", "team", "work", "job", "candidate", "responsibilities", "requirements",
  "qualifications", "experience", "years", "skills", "ability", "strong", "plus",
]);

export function extractJobKeywords(jobDescription: string): { term: string; isCritical: boolean }[] {
  if (!jobDescription || !jobDescription.trim()) return [];

  const lines = jobDescription.split(/[\r\n]+/);
  const keywordMap = new Map<string, boolean>();

  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed) continue;

    // A requirement is only labeled "critical" if the line explicitly contains critical indicators
    const isLineCritical = /\b(required|must[- ]have|mandatory|essential|minimum qualifications?|strictly required)\b/i.test(
      trimmed
    );

    // Extract word tokens of length >= 3
    const tokens = trimmed.toLowerCase().match(/\b[a-z0-9+#.-]{3,}\b/g) || [];

    for (const token of tokens) {
      const clean = token.replace(/^[.-]+|[.-]+$/g, "");
      if (clean.length < 3 || STOP_WORDS.has(clean) || /^\d+$/.test(clean)) {
        continue;
      }

      // If already recorded as critical, preserve critical status
      const existing = keywordMap.get(clean);
      if (existing === true) {
        continue;
      }
      keywordMap.set(clean, isLineCritical);
    }
  }

  return Array.from(keywordMap.entries()).map(([term, isCritical]) => ({
    term,
    isCritical,
  }));
}

export function getAllResumeText(resume: Resume): string {
  const parts: string[] = [];

  if (resume.contact) {
    if (resume.contact.name?.value) parts.push(resume.contact.name.value);
    if (resume.contact.location?.value) parts.push(resume.contact.location.value);
  }

  if (resume.summary?.value) {
    parts.push(resume.summary.value);
  }

  for (const exp of resume.experience || []) {
    if (!exp.included) continue;
    if (exp.title?.value) parts.push(exp.title.value);
    if (exp.company?.value) parts.push(exp.company.value);
    for (const b of exp.bullets || []) {
      if (b.value) parts.push(b.value);
    }
  }

  for (const edu of resume.education || []) {
    if (!edu.included) continue;
    if (edu.institution?.value) parts.push(edu.institution.value);
    if (edu.degree?.value) parts.push(edu.degree.value);
  }

  for (const skill of resume.skills || []) {
    if (skill.value) parts.push(skill.value);
  }

  return parts.join(" ").toLowerCase();
}

export function checkPlaceholders(resume: Resume): string[] {
  const allText = getAllResumeText(resume);
  const placeholderRegex = /\[(?:ADD\s+METRIC|ADD[^\]]*|TODO[^\]]*|METRIC[^\]]*)\]/gi;
  const matches = allText.match(placeholderRegex) || [];
  return matches.map((m) => m.toUpperCase());
}

export function checkActionVerbs(resume: Resume): { total: number; withVerb: number; percentage: number } {
  let total = 0;
  let withVerb = 0;

  for (const exp of resume.experience || []) {
    if (!exp.included) continue;
    for (const b of exp.bullets || []) {
      const trimmed = b.value.trim();
      if (!trimmed) continue;
      total++;
      const firstWord = (trimmed.match(/^[A-Za-z]+/)?.[0] || "").toLowerCase();
      if (COMMON_ACTION_VERBS.has(firstWord)) {
        withVerb++;
      }
    }
  }

  const percentage = total > 0 ? Math.round((withVerb / total) * 100) : 100;
  return { total, withVerb, percentage };
}

export function evaluateAtsChecklist(
  resume: Resume,
  jobDescription: string,
  renderedPageCount: number
): AtsChecklistReport {
  // 1. Keywords
  const extracted = extractJobKeywords(jobDescription);
  const resumeText = getAllResumeText(resume);

  const keywordItems: KeywordMatchResult[] = extracted.map(({ term, isCritical }) => {
    // Regex boundary check where possible
    const escaped = term.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    const regex = new RegExp(`(^|[^a-z0-9])${escaped}([^a-z0-9]|$)`, "i");
    const isMatched = regex.test(resumeText);
    return {
      term,
      isCritical,
      isMatched,
    };
  });

  const matchedCount = keywordItems.filter((k) => k.isMatched).length;
  const missingCount = keywordItems.length - matchedCount;

  // 2. Page count (using actual rendered result from Python service)
  const isOptimalPage = renderedPageCount >= 1 && renderedPageCount <= 2;
  const pageMessage =
    renderedPageCount > 2
      ? `Resume is ${renderedPageCount} pages (exceeds recommended 2-page limit)`
      : `Resume is ${renderedPageCount} page${renderedPageCount === 1 ? "" : "s"} (within 2-page limit)`;

  // 3. Action verbs
  const { total: totalBullets, withVerb: verbBullets, percentage: verbPercentage } =
    checkActionVerbs(resume);

  // 4. Placeholders
  const placeholders = checkPlaceholders(resume);

  return {
    keywords: {
      total: keywordItems.length,
      matchedCount,
      missingCount,
      items: keywordItems,
    },
    pageCount: {
      pages: renderedPageCount,
      isOptimal: isOptimalPage,
      message: pageMessage,
    },
    actionVerbs: {
      totalBullets,
      verbBullets,
      isOptimal: verbPercentage >= 70,
      percentage: verbPercentage,
    },
    placeholders: {
      count: placeholders.length,
      items: placeholders,
      isResolved: placeholders.length === 0,
    },
  };
}
