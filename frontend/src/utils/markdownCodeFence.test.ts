import { describe, expect, it } from "vitest";

import { stripMarkdownCodeFences } from "./markdownCodeFence";

describe("stripMarkdownCodeFences", () => {
  it("strips a fenced python block to raw code", () => {
    expect(stripMarkdownCodeFences("```python\ndef foo(): pass\n```")).toBe("def foo(): pass");
  });

  it("handles different language specifiers", () => {
    expect(stripMarkdownCodeFences("```javascript\nconsole.log('ok');\n```")).toBe("console.log('ok');");
    expect(stripMarkdownCodeFences("```typescript\nconst ok: boolean = true;\n```")).toBe(
      "const ok: boolean = true;",
    );
    expect(stripMarkdownCodeFences("```java\nclass Main {}\n```")).toBe("class Main {}");
  });

  it("returns unfenced content as-is", () => {
    expect(stripMarkdownCodeFences("def foo(): pass")).toBe("def foo(): pass");
    expect(stripMarkdownCodeFences("  keep surrounding whitespace  ")).toBe("  keep surrounding whitespace  ");
  });

  it("strips fences without a language specifier", () => {
    expect(stripMarkdownCodeFences("```\nreturn 42\n```")).toBe("return 42");
  });
});
