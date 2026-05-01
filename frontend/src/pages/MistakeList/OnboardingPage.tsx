import { useState } from "react";
import { Button, Space, Typography, message } from "antd";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";

import ProblemUrlImporter from "../../components/common/ProblemUrlImporter";
import { importPayload } from "../../services/importExportService";
import type { ProblemUrlPreviewResponse } from "../../services/problemImportService";
import { useDraftStore } from "../../stores/draftStore";
import demoData from "../../data/demoImportPayload.json";

interface Props {
  userId: number | null;
  onImported: () => void;
}

export default function OnboardingPage({ userId, onImported }: Props) {
  const navigate = useNavigate();
  const { t } = useTranslation();
  const [loadingDemo, setLoadingDemo] = useState(false);
  const patchDraft = useDraftStore((s) => s.patchDraft);
  const importedKey = `coderecall_ever_imported_${userId}`;

  const handleUrlFilled = (data: ProblemUrlPreviewResponse) => {
    const patch = {
      title: data.title,
      stem_markdown: data.stem_markdown,
      difficulty: data.difficulty,
      source: data.source_url,
      tags: data.tags,
    };
    patchDraft("new", patch);
    localStorage.setItem(importedKey, "1");
    void message.success(t("onboarding.urlFillSuccess"));
    navigate("/mistakes/new");
  };

  const handleLoadDemo = async () => {
    setLoadingDemo(true);
    try {
      await importPayload(demoData as Parameters<typeof importPayload>[0], "skip_existing");
      localStorage.setItem(importedKey, "1");
      onImported();
      void message.success(t("onboarding.demoLoaded"));
    } catch {
      void message.error(t("onboarding.demoLoadFailed"));
    } finally {
      setLoadingDemo(false);
    }
  };

  return (
    <div
      style={{
        minHeight: "80vh",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        padding: "48px 24px",
        textAlign: "center",
      }}
    >
      <Typography.Title level={2} style={{ marginBottom: 8 }}>
        {t("onboarding.heroTitle")}
      </Typography.Title>
      <Typography.Paragraph type="secondary" style={{ fontSize: 16, marginBottom: 32 }}>
        {t("onboarding.heroSubtitle")}
      </Typography.Paragraph>

      {/* 代码预览卡 */}
      <div className="onboarding-diff-card">
        <div className="diff-del">{t("onboarding.demoLineDel")}</div>
        <div className="diff-add">{t("onboarding.demoLineAdd")}</div>
        <div className="diff-info">{t("onboarding.demoLineInfo")}</div>
      </div>

      {/* URL 导入 */}
      <div style={{ width: "100%", maxWidth: 480, marginBottom: 16 }}>
        <ProblemUrlImporter onFilled={handleUrlFilled} autoFocus />
      </div>

      {/* Demo 按钮 */}
      <Space direction="vertical" size={8} style={{ width: "100%", maxWidth: 480 }}>
        <Button
          block
          size="large"
          loading={loadingDemo}
          onClick={() => void handleLoadDemo()}
        >
          {t("onboarding.loadDemo")}
        </Button>
        <Button type="link" onClick={() => navigate("/mistakes/new")}>
          {t("onboarding.createBlank")}
        </Button>
      </Space>
    </div>
  );
}
