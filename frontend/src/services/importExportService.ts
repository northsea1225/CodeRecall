import { api } from "./api";
import type { ExportResponse, ImportPayload, ImportResponse } from "../types/mistake";

const extractFilename = (contentDisposition?: string, fallback = "coderecall-export.json"): string => {
  const match = contentDisposition?.match(/filename="?([^";\n]+)"?/);
  return match?.[1] ?? fallback;
};

export const exportAll = async (): Promise<{ data: ExportResponse; filename: string }> => {
  const response = await api.get<ExportResponse>("/export");
  return {
    data: response.data,
    filename: extractFilename(response.headers["content-disposition"]),
  };
};

export const exportAllV3 = async (): Promise<{ data: ExportResponse; filename: string }> => {
  const response = await api.get<ExportResponse>("/export/v3");
  return {
    data: response.data,
    filename: extractFilename(response.headers["content-disposition"], "coderecall-v3-export.json"),
  };
};

export const importPayload = async (
  payload: ImportPayload,
  strategy: "skip_existing" | "replace" = "skip_existing",
): Promise<ImportResponse> => {
  const response = await api.post<ImportResponse>(`/import?strategy=${strategy}`, payload);
  return response.data;
};

export const importPayloadV3 = async (
  payload: ImportPayload,
  strategy: "skip_existing" | "replace" = "skip_existing",
): Promise<ImportResponse> => {
  const response = await api.post<ImportResponse>(`/import/v3?strategy=${strategy}`, payload);
  return response.data;
};
