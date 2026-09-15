"use client";

import { useState } from "react";
import { CheckIcon, CopyIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface CopyButtonProps {
  text: string;
  className?: string;
  label?: string;
}

export function CopyButton({
  text,
  className,
  label = "Copy",
}: CopyButtonProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1400);
    } catch (err) {
      console.error("Failed to copy:", err);
    }
  };

  return (
    <Button
      type="button"
      variant="ghost"
      size="icon-sm"
      className={cn(className)}
      onClick={handleCopy}
      aria-label={label}
      data-copied={copied ? "" : undefined}
    >
      {copied ? <CheckIcon /> : <CopyIcon />}
    </Button>
  );
}
