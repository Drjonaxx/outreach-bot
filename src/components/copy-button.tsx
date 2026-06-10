"use client";

import { useState } from "react";

export function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);

  return (
    <button
      type="button"
      onClick={async () => {
        await navigator.clipboard.writeText(text);
        setCopied(true);
        setTimeout(() => setCopied(false), 1500);
      }}
      className="rounded-md border border-stone-300 bg-white px-3 py-2 text-sm hover:border-stone-500"
    >
      {copied ? "¡Copiada!" : "Copiar respuesta"}
    </button>
  );
}
