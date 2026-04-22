export type MistakeStatus = "new" | "learning" | "reviewing" | "mastered";

export interface PaginationMeta {
  total: number;
  page: number;
  page_size: number;
}

export interface Category {
  id: number;
  name: string;
  description: string;
  parent_id: number | null;
  sort_order: number;
  created_at: string;
  updated_at: string;
}

export interface CategoryCreate {
  name: string;
  description: string;
  parent_id?: number | null;
  sort_order?: number;
}

export interface CategoryListResponse {
  items: Category[];
  total: number;
}

export interface Tag {
  id: number;
  name: string;
  created_at: string;
  updated_at: string;
}

export interface TagListResponse {
  items: Tag[];
  total: number;
}

export interface Mistake {
  id: number;
  title: string;
  stem_markdown: string;
  wrong_answer_markdown: string;
  correct_answer_markdown: string;
  error_reason_markdown: string;
  language: string;
  difficulty: number;
  source: string;
  status: MistakeStatus;
  review_count: number;
  last_reviewed_at: string | null;
  next_review_at: string | null;
  ease_factor: number;
  interval_days: number;
  repetition: number;
  is_archived: boolean;
  category: Category;
  tags: Tag[];
  created_at: string;
  updated_at: string;
}

export interface MistakeCreate {
  title: string;
  stem_markdown: string;
  wrong_answer_markdown: string;
  correct_answer_markdown: string;
  error_reason_markdown: string;
  language: string;
  difficulty: number;
  source: string;
  status: MistakeStatus;
  category_id: number;
  tags: string[];
  is_archived?: boolean;
}

export interface MistakeUpdate {
  title?: string;
  stem_markdown?: string;
  wrong_answer_markdown?: string;
  correct_answer_markdown?: string;
  error_reason_markdown?: string;
  language?: string;
  difficulty?: number;
  source?: string;
  category_id?: number;
  tags?: string[];
  is_archived?: boolean;
}

export interface MistakeListResponse {
  items: Mistake[];
  total: number;
  pagination: PaginationMeta;
}

export interface ImportCategory {
  name: string;
  description: string;
}

export interface ImportTag {
  name: string;
}

export interface ImportMistake {
  title: string;
  stem_markdown: string;
  wrong_answer_markdown: string;
  correct_answer_markdown: string;
  error_reason_markdown: string;
  language: string;
  difficulty: number;
  source: string;
  status: string;
  category_name: string;
  tag_names: string[];
  ease_factor?: number;
  interval_days?: number;
  repetition?: number;
  next_review_at?: string | null;
  is_archived?: boolean;
}

export interface ImportPayload {
  version: string;
  schema_version?: string;
  mistakes: ImportMistake[];
  categories: ImportCategory[];
  tags: ImportTag[];
}

export interface ExportResponse {
  version: string;
  schema_version: string;
  exported_at: string;
  categories: ImportCategory[];
  tags: ImportTag[];
  mistakes: ImportMistake[];
}

export interface ImportCount {
  mistakes: number;
  categories: number;
  tags: number;
}

export interface ImportSkip {
  entity: string;
  identifier: string;
  reason: string;
}

export interface ImportResponse {
  version: string;
  imported: ImportCount;
  skipped: ImportSkip[];
}
