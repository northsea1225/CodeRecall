import { api } from "./api";
import type { Category, CategoryCreate, CategoryListResponse, Tag, TagListResponse } from "../types/mistake";

export const listCategories = async (): Promise<CategoryListResponse> => {
  const response = await api.get<CategoryListResponse>("/categories");
  return response.data;
};

export const createCategory = async (payload: CategoryCreate): Promise<Category> => {
  const response = await api.post<Category>("/categories", {
    ...payload,
    description: payload.description ?? "",
    sort_order: payload.sort_order ?? 0,
  });
  return response.data;
};

export const listTags = async (): Promise<TagListResponse> => {
  const response = await api.get<TagListResponse>("/tags");
  return response.data;
};
