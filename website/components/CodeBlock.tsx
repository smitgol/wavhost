"use client";

import { CopyButton } from "@/components/CopyButton";

type CodeBlockProps = {
  text: string;
  label: string;
};

export function CodeBlock({ text, label }: CodeBlockProps) {
  return (
    <div className="code-wrap">
      <CopyButton text={text} className="copy-btn copy-btn--block" label={label} />
      <pre className="code docs-code">
        <code data-copy>{text}</code>
      </pre>
    </div>
  );
}
