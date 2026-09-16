"use client";

import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { CopyButton } from "@/components/CopyButton";

type CodeSnippetProps = {
  title: string;
  text: string;
  label: string;
  defaultOpen?: boolean;
};

export function CodeSnippet({
  title,
  text,
  label,
  defaultOpen = false,
}: CodeSnippetProps) {
  return (
    <Accordion
      type="single"
      collapsible
      defaultValue={defaultOpen ? "snippet" : undefined}
      className="my-2"
    >
      <AccordionItem value="snippet" className="border-border rounded-lg border px-3">
        <AccordionTrigger className="py-2.5 text-xs font-semibold tracking-wide uppercase hover:no-underline">
          {title}
        </AccordionTrigger>
        <AccordionContent>
          <div className="code-wrap relative">
            <CopyButton
              text={text}
              className="copy-btn copy-btn--block"
              label={label}
            />
            <pre className="code docs-code">
              <code data-copy>{text}</code>
            </pre>
          </div>
        </AccordionContent>
      </AccordionItem>
    </Accordion>
  );
}
