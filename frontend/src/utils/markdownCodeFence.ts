const fencedBlockPattern = /^\s*```[ \t]*[^`\n\r]*\r?\n?([\s\S]*?)\r?\n```[ \t]*\s*$/;

export const stripMarkdownCodeFences = (value?: string | null): string => {
  if (!value) {
    return "";
  }

  const fencedBlock = value.match(fencedBlockPattern);
  if (!fencedBlock) {
    return value;
  }

  return fencedBlock[1].replace(/\r\n?/g, "\n").trim();
};
