import { Card, Empty, Spin, Typography } from "antd";
import {
  PolarAngleAxis,
  PolarGrid,
  Radar,
  RadarChart,
  ResponsiveContainer,
  Tooltip,
} from "recharts";
import type { StatsTagRadar } from "../../types/stats";

interface RadarTagChartProps {
  radar: StatsTagRadar | null;
  loading?: boolean;
}

const MIN_TAGS_FOR_RADAR = 3;

export default function RadarTagChart({ radar, loading = false }: RadarTagChartProps) {
  const items = radar?.items ?? [];
  const minCount = radar?.min_count_threshold ?? 2;
  const qualifyingCount = items.length;

  const renderContent = () => {
    if (loading && !radar) {
      return (
        <div style={{ display: "flex", justifyContent: "center", padding: "40px 0" }}>
          <Spin />
        </div>
      );
    }

    if (qualifyingCount < MIN_TAGS_FOR_RADAR) {
      const needed = MIN_TAGS_FOR_RADAR - qualifyingCount;
      return (
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description={
            <Typography.Text type="secondary">
              {`再积累 ${needed} 个知识点（每个至少 ${minCount} 道题）解锁能力雷达`}
            </Typography.Text>
          }
        />
      );
    }

    const data = items.map((item) => ({
      subject: item.tag_name,
      掌握度: Math.round(item.mastery_rate * 100),
      fullMark: 100,
    }));

    return (
      <ResponsiveContainer width="100%" height={320}>
        <RadarChart data={data}>
          <PolarGrid />
          <PolarAngleAxis dataKey="subject" />
          <Radar
            name="掌握度"
            dataKey="掌握度"
            stroke="#1677ff"
            fill="#1677ff"
            fillOpacity={0.3}
          />
          <Tooltip formatter={(value: number) => [`${value}%`, "掌握度"]} />
        </RadarChart>
      </ResponsiveContainer>
    );
  };

  return (
    <Card className="panel-card" title="算法能力雷达">
      {renderContent()}
    </Card>
  );
}
