export interface User {
  id: number
  email: string
  created_at: string
}

export interface Dimension {
  label: string
  score: number
  max: number
  detail?: string
}

export interface AnalysisDetails {
  dimensions: Record<string, Dimension>
  suggestions: string[]
  matched_keywords: string[]
  missing_keywords: string[]
}

export interface Resume {
  id: number
  filename: string
  content_text: string
  created_at: string
}

export interface Analysis {
  id: number
  resume_id: number
  filename?: string
  job_description: string
  score: number
  summary: string
  engine: string
  details: AnalysisDetails
  created_at: string
}
