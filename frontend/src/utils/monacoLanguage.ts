const languageMap: Record<string, string> = {
  js: "javascript",
  javascript: "javascript",
  ts: "typescript",
  typescript: "typescript",
  py: "python",
  python: "python",
  cpp: "cpp",
  java: "java",
  go: "go",
  rust: "rust",
  sql: "sql",
};

export const toMonacoLanguage = (value?: string | null): string => {
  const normalized = value?.trim().toLowerCase();
  if (!normalized) {
    return "plaintext";
  }

  return languageMap[normalized] ?? "plaintext";
};
