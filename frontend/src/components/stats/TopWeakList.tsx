import { Card, Skeleton, Space, Table, Tag } from "antd";
import { useNavigate } from "react-router-dom";
import type { ColumnsType } from "antd/es/table";
import { useTranslation } from "react-i18next";

import type { StatsTopWeakItem } from "../../types/stats";
import type { ReviewResult } from "../../types/review";

interface TopWeakListProps {
  items: StatsTopWeakItem[];
  loading?: boolean;
}

export default function TopWeakList({ items, loading = false }: TopWeakListProps) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const resultLabels: Record<ReviewResult, string> = {
    again: t("statsComponents.resultAgain"),
    hard: t("statsComponents.resultHard"),
    good: t("statsComponents.resultGood"),
    easy: t("statsComponents.resultEasy"),
  };
  const renderLastResult = (value: StatsTopWeakItem["last_result"]) => {
    if (!value) {
      return <Tag>{t("statsComponents.notReviewed")}</Tag>;
    }

    if (value === "again") {
      return <Tag color="red">{resultLabels[value]}</Tag>;
    }

    if (value === "good" || value === "easy") {
      return <Tag color="green">{resultLabels[value]}</Tag>;
    }

    return <Tag color="gold">{resultLabels[value]}</Tag>;
  };
  const columns: ColumnsType<StatsTopWeakItem> = [
    {
      title: t("statsComponents.colTitle"),
      dataIndex: "title",
      key: "title",
      ellipsis: true,
    },
    {
      title: t("statsComponents.colLanguage"),
      dataIndex: "language",
      key: "language",
      render: (value: string) => <Tag>{value}</Tag>,
    },
    {
      title: t("statsComponents.colCategory"),
      dataIndex: "category_name",
      key: "category_name",
    },
    {
      title: t("statsComponents.colStatus"),
      dataIndex: "status",
      key: "status",
      render: (value: string, item) => (
        <Space size={[4, 4]} wrap>
          <Tag>{value}</Tag>
          {item.overdue_days > 0 ? (
            <Tag color="gold">{t("statsComponents.overdueDays", { count: item.overdue_days })}</Tag>
          ) : null}
        </Space>
      ),
    },
    {
      title: t("statsComponents.colReviewCount"),
      dataIndex: "review_count",
      key: "review_count",
      width: 120,
    },
    {
      title: t("statsComponents.colLastResult"),
      dataIndex: "last_result",
      key: "last_result",
      render: renderLastResult,
    },
    {
      title: t("statsComponents.colWeakScore"),
      dataIndex: "weak_score",
      key: "weak_score",
      render: (value: number) => value.toFixed(1),
    },
  ];

  return (
    <Card className="panel-card stats-table-card" title={t("statsComponents.topWeakTitle")}>
      {loading ? (
        <Skeleton active paragraph={{ rows: 6 }} />
      ) : (
        <Table
          columns={columns}
          dataSource={items}
          pagination={false}
          rowKey="mistake_id"
          scroll={{ x: 920 }}
          rowClassName={(item) => (item.overdue_days > 0 ? "stats-topweak-row--overdue" : "")}
          onRow={(item) => ({
            onClick: () => navigate(`/mistakes/${item.mistake_id}`),
          })}
        />
      )}
    </Card>
  );
}
