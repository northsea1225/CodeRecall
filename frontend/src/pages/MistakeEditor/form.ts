import type { Mistake, MistakeCreate, MistakeStatus, MistakeUpdate } from "../../types/mistake";
import { stripMarkdownCodeFences } from "../../utils/markdownCodeFence";

export interface MistakeDraft {
  title: string;
  stem_markdown: string;
  wrong_answer_markdown: string;
  correct_answer_markdown: string;
  error_reason_markdown: string;
  category_id?: number;
  tags: string[];
  language: string;
  difficulty: number;
  source: string;
  status: MistakeStatus;
}

const normalizeLanguage = (language: string): string => (language === "plain" ? "plaintext" : language);

const normalizeTags = (tags: string[]): string[] =>
  Array.from(
    new Set(
      tags
        .map((tag) => tag.trim())
        .filter(Boolean),
    ),
  );

export const createEmptyDraft = (): MistakeDraft => ({
  title: "",
  stem_markdown: "",
  wrong_answer_markdown: "",
  correct_answer_markdown: "",
  error_reason_markdown: "",
  category_id: undefined,
  tags: [],
  language: "plaintext",
  difficulty: 3,
  source: "",
  status: "new",
});

export const mistakeToDraft = (mistake: Mistake): MistakeDraft => ({
  title: mistake.title,
  stem_markdown: mistake.stem_markdown,
  wrong_answer_markdown: stripMarkdownCodeFences(mistake.wrong_answer_markdown),
  correct_answer_markdown: stripMarkdownCodeFences(mistake.correct_answer_markdown),
  error_reason_markdown: mistake.error_reason_markdown,
  category_id: mistake.category.id,
  tags: mistake.tags.map((tag) => tag.name),
  language: normalizeLanguage(mistake.language),
  difficulty: mistake.difficulty,
  source: mistake.source,
  status: mistake.status,
});

const requireCategoryId = (draft: MistakeDraft): number => {
  if (!draft.category_id) {
    throw new Error("Category is required.");
  }

  return draft.category_id;
};

export const draftToCreatePayload = (draft: MistakeDraft): MistakeCreate => ({
  title: draft.title.trim(),
  stem_markdown: draft.stem_markdown,
  wrong_answer_markdown: stripMarkdownCodeFences(draft.wrong_answer_markdown),
  correct_answer_markdown: stripMarkdownCodeFences(draft.correct_answer_markdown),
  error_reason_markdown: draft.error_reason_markdown,
  category_id: requireCategoryId(draft),
  tags: normalizeTags(draft.tags),
  language: draft.language,
  difficulty: draft.difficulty,
  source: draft.source.trim(),
  status: draft.status,
});

export const draftToUpdatePayload = (draft: MistakeDraft): MistakeUpdate => ({
  title: draft.title.trim(),
  stem_markdown: draft.stem_markdown,
  wrong_answer_markdown: stripMarkdownCodeFences(draft.wrong_answer_markdown),
  correct_answer_markdown: stripMarkdownCodeFences(draft.correct_answer_markdown),
  error_reason_markdown: draft.error_reason_markdown,
  category_id: requireCategoryId(draft),
  tags: normalizeTags(draft.tags),
  language: draft.language,
  difficulty: draft.difficulty,
  source: draft.source.trim(),
});
