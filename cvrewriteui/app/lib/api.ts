// Client for the CV Rewrite API. Mirrors the FastAPI response shape.
//
// The SPA is served by FastAPI on the same origin, so requests are relative
// (`/api/rewrite`) — no CORS, no baked-in host. In `dev`, Vite proxies these
// paths to the API (see vite.config.ts). Set VITE_API_URL only to point the
// app at an API on a different origin.

import { loadApiKey } from "~/lib/apikey-store"

export const API_BASE_URL: string =
  (import.meta.env.VITE_API_URL as string | undefined) ?? ""

/**
 * Build request headers, attaching the user's Anthropic key (BYOK) as
 * `X-Anthropic-Api-Key` when one is stored. If none is stored, the header is
 * omitted and the server uses its own key (or Ollama) — nothing changes.
 */
async function buildHeaders(base?: Record<string, string>): Promise<Headers> {
  const headers = new Headers(base)
  const key = await loadApiKey()
  if (key) headers.set("X-Anthropic-Api-Key", key)
  return headers
}

export interface AppConfig {
  /** True when the server has no key of its own, so the user must supply one. */
  requiresApiKey: boolean
}

/** Ask the server whether the user must provide their own Anthropic key. */
export async function fetchConfig(): Promise<AppConfig> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/config`)
    if (!res.ok) return { requiresApiKey: false }
    const body = (await res.json()) as { requires_api_key?: boolean }
    return { requiresApiKey: Boolean(body.requires_api_key) }
  } catch {
    return { requiresApiKey: false }
  }
}

export type Verdict = "STRONG" | "PARTIAL" | "WEAK" | "NOT_RECOMMENDED"

export interface ScoreDimension {
  name: string
  weight: number
  score: number
}

export interface Gap {
  requirement: string
  candidate_has: string
  closable: boolean
  how_to_close: string
}

export interface ScoreReport {
  overall_score: number
  verdict: Verdict
  dimensions: ScoreDimension[]
  why_apply: string[]
  why_think_twice: string[]
  gaps: Gap[]
  ats_flags: string[]
}

export interface ExperienceEntry {
  title: string
  company: string
  dates: string
  bullets: string[]
}

export interface EducationEntry {
  qualification: string
  institution: string
  dates: string
}

export interface RewrittenCv {
  full_name: string
  contact: string
  professional_summary: string
  experience: ExperienceEntry[]
  skills: string[]
  education: EducationEntry[]
  certifications: string[]
  rewrite_note: string
}

export interface InterviewPrep {
  likely_questions: string[]
  talking_points: string[]
  topics_to_prepare: string[]
  company_research: string | null
}

export interface RewriteResponse {
  score_report: ScoreReport
  rewritten_cv: RewrittenCv | null
  interview_prep: InterviewPrep | null
  pdf_base64: string | null
  pdf_filename: string | null
}

/** Upload a CV (PDF) + job description and get the analysis + rewritten CV. */
export async function rewriteCv(
  cv: File,
  jobDescription: string,
): Promise<RewriteResponse> {
  const form = new FormData()
  form.append("cv", cv)
  form.append("job_description", jobDescription)

  let res: Response
  try {
    res = await fetch(`${API_BASE_URL}/api/rewrite`, {
      method: "POST",
      headers: await buildHeaders(),
      body: form,
    })
  } catch {
    const where = API_BASE_URL || "this server"
    throw new Error(`Could not reach the API at ${where}. Is the backend running?`)
  }

  if (!res.ok) {
    let detail = `Request failed (${res.status})`
    try {
      const body = await res.json()
      if (typeof body?.detail === "string") detail = body.detail
    } catch {
      /* keep the generic message */
    }
    throw new Error(detail)
  }

  return (await res.json()) as RewriteResponse
}

export interface GuideResponse {
  pdf_base64: string
  pdf_filename: string
}

/**
 * Build a full interview-prep training guide (PDF) from a prior analysis.
 * The app is stateless, so we send the relevant results back to the API.
 */
export async function buildInterviewGuide(
  jobDescription: string,
  data: RewriteResponse,
): Promise<GuideResponse> {
  if (!data.interview_prep) {
    throw new Error("There's no interview prep to build a guide from.")
  }
  const body = {
    job_description: jobDescription,
    score_report: data.score_report,
    interview_prep: data.interview_prep,
    rewritten_cv: data.rewritten_cv,
  }

  let res: Response
  try {
    res = await fetch(`${API_BASE_URL}/api/interview-guide`, {
      method: "POST",
      headers: await buildHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify(body),
    })
  } catch {
    const where = API_BASE_URL || "this server"
    throw new Error(`Could not reach the API at ${where}. Is the backend running?`)
  }

  if (!res.ok) {
    let detail = `Request failed (${res.status})`
    try {
      const b = await res.json()
      if (typeof b?.detail === "string") detail = b.detail
    } catch {
      /* keep the generic message */
    }
    throw new Error(detail)
  }

  return (await res.json()) as GuideResponse
}

/** Turn a base64 PDF into a data URL for inline preview. */
export function pdfDataUrl(base64: string): string {
  return `data:application/pdf;base64,${base64}`
}

/** Trigger a browser download of a base64-encoded PDF. */
export function downloadPdf(base64: string, filename: string): void {
  const binary = atob(base64)
  const bytes = new Uint8Array(binary.length)
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i)
  const blob = new Blob([bytes], { type: "application/pdf" })
  const url = URL.createObjectURL(blob)
  const a = document.createElement("a")
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}
