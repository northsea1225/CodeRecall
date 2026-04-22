import type { MistakeStatus } from "./mistake";
import type { ReviewResult } from "./review";

export interface StatsOverview {
  as_of: string;
  total_mistakes: number;
  active_mistakes: number;
  mastered_count: number;
  due_today: number;
  reviewed_today: number;
  reviewed_7d: number;
  avg_accuracy_7d: number;
  avg_ease_factor: number;
  streak_days: number;
}

export interface StatsTrendRange {
  from: string;
  to: string;
  bucket: "day";
}

export interface StatsTrendItem {
  date: string;
  created_count: number;
  review_count: number;
  again_count: number;
  hard_count: number;
  good_count: number;
  easy_count: number;
}

export interface StatsTrend {
  range: StatsTrendRange;
  items: StatsTrendItem[];
}

export interface StatsHeatmapRange {
  from: string;
  to: string;
}

export interface StatsHeatmapCell {
  date: string;
  count: number;
  level: 0 | 1 | 2 | 3 | 4;
}

export interface StatsHeatmap {
  range: StatsHeatmapRange;
  max_count: number;
  cells: StatsHeatmapCell[];
}

export interface StatsTopWeakItem {
  mistake_id: number;
  title: string;
  language: string;
  category_name: string;
  status: MistakeStatus;
  review_count: number;
  last_result: ReviewResult | null;
  again_count: number;
  hard_count: number;
  next_review_at: string | null;
  overdue_days: number;
  weak_score: number;
}

export interface StatsTopWeak {
  items: StatsTopWeakItem[];
}

export interface StatsTagRadarItem {
  tag_name: string;
  mistake_count: number;
  mastery_rate: number;
  avg_ease_factor: number;
}

export interface StatsTagRadar {
  items: StatsTagRadarItem[];
  min_count_threshold: number;
}
