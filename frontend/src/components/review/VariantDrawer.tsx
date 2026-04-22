import { useState } from "react";
import { Button, Drawer, Spin, Tag, Typography } from "antd";
import { api } from "../../services/api";
import MarkdownRenderer from "../common/MarkdownRenderer";

interface VariantOut {
  variant_title: string;
  variant_stem: string;
  variant_hint: string;
}

interface VariantDrawerProps {
  mistakeId: number;
  open: boolean;
  onClose: () => void;
}

export default function VariantDrawer({ mistakeId, open, onClose }: VariantDrawerProps) {
  const [loading, setLoading] = useState(false);
  const [variant, setVariant] = useState<VariantOut | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [hintVisible, setHintVisible] = useState(false);

  const handleGenerate = async () => {
    setLoading(true);
    setError(null);
    setVariant(null);
    setHintVisible(false);
    try {
      const response = await api.post<VariantOut>(`/ai/generate-variant/${mistakeId}`);
      setVariant(response.data);
    } catch {
      setError("生成失败，请重试");
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    setVariant(null);
    setError(null);
    setHintVisible(false);
    onClose();
  };

  return (
    <Drawer
      title="AI 变体题"
      open={open}
      onClose={handleClose}
      width={600}
      extra={
        <Button type="primary" onClick={handleGenerate} loading={loading} disabled={loading}>
          {variant ? "重新生成" : "生成变体题"}
        </Button>
      }
    >
      {!variant && !loading && !error && (
        <Typography.Text type="secondary">点击右上角「生成变体题」，AI 将基于原题生成同类陷阱的新题目。</Typography.Text>
      )}
      {loading && (
        <div style={{ textAlign: "center", padding: "40px 0" }}>
          <Spin size="large" />
        </div>
      )}
      {error && <Typography.Text type="danger">{error}</Typography.Text>}
      {variant && (
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <div>
            <Tag color="blue">变体题</Tag>
            <Typography.Title level={4} style={{ marginTop: 8 }}>
              {variant.variant_title}
            </Typography.Title>
          </div>
          <div className="review-markdown">
            <MarkdownRenderer>{variant.variant_stem}</MarkdownRenderer>
          </div>
          <div>
            {hintVisible ? (
              <div style={{ background: "var(--app-sider-bg)", padding: "12px 16px", borderRadius: 6 }}>
                <Typography.Text strong>陷阱提示：</Typography.Text>
                <Typography.Text>{variant.variant_hint}</Typography.Text>
              </div>
            ) : (
              <Button onClick={() => setHintVisible(true)}>显示陷阱提示</Button>
            )}
          </div>
        </div>
      )}
    </Drawer>
  );
}
