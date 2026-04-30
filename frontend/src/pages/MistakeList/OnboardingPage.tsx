import { useState } from "react";
import { Button, Space, Typography, message } from "antd";
import { useNavigate } from "react-router-dom";

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
    void message.success("题面已抓取，请补充错误代码和错因");
    navigate("/mistakes/new");
  };

  const handleLoadDemo = async () => {
    setLoadingDemo(true);
    try {
      await importPayload(demoData as Parameters<typeof importPayload>[0], "skip_existing");
      localStorage.setItem(importedKey, "1");
      onImported();
      void message.success("Demo 数据已载入");
    } catch {
      void message.error("Demo 数据载入失败");
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
        AC 的最后一块拼图
      </Typography.Title>
      <Typography.Paragraph type="secondary" style={{ fontSize: 16, marginBottom: 32 }}>
        专注逻辑短板，自动提取错因，定制你的专属遗忘曲线
      </Typography.Paragraph>

      {/* 代码预览卡 */}
      <div className="onboarding-diff-card">
        <div className="diff-del">- int sum = a * b;  // ❌ 整型溢出</div>
        <div className="diff-add">+ long long sum = (long long)a * b;</div>
        <div className="diff-info">💡 AI: 发现 int 溢出，建议改用 long long</div>
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
          ⚡ 载入经典错误 Demo 体验
        </Button>
        <Button type="link" onClick={() => navigate("/mistakes/new")}>
          手动创建空白错题
        </Button>
      </Space>
    </div>
  );
}
