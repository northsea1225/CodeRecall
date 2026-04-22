import { api } from "./api";

export interface ProblemUrlPreviewResponse {
  provider: string;
  source_url: string;
  external_id: string;
  title: string;
  difficulty_raw: string;
  difficulty: number;
  tags: string[];
  stem_markdown: string;
  warnings: string[];
}

export const previewProblemUrl = async (url: string): Promise<ProblemUrlPreviewResponse> => {
  const response = await api.post<ProblemUrlPreviewResponse>("/import/problem-url/preview", { url });
  return response.data;
};
