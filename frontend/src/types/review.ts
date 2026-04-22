export type ReviewStrategy = "random" | "spaced_repetition" | "due_first";
export type ReviewResult = "again" | "hard" | "good" | "easy";

export interface ReviewItem {
  mistake_id: number;
  title: string;
  stem_markdown: string;
  language: string;
  difficulty: number;
  category_name: string;
  tag_names: string[];
  shown_at: string;
}

export interface ReviewReveal {
  mistake_id: number;
  title: string;
  stem_markdown: string;
  wrong_answer_markdown: string;
  correct_answer_markdown: string;
  error_reason_markdown: string;
  language: string;
  difficulty: number;
  category_name: string;
  tag_names: string[];
}

export interface ReviewProgress {
  completed: number;
  total: number;
}

export interface ReviewSessionStartPayload {
  strategy: ReviewStrategy;
  limit?: number;
}

export interface ReviewSession {
  id: number;
  strategy: ReviewStrategy;
  started_at: string;
  total_count: number;
  completed_count: number;
  next_item: ReviewItem | null;
}

export interface ReviewNextResponse {
  next_item: ReviewItem | null;
  progress: ReviewProgress;
}

export interface ReviewSubmitPayload {
  mistake_id: number;
  user_result: ReviewResult;
  shown_at?: string;
  time_spent_ms?: number;
  note?: string;
}

export interface ReviewLog {
  id: number;
  mistake_id: number;
  session_id: number | null;
  review_mode: string;
  user_result: ReviewResult;
  shown_at: string;
  answered_at: string | null;
  time_spent_ms: number | null;
  note: string;
}

export interface ReviewSubmitResponse extends ReviewLog {
  progress: ReviewProgress;
}

export interface ReviewResultCounts {
  again: number;
  hard: number;
  good: number;
  easy: number;
}

export interface ReviewSummary {
  total_count: number;
  completed_count: number;
  result_counts: ReviewResultCounts;
  duration_ms: number;
}

export interface ReviewCapability {
  ai_analysis_enabled: boolean;
  model?: string;
}

export interface ReviewDueCount {
  due_count: number;
  as_of: string;
}

export type AiAnalysisStreamStatus = "idle" | "ready" | "streaming" | "completed" | "error";
