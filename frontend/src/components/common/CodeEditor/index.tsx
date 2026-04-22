import { lazy, Suspense } from "react";
import { Spin, Typography } from "antd";

import type { CodeEditorProps } from "./CodeEditorInner";

const CodeEditorInner = lazy(() => import("./CodeEditorInner"));

const resolveHeight = (height: number | string): string => (typeof height === "number" ? `${height}px` : height);

function CodeEditorFallback({ height }: { height: number | string }) {
  return (
    <div
      className="panel-card"
      style={{
        minHeight: resolveHeight(height),
        display: "grid",
        placeItems: "center",
        border: "1px solid var(--color-border)",
        borderRadius: 16,
        background: "var(--color-bg-surface)",
      }}
    >
      <div style={{ display: "grid", justifyItems: "center", gap: 8 }}>
        <Spin size="small" />
        <Typography.Text type="secondary">编辑器资源加载中...</Typography.Text>
      </div>
    </div>
  );
}

export default function CodeEditor(props: CodeEditorProps) {
  return (
    <Suspense fallback={<CodeEditorFallback height={props.height} />}>
      <CodeEditorInner {...props} />
    </Suspense>
  );
}
