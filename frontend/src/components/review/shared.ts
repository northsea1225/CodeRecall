import type { ReviewResult, ReviewSummary } from "../../types/review";

export interface SelfRateOption {
  key: "1" | "2" | "3" | "4";
  value: ReviewResult;
  label: string;
  tooltip: string;
  buttonType?: "default" | "primary";
  className?: string;
  danger?: boolean;
}

export const selfRateOptions: SelfRateOption[] = [
  {
    key: "1",
    value: "again",
    label: "重来 (Again)",
    tooltip: "< 1m",
    className: "review-rate-button--again",
    danger: true,
  },
  {
    key: "2",
    value: "hard",
    label: "困难 (Hard)",
    tooltip: "12h",
    className: "review-rate-button--hard",
  },
  {
    key: "3",
    value: "good",
    label: "良好 (Good)",
    tooltip: "1d",
    buttonType: "primary",
  },
  {
    key: "4",
    value: "easy",
    label: "简单 (Easy)",
    tooltip: "4d",
    className: "review-rate-button--easy",
  },
];

export const formatReviewDuration = (durationMs: number): string => {
  if (durationMs < 60_000) {
    return `${Math.max(Math.round(durationMs / 1000), 0)} 秒`;
  }

  return `${Math.round(durationMs / 60_000)} 分钟`;
};

export const computeReviewAccuracy = (summary: ReviewSummary): number => {
  if (summary.total_count === 0) {
    return 0;
  }

  return Math.round(((summary.result_counts.good + summary.result_counts.easy) / summary.total_count) * 100);
};
