import ReactMarkdown from "react-markdown";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import type { PluggableList } from "unified";

const remarkPlugins: PluggableList = [[remarkMath, { singleDollarTextMath: true }]];
const rehypePlugins: PluggableList = [[rehypeKatex, { throwOnError: false, strict: false, trust: false }]];

export default function MarkdownRenderer({ children }: { children?: string }) {
  return (
    <ReactMarkdown remarkPlugins={remarkPlugins} rehypePlugins={rehypePlugins}>
      {children ?? ""}
    </ReactMarkdown>
  );
}
