import { useEffect, useRef } from "react";
import Editor from "@monaco-editor/react";
import type { Monaco } from "@monaco-editor/react";

import { defineCodeRecallThemes } from "./theme";

export interface CodeEditorProps {
  value?: string;
  onChange?: (value: string) => void;
  language: string;
  height: number | string;
  theme?: string;
}

export default function CodeEditorInner({
  value = "",
  onChange,
  language,
  height,
  theme = "coderecall-light",
}: CodeEditorProps) {
  const monacoRef = useRef<Monaco | null>(null);

  useEffect(() => {
    const monaco = monacoRef.current;
    if (!monaco) {
      return;
    }

    defineCodeRecallThemes(monaco);
    monaco.editor.setTheme(theme);
  }, [theme]);

  return (
    <Editor
      value={value}
      language={language}
      height={height}
      theme={theme}
      beforeMount={defineCodeRecallThemes}
      onMount={(_editor, monaco) => {
        monacoRef.current = monaco;
      }}
      options={{
        minimap: { enabled: false },
        lineNumbers: "on",
        automaticLayout: true,
        scrollBeyondLastLine: false,
      }}
      onChange={(nextValue) => onChange?.(nextValue ?? "")}
    />
  );
}
