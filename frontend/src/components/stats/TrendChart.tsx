import { Card, Skeleton, Typography } from "antd";
import { useTranslation } from "react-i18next";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { StatsTrend } from "../../types/stats";

interface TrendChartProps {
  trend: StatsTrend | null;
  loading?: boolean;
}

const formatDate = (value: string): string => value.slice(5);

export default function TrendChart({ trend, loading = false }: TrendChartProps) {
  const { t } = useTranslation();

  if (loading) {
    return (
      <Card className="panel-card stats-chart-card" title={t("statsComponents.reviewTrend")}>
        <Skeleton.Image active className="stats-chart-skeleton" />
      </Card>
    );
  }

  return (
    <Card className="panel-card stats-chart-card" title={t("statsComponents.reviewTrend")}>
      {trend && trend.items.length > 0 ? (
        <ResponsiveContainer width="100%" height={220}>
          <LineChart data={trend.items} margin={{ top: 12, right: 20, left: -20, bottom: 0 }}>
            <CartesianGrid stroke="var(--border-divider)" vertical={false} />
            <XAxis
              dataKey="date"
              tickFormatter={formatDate}
              tick={{ fill: "var(--text-secondary)", fontSize: 12 }}
              tickLine={false}
              axisLine={{ stroke: "var(--border-default)" }}
            />
            <YAxis
              allowDecimals={false}
              tick={{ fill: "var(--text-secondary)", fontSize: 12 }}
              tickLine={false}
              axisLine={false}
            />
            <Tooltip
              formatter={(value: number | string) => [
                t("statsComponents.reviewCountValue", { count: value }),
                t("statsComponents.reviewCount"),
              ]}
              labelFormatter={(label: string | number) => t("statsComponents.dateLabel", { date: label })}
              contentStyle={{
                background: "var(--color-bg-card)",
                borderColor: "var(--color-border)",
                color: "var(--color-text-primary)",
              }}
              itemStyle={{ color: "var(--color-text-primary)" }}
              labelStyle={{ color: "var(--color-text-secondary)" }}
            />
            <Line
              type="monotone"
              dataKey="review_count"
              name={t("statsComponents.reviewCount")}
              stroke="var(--color-primary)"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4 }}
            />
          </LineChart>
        </ResponsiveContainer>
      ) : (
        <Typography.Text className="soft-note">{t("statsComponents.noTrendData")}</Typography.Text>
      )}
    </Card>
  );
}
