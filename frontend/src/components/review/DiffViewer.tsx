import { useMemo, useEffect, useRef } from "react";
import { DiffEditor } from "@monaco-editor/react";
import type { DiffEditorProps, Monaco } from "@monaco-editor/react";
import { Typography } from "antd";
import { useTranslation } from "react-i18next";

import { defineCodeRecallThemes } from "../common/CodeEditor/theme";
import { toMonacoLanguage } from "../../utils/monacoLanguage";
import { stripMarkdownCodeFences } from "../../utils/markdownCodeFence";

interface DiffViewerProps {
  originalCode: string;
  modifiedCode: string;
  language: string;
  description?: string;
  height?: number;
  theme?: string;
}

export default function DiffViewer({
  originalCode,
  modifiedCode,
  language,
  description,
  height = 360,
  theme = "coderecall-light",
}: DiffViewerProps) {
  const { t } = useTranslation();
  const monacoLanguage = toMonacoLanguage(language);
  const monacoRef = useRef<Monaco | null>(null);

  // Strip markdown fences defensively — callers may pass raw markdown fields
  const strippedOriginalCode = useMemo(() => stripMarkdownCodeFences(originalCode), [originalCode]);
  const strippedModifiedCode = useMemo(() => stripMarkdownCodeFences(modifiedCode), [modifiedCode]);

  useEffect(() => {
    const monaco = monacoRef.current;
    if (!monaco) {
      return;
    }

    defineCodeRecallThemes(monaco);
    monaco.editor.setTheme(theme);
  }, [theme]);

  return (
    <div className="review-diff-shell">
      <div className="review-diff-copy">
        <Typography.Text strong>{description ?? t("reviewComponents.diffViewerDesc")}</Typography.Text>
        <Typography.Text className="soft-note">Language: {monacoLanguage}</Typography.Text>
      </div>
      <DiffEditor
        original={strippedOriginalCode}
        modified={strippedModifiedCode}
        language={monacoLanguage}
        theme={theme}
        height={height}
        beforeMount={defineCodeRecallThemes}
        onMount={(_editor, monaco) => {
          monacoRef.current = monaco;
        }}
        options={{
          readOnly: true,
          originalEditable: false,
          renderSideBySide: true,
          diffAlgorithm: "advanced",
          ignoreTrimWhitespace: false,
          renderIndicators: true,
          useInlineViewWhenSpaceIsLimited: false,
          renderOverviewRuler: false,
          automaticLayout: true,
          scrollBeyondLastLine: false,
          minimap: { enabled: false },
          wordWrap: "off",
        } as DiffEditorProps["options"]}
      />
    </div>
  );
}
