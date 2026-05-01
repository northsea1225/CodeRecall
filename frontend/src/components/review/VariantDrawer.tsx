import { useState } from "react";
import { Button, Drawer, Spin, Tag, Typography } from "antd";
import { useTranslation } from "react-i18next";
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
  const { t } = useTranslation();
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
      setError(t("variant.generateFailed"));
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
      title={t("variant.title")}
      open={open}
      onClose={handleClose}
      width={600}
      extra={
        <Button type="primary" onClick={handleGenerate} loading={loading} disabled={loading}>
          {variant ? t("variant.regenerate") : t("variant.generate")}
        </Button>
      }
    >
      {!variant && !loading && !error && (
        <Typography.Text type="secondary">{t("variant.tooltip")}</Typography.Text>
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
            <Tag color="blue">{t("variant.tag")}</Tag>
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
                <Typography.Text strong>{t("variant.hintLabel")}</Typography.Text>
                <Typography.Text>{variant.variant_hint}</Typography.Text>
              </div>
            ) : (
              <Button onClick={() => setHintVisible(true)}>{t("variant.showHint")}</Button>
            )}
          </div>
        </div>
      )}
    </Drawer>
  );
}
