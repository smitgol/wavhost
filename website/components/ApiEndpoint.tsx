"use client";

import type { ReactNode } from "react";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";

type ApiEndpointProps = {
  id: string;
  method: "get" | "post" | "delete";
  path: string;
  description: ReactNode;
  children?: ReactNode;
  defaultOpen?: boolean;
};

export function ApiEndpoint({
  id,
  method,
  path,
  description,
  children,
  defaultOpen = false,
}: ApiEndpointProps) {
  return (
    <Accordion
      type="single"
      collapsible
      defaultValue={defaultOpen ? id : undefined}
      className="endpoint-accordion"
    >
      <AccordionItem value={id} className="endpoint border-0" id={id}>
        <AccordionTrigger className="endpoint-head hover:no-underline">
          <span className="endpoint-head-lead">
            <span className={`method method-${method}`}>{method.toUpperCase()}</span>
            <code className="endpoint-path">{path}</code>
          </span>
        </AccordionTrigger>
        <AccordionContent className="endpoint-body-wrap">
          <div className="endpoint-body">
            <p className="endpoint-desc">{description}</p>
            {children}
          </div>
        </AccordionContent>
      </AccordionItem>
    </Accordion>
  );
}
