import { api } from "./api";
import type {
  ReviewDueCount,
  ReviewCapability,
  ReviewNextResponse,
  ReviewReveal,
  ReviewSession,
  ReviewSessionStartPayload,
  ReviewSubmitPayload,
  ReviewSubmitResponse,
  ReviewSummary,
} from "../types/review";

export const startReviewSession = async (
  payload: ReviewSessionStartPayload = { strategy: "random", limit: 10 },
): Promise<ReviewSession> => {
  const response = await api.post<ReviewSession>("/review/sessions", payload);
  return response.data;
};

export const getNextReviewItem = async (sessionId: number): Promise<ReviewNextResponse> => {
  const response = await api.get<ReviewNextResponse>(`/review/sessions/${sessionId}/next`);
  return response.data;
};

export const submitReviewResult = async (
  sessionId: number,
  payload: ReviewSubmitPayload,
): Promise<ReviewSubmitResponse> => {
  const response = await api.post<ReviewSubmitResponse>(`/review/sessions/${sessionId}/submit`, payload);
  return response.data;
};

export const getReviewSummary = async (sessionId: number): Promise<ReviewSummary> => {
  const response = await api.get<ReviewSummary>(`/review/sessions/${sessionId}/summary`);
  return response.data;
};

export const getReviewCapability = async (): Promise<ReviewCapability> => {
  const response = await api.get<ReviewCapability>("/review/capability");
  return response.data;
};

export const getDueCount = async (): Promise<ReviewDueCount> => {
  const response = await api.get<ReviewDueCount>("/review/due-count");
  return response.data;
};

export const revealReviewItem = async (mistakeId: number): Promise<ReviewReveal> => {
  const response = await api.get<ReviewReveal>(`/review/items/${mistakeId}/reveal`);
  return response.data;
};
