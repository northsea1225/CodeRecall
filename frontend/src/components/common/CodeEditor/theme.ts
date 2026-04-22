import type { Monaco } from "@monaco-editor/react";

const readCssVar = (styles: CSSStyleDeclaration, name: string, fallback: string): string =>
  styles.getPropertyValue(name).trim() || fallback;

export const defineCodeRecallThemes = (monaco: Monaco) => {
  const styles = window.getComputedStyle(document.documentElement);
  const bgCanvas = readCssVar(styles, "--monaco-bg", "#ffffff");
  const textPrimary = readCssVar(styles, "--color-text-primary", "#111827");
  const textTertiary = readCssVar(styles, "--color-text-tertiary", "#6b7280");
  const borderDefault = readCssVar(styles, "--color-border", "#e2e8f0");
  const primary = readCssVar(styles, "--color-primary", "#2563eb");

  // Code token colors (IDE-style, not semantic app colors)
  const codeTokenString = readCssVar(styles, "--code-token-string", "#A31515");
  const codeTokenKeyword = readCssVar(styles, "--code-token-keyword", "#0000FF");
  const codeTokenNumber = readCssVar(styles, "--code-token-number", "#098658");
  const codeTokenComment = readCssVar(styles, "--code-token-comment", "#6A7172");

  // Diff colors — Monaco's color API requires hex format; rgba() strings are silently ignored.
  // Word-level (text) colors match line-level to avoid char-overlay vivid blocks.
  const isDark = document.documentElement.getAttribute("data-theme") === "dark";
  const diff = isDark
    ? {
        addedLine: "#2EA04326",   // rgba(46,160,67,0.15)
        addedText: "#2EA04366",   // rgba(46,160,67,0.40)
        removedLine: "#F8514926", // rgba(248,81,73,0.15)
        removedText: "#F8514966", // rgba(248,81,73,0.40)
      }
    : {
        addedLine: "#e6ffec",   // GitHub pastel green
        addedText: "#e6ffec",   // same as addedLine — char overlay invisible, no vivid block
        removedLine: "#ffebe9", // GitHub pastel red
        removedText: "#ffebe9", // same as removedLine — char overlay invisible, no vivid block
      };

  const sharedRules = [
    { token: "comment", foreground: codeTokenComment.replace("#", ""), fontStyle: "italic" },
    { token: "keyword", foreground: codeTokenKeyword.replace("#", "") },
    { token: "number", foreground: codeTokenNumber.replace("#", "") },
    { token: "string", foreground: codeTokenString.replace("#", "") },
  ];

  const sharedDiffColors = {
    "diffEditor.insertedLineBackground": diff.addedLine,
    "diffEditor.insertedTextBackground": diff.addedText,
    "diffEditor.removedLineBackground": diff.removedLine,
    "diffEditor.removedTextBackground": diff.removedText,
    "diffEditorGutter.insertedLineBackground": "#00000000",
    "diffEditorGutter.removedLineBackground": "#00000000",
  };

  monaco.editor.defineTheme("coderecall-light", {
    base: "vs",
    inherit: true,
    rules: sharedRules,
    colors: {
      "editor.background": bgCanvas,
      "editor.foreground": textPrimary,
      "editorLineNumber.foreground": textTertiary,
      "editorCursor.foreground": primary,
      "editor.selectionBackground": "#2563EB2E",      // rgba(37,99,235,0.18) as 8-digit hex
      "editor.lineHighlightBackground": "#0F172A0A",  // rgba(15,23,42,0.04) as 8-digit hex
      "editorIndentGuide.background1": "#6B728029",   // rgba(107,114,128,0.16) as 8-digit hex
      "scrollbarSlider.background": "#94a3b8",
      "scrollbarSlider.hoverBackground": "#64748b",
      "scrollbarSlider.activeBackground": "#475569",
      ...sharedDiffColors,
    },
  });

  monaco.editor.defineTheme("coderecall-dark", {
    base: "vs-dark",
    inherit: true,
    rules: sharedRules,
    colors: {
      "editor.background": bgCanvas,
      "editor.foreground": textPrimary,
      "editorLineNumber.foreground": textTertiary,
      "editorCursor.foreground": primary,
      "editor.selectionBackground": "#2563EB3D",      // rgba(37,99,235,0.24) as 8-digit hex
      "editor.lineHighlightBackground": "#FFFFFF0A",  // very subtle highlight, won't clash with diff
      "editorIndentGuide.background1": borderDefault,
      "scrollbarSlider.background": "#475569",
      "scrollbarSlider.hoverBackground": "#64748b",
      "scrollbarSlider.activeBackground": "#94a3b8",
      ...sharedDiffColors,
    },
  });
};
