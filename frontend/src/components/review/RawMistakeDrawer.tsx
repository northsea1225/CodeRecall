import { useEffect, useMemo, useState } from "react";
import { Alert, Descriptions, Drawer, Empty, Space, Spin, Tag } from "antd";

import { getMistake } from "../../services/mistakeService";
import type { Mistake } from "../../types/mistake";
import type { ReviewItem, ReviewReveal } from "../../types/review";

interface RawMistakeDrawerProps {
  open: boolean;
  mistakeId: number | null;
  currentItem: ReviewItem | null;
  revealedData: ReviewReveal | null;
  onClose: () => void;
}

const formatDate = (value?: string): string => {
  if (!value) {
    return "-";
  }

  return new Date(value).toLocaleString("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
};

export default function RawMistakeDrawer({
  open,
  mistakeId,
  currentItem,
  revealedData,
  onClose,
}: RawMistakeDrawerProps) {
  const [mistake, setMistake] = useState<Mistake | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open || !mistakeId) {
      return;
    }

    let active = true;
    setLoading(true);
    setError(null);
    setMistake(null);

    const loadMistake = async () => {
      try {
        const response = await getMistake(mistakeId);
        if (active) {
          setMistake(response);
        }
      } catch (drawerError) {
        if (active) {
          setError(drawerError instanceof Error ? drawerError.message : "加载原始错题失败。");
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    };

    void loadMistake();

    return () => {
      active = false;
    };
  }, [mistakeId, open]);

  const fallbackTags = useMemo(
    () => currentItem?.tag_names ?? revealedData?.tag_names ?? [],
    [currentItem?.tag_names, revealedData?.tag_names],
  );

  return (
    <Drawer
      width={480}
      title="原始错题信息"
      placement="right"
      open={open}
      onClose={onClose}
      destroyOnClose={false}
    >
      {loading ? (
        <div className="review-drawer-loading">
          <Spin />
        </div>
      ) : null}

      {error ? <Alert type="error" showIcon message={error} style={{ marginBottom: 16 }} /> : null}

      {!loading && !error && !mistakeId ? <Empty description="当前没有可查看的错题。" /> : null}

      {!loading && mistakeId ? (
        <Descriptions column={1} bordered size="small">
          <Descriptions.Item label="标题">
            {mistake?.title ?? revealedData?.title ?? currentItem?.title ?? "-"}
          </Descriptions.Item>
          <Descriptions.Item label="分类">
            {mistake?.category.name ?? revealedData?.category_name ?? currentItem?.category_name ?? "-"}
          </Descriptions.Item>
          <Descriptions.Item label="标签">
            <Space wrap>
              {(mistake?.tags.map((tag) => tag.name) ?? fallbackTags).map((tag) => (
                <Tag key={tag}>#{tag}</Tag>
              ))}
            </Space>
          </Descriptions.Item>
          <Descriptions.Item label="来源">{mistake?.source ?? "-"}</Descriptions.Item>
          <Descriptions.Item label="难度">
            {mistake?.difficulty ?? revealedData?.difficulty ?? currentItem?.difficulty ?? "-"}
          </Descriptions.Item>
          <Descriptions.Item label="创建时间">{formatDate(mistake?.created_at)}</Descriptions.Item>
        </Descriptions>
      ) : null}
    </Drawer>
  );
}
