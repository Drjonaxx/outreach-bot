"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";

type Site = {
  id: string;
  name: string;
  description: string;
  html: string;
  published: boolean;
  slug: string;
};

export default function EditPage() {
  const { siteId } = useParams<{ siteId: string }>();
  const router = useRouter();
  const [site, setSite] = useState<Site | null>(null);
  const [html, setHtml] = useState("");
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    fetch(`/api/sites/${siteId}`)
      .then((r) => r.json())
      .then((data) => {
        if (data.site) {
          setSite(data.site);
          setHtml(data.site.html);
        }
      });
  }, [siteId]);

  const handleSave = useCallback(async () => {
    setSaving(true);
    setError("");
    try {
      const res = await fetch(`/api/sites/${siteId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ html }),
      });
      if (!res.ok) {
        setError("Save failed.");
      } else {
        setSaved(true);
        setTimeout(() => setSaved(false), 2000);
      }
    } finally {
      setSaving(false);
    }
  }, [siteId, html]);

  async function handlePublish() {
    const res = await fetch("/api/stripe/checkout", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ siteId }),
    });
    const data = await res.json();
    if (data.url) window.location.href = data.url;
  }

  if (!site) {
    return (
      <div className="flex min-h-screen items-center justify-center text-gray-400">
        Loading…
      </div>
    );
  }

  const appUrl = typeof window !== "undefined" ? window.location.origin : "";

  return (
    <div className="flex h-screen flex-col">
      {/* Top bar */}
      <header className="flex items-center justify-between border-b border-gray-200 bg-white px-4 py-3">
        <div className="flex items-center gap-3">
          <Link href="/dashboard" className="text-sm text-gray-500 hover:text-gray-700">
            ← Dashboard
          </Link>
          <span className="text-gray-300">|</span>
          <span className="font-semibold text-gray-900">{site.name}</span>
          {site.published && (
            <a
              href={`${appUrl}/s/${site.slug}`}
              target="_blank"
              rel="noreferrer"
              className="text-xs text-indigo-600 underline hover:text-indigo-800"
            >
              View live ↗
            </a>
          )}
        </div>
        <div className="flex items-center gap-3">
          {error && <span className="text-sm text-red-600">{error}</span>}
          {saved && <span className="text-sm text-green-600">Saved!</span>}
          <button
            onClick={handleSave}
            disabled={saving}
            className="rounded border border-gray-300 px-4 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
          >
            {saving ? "Saving…" : "Save"}
          </button>
          {!site.published && (
            <button
              onClick={handlePublish}
              className="rounded bg-indigo-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-indigo-700"
            >
              Publish ($9) →
            </button>
          )}
        </div>
      </header>

      {/* Split pane */}
      <div className="flex flex-1 overflow-hidden">
        {/* Code editor */}
        <div className="flex w-1/2 flex-col border-r border-gray-200">
          <div className="border-b border-gray-100 bg-gray-50 px-4 py-2 text-xs font-medium uppercase tracking-wider text-gray-400">
            HTML
          </div>
          <textarea
            value={html}
            onChange={(e) => setHtml(e.target.value)}
            spellCheck={false}
            className="flex-1 resize-none bg-gray-900 p-4 font-mono text-sm text-gray-100 focus:outline-none"
          />
        </div>

        {/* Live preview */}
        <div className="flex w-1/2 flex-col">
          <div className="border-b border-gray-100 bg-gray-50 px-4 py-2 text-xs font-medium uppercase tracking-wider text-gray-400">
            Preview
          </div>
          <iframe
            srcDoc={html}
            sandbox="allow-scripts allow-same-origin"
            className="flex-1 w-full border-none"
            title="Site preview"
          />
        </div>
      </div>
    </div>
  );
}
