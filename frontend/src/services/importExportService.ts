import { api } from "./api";
import type { ExportResponse, ImportPayload, ImportResponse } from "../types/mistake";

const extractFilename = (contentDisposition?: string): string => {
  const match = contentDisposition?.match(/filename="?([^"]+)"?/);
  return match?.[1] ?? "coderecall-export.json";
};

export const exportAll = async (): Promise<{ data: ExportResponse; filename: string }> => {
  const response = await api.get<ExportResponse>("/export");
  return {
    data: response.data,
    filename: extractFilename(response.headers["content-disposition"]),
  };
};

export const importPayload = async (
  payload: ImportPayload,
  strategy: "skip_existing" | "replace" = "skip_existing",
): Promise<ImportResponse> => {
  const response = await api.post<ImportResponse>(`/import?strategy=${strategy}`, payload);
  return response.data;
};
