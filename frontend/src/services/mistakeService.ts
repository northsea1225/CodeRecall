import { api } from "./api";
import type { Mistake, MistakeCreate, MistakeListResponse, MistakeUpdate } from "../types/mistake";

export interface ListMistakesParams {
  page?: number;
  page_size?: number;
  category_id?: number;
  language?: string;
  keyword?: string;
}

export const listMistakes = async (params: ListMistakesParams = {}): Promise<MistakeListResponse> => {
  const response = await api.get<MistakeListResponse>("/mistakes", { params });
  return response.data;
};

export const getMistake = async (id: number): Promise<Mistake> => {
  const response = await api.get<Mistake>(`/mistakes/${id}`);
  return response.data;
};

export const createMistake = async (payload: MistakeCreate): Promise<Mistake> => {
  const response = await api.post<Mistake>("/mistakes", payload);
  return response.data;
};

export const updateMistake = async (id: number, payload: MistakeUpdate): Promise<Mistake> => {
  const response = await api.patch<Mistake>(`/mistakes/${id}`, payload);
  return response.data;
};

export const deleteMistake = async (id: number): Promise<void> => {
  await api.delete(`/mistakes/${id}`);
};
