import { useState } from "react";
import { Alert, Button, Card, Space, Typography, Upload } from "antd";
import { useTranslation } from "react-i18next";

import { exportAll, importPayload } from "../../services/importExportService";
import { useUIStore } from "../../stores/uiStore";
import type { ImportPayload, ImportResponse } from "../../types/mistake";

const downloadJson = (filename: string, payload: unknown) => {
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
};

export default function ImportExportPage() {
  const { t } = useTranslation();
  const [lastImport, setLastImport] = useState<ImportResponse | null>(null);
  const [lastFileName, setLastFileName] = useState<string | null>(null);
  const setGlobalLoading = useUIStore((state) => state.setGlobalLoading);
  const showToast = useUIStore((state) => state.showToast);

  const parseImportPayload = async (file: File): Promise<ImportPayload> => {
    const rawText = await file.text();

    let parsed: unknown;
    try {
      parsed = JSON.parse(rawText);
    } catch {
      throw new Error(t("importExport.errorInvalidJson"));
    }

    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
      throw new Error(t("importExport.errorInvalidStructure"));
    }

    const payload = parsed as Partial<ImportPayload>;
    if (payload.version !== "v1") {
      throw new Error(t("importExport.errorVersionV1"));
    }
    if (payload.schema_version && payload.schema_version !== "v2") {
      throw new Error(t("importExport.errorVersionV2"));
    }

    return payload as ImportPayload;
  };

  const handleExport = async () => {
    setGlobalLoading(true);
    try {
      const response = await exportAll();
      downloadJson("coderecall-export.json", response.data);
      showToast("success", t("importExport.exportSuccess", { count: response.data.mistakes.length }));
    } catch (exportError) {
      showToast("error", exportError instanceof Error ? exportError.message : t("importExport.exportFailed"));
    } finally {
      setGlobalLoading(false);
    }
  };

  const handleImport = async (file: File) => {
    setGlobalLoading(true);
    try {
      const payload = await parseImportPayload(file);
      const response = await importPayload(payload);
      setLastImport(response);
      setLastFileName(file.name);
      showToast(
        "success",
        t("importExport.importSuccess", {
          mistakes: response.imported.mistakes,
          categories: response.imported.categories,
          tags: response.imported.tags,
          skipped: response.skipped.length,
        }),
      );
    } catch (importError) {
      showToast("error", importError instanceof Error ? importError.message : t("importExport.importFailed"));
    } finally {
      setGlobalLoading(false);
    }
  };

  return (
    <div className="page-stack">
      <div className="page-title-copy">
        <Typography.Title level={2} style={{ margin: 0 }}>
          {t("importExport.title")}
        </Typography.Title>
      </div>

      <div className="import-grid">
        <Card className="panel-card" title={t("importExport.exportTitle")}>
          <Typography.Paragraph className="soft-note">
            {t("importExport.exportDesc")}
          </Typography.Paragraph>
          <Button type="primary" onClick={() => void handleExport()}>
            {t("importExport.exportButton")}
          </Button>
        </Card>

        <Card className="panel-card" title={t("importExport.importTitle")}>
          <Space direction="vertical" size="middle" style={{ width: "100%" }}>
            <Typography.Paragraph className="soft-note" style={{ marginBottom: 0 }}>
              {t("importExport.importDesc")}
            </Typography.Paragraph>
            <Upload
              accept=".json,application/json"
              maxCount={1}
              showUploadList={false}
              beforeUpload={(file) => {
                void handleImport(file);
                return Upload.LIST_IGNORE;
              }}
            >
              <Button type="primary">{t("importExport.importButton")}</Button>
            </Upload>
            <Alert
              type="info"
              showIcon
              message={t("importExport.importHint")}
            />
          </Space>
        </Card>
      </div>

      {lastImport ? (
        <Card className="panel-card" title={t("importExport.lastImportTitle")}>
          <Space direction="vertical">
            {lastFileName ? (
              <Typography.Text>{t("importExport.fileLabel", { name: lastFileName })}</Typography.Text>
            ) : null}
            <Typography.Text>{t("importExport.importedMistakes", { count: lastImport.imported.mistakes })}</Typography.Text>
            <Typography.Text>{t("importExport.importedCategories", { count: lastImport.imported.categories })}</Typography.Text>
            <Typography.Text>{t("importExport.importedTags", { count: lastImport.imported.tags })}</Typography.Text>
            <Typography.Text className="soft-note">{t("importExport.skipped", { count: lastImport.skipped.length })}</Typography.Text>
            <Typography.Text className="soft-note">{t("importExport.importDone")}</Typography.Text>
          </Space>
        </Card>
      ) : null}
    </div>
  );
}
