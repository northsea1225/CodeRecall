import { api } from "./api";
import type { StatsHeatmap, StatsOverview, StatsTagRadar, StatsTopWeak, StatsTrend } from "../types/stats";

export interface StatsOverviewParams {
  days?: number;
  tz_offset_minutes?: number;
}

export interface StatsTrendParams {
  days?: number;
  bucket?: "day";
  tz_offset_minutes?: number;
}

export interface StatsHeatmapParams {
  days?: number;
  tz_offset_minutes?: number;
}

export interface StatsTopWeakParams {
  limit?: number;
  days?: number;
}

export const getStatsOverview = async (params: StatsOverviewParams = {}): Promise<StatsOverview> => {
  const response = await api.get<StatsOverview>("/stats/overview", { params });
  return response.data;
};

export const getStatsTrend = async (params: StatsTrendParams = {}): Promise<StatsTrend> => {
  const response = await api.get<StatsTrend>("/stats/trend", { params });
  return response.data;
};

export const getStatsHeatmap = async (params: StatsHeatmapParams = {}): Promise<StatsHeatmap> => {
  const response = await api.get<StatsHeatmap>("/stats/heatmap", { params });
  return response.data;
};

export const getStatsTopWeak = async (params: StatsTopWeakParams = {}): Promise<StatsTopWeak> => {
  const response = await api.get<StatsTopWeak>("/stats/top-weak", { params });
  return response.data;
};

export interface StatsTagRadarParams {
  min_count?: number;
}

export const getStatsTagRadar = async (params: StatsTagRadarParams = {}): Promise<StatsTagRadar> => {
  const response = await api.get<StatsTagRadar>("/stats/tag-radar", { params });
  return response.data;
};
