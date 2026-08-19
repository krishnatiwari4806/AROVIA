/**
 * Competency Rubric and Scoring Calibration Utilities for AROVIA.
 */

export const COMPETENCY_TIERS = {
  EXCEPTIONAL: {
    minScore: 85,
    maxScore: 100,
    title: "Exceptional / Strong Hire",
    badgeClass: "badge-emerald",
    color: "#10b981",
    bgAlpha: "rgba(16, 185, 129, 0.15)",
    borderAlpha: "rgba(16, 185, 129, 0.35)",
    description: "Demonstrates advanced architectural mastery, rigorous edge-case analysis, and structured engineering conviction.",
  },
  PROFICIENT: {
    minScore: 70,
    maxScore: 84,
    title: "Proficient / Solid Hire",
    badgeClass: "badge-blue",
    color: "#3b82f6",
    bgAlpha: "rgba(59, 130, 246, 0.15)",
    borderAlpha: "rgba(59, 130, 246, 0.35)",
    description: "Solid technical fundamentals, good problem solving, and effective communication with minor polish needed on edge cases.",
  },
  DEVELOPING: {
    minScore: 50,
    maxScore: 69,
    title: "Developing / Needs Practice",
    badgeClass: "badge-amber",
    color: "#f59e0b",
    bgAlpha: "rgba(245, 158, 11, 0.15)",
    borderAlpha: "rgba(245, 158, 11, 0.35)",
    description: "Promising baseline understanding; requires structured practice in distributed systems trade-offs and technical depth.",
  },
  NEEDS_PREPARATION: {
    minScore: 0,
    maxScore: 49,
    title: "Needs Substantial Preparation",
    badgeClass: "badge-rose",
    color: "#f43f5e",
    bgAlpha: "rgba(244, 63, 94, 0.15)",
    borderAlpha: "rgba(244, 63, 94, 0.35)",
    description: "Significant conceptual gaps detected in core domain fundamentals; recommend reviewing foundational engineering principles.",
  },
};

/**
 * Resolve competency tier metadata from numeric composite score.
 * @param {number} score - Overall score from 0 to 100
 */
export function getCompetencyTier(score) {
  const cleanScore = Math.max(0, Math.min(100, Math.round(score || 0)));
  if (cleanScore >= 85) return COMPETENCY_TIERS.EXCEPTIONAL;
  if (cleanScore >= 70) return COMPETENCY_TIERS.PROFICIENT;
  if (cleanScore >= 50) return COMPETENCY_TIERS.DEVELOPING;
  return COMPETENCY_TIERS.NEEDS_PREPARATION;
}

/**
 * Target benchmark baseline score by seniority level.
 * @param {string} seniorityLevel - 'junior' | 'mid' | 'senior'
 */
export function getSeniorityBenchmark(seniorityLevel) {
  const level = (seniorityLevel || "").toLowerCase();
  if (level.includes("senior")) return 85;
  if (level.includes("mid")) return 70;
  return 55; // Junior
}

/**
 * Dimension metadata, icons, and descriptions.
 */
export const DIMENSION_METADATA = {
  relevance: {
    label: "Relevance & Alignment",
    short: "Relevance",
    description: "How directly and thoroughly candidate responses addressed the specific prompt and problem context.",
    color: "#06b6d4", // Cyan
  },
  correctness: {
    label: "Technical Correctness",
    short: "Correctness",
    description: "Accuracy of underlying architectures, algorithms, protocols, data structures, and edge-case mechanics.",
    color: "#10b981", // Emerald
  },
  keywords: {
    label: "Key Concepts & Coverage",
    short: "Key Concepts",
    description: "Demonstrated mastery of essential domain patterns, system components, and industry terminology.",
    color: "#8b5cf6", // Purple
  },
  clarity: {
    label: "Clarity & Articulation",
    short: "Clarity",
    description: "Logical organization, concise phrasing, structured problem breakdown, and communication flow.",
    color: "#3b82f6", // Blue
  },
  confidence: {
    label: "Confidence & Fluency",
    short: "Confidence",
    description: "Assertiveness, technical conviction, minimal hesitation markers, and decisive engineering ownership.",
    color: "#f59e0b", // Amber
  },
};
