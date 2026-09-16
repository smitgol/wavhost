"use client";

import type { ReactNode } from "react";
import { ChevronDownIcon } from "lucide-react";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";

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
    <Collapsible id={id} defaultOpen={defaultOpen} className="endpoint">
      <CollapsibleTrigger className="endpoint-head">
        <span className="endpoint-head-lead">
          <span className={`method method-${method}`}>{method.toUpperCase()}</span>
          <code className="endpoint-path">{path}</code>
        </span>
        <ChevronDownIcon className="endpoint-chevron size-4 shrink-0" aria-hidden />
      </CollapsibleTrigger>
      <CollapsibleContent className="endpoint-body-wrap">
        <div className="endpoint-body">
          <p className="endpoint-desc">{description}</p>
          {children}
        </div>
      </CollapsibleContent>
    </Collapsible>
  );
}
