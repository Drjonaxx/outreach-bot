"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import Navbar from "@/components/Navbar";

type Site = {
  id: string;
  name: string;
  description: string;
  published: boolean;
  slug: string;
  createdAt: string;
};

export default function DashboardPage() {
  const [sites, setSites] = useState<Site[]>([]);
  const [loading, setLoading] = useState(true);
  const searchParams = useSearchParams();
  const justPublished = searchParams.get("published");

  useEffect(() => {
    fetch("/api/sites")
      .then((r) => r.json())
      .then((data) => setSites(data.sites ?? []))
      .finally(() => setLoading(false));
  }, []);

  async function handlePublish(siteId: string) {
    const res = await fetch("/api/stripe/checkout", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ siteId }),
    });
    const data = await res.json();
    if (data.url) window.location.href = data.url;
  }

  async function handleDelete(siteId: string) {
    if (!confirm("Delete this site? This cannot be undone.")) return;
    await fetch(`/api/sites/${siteId}`, { method: "DELETE" });
    setSites((prev) => prev.filter((s) => s.id !== siteId));
  }

  const appUrl = process.env.NEXT_PUBLIC_APP_URL ?? "";

  return (
    <div className="min-h-screen">
      <Navbar />
      <main className="mx-auto max-w-5xl px-6 py-12">
        <div className="mb-8 flex items-center justify-between">
          <h1 className="text-3xl font-bold text-gray-900">My sites</h1>
          <Link
            href="/generate"
            className="rounded-md bg-indigo-600 px-5 py-2.5 text-sm font-medium text-white hover:bg-indigo-700"
          >
            + New site
          </Link>
        </div>

        {justPublished && (
          <div className="mb-6 rounded-lg border border-green-200 bg-green-50 p-4 text-green-800">
            Your site has been published! It's now live at its public URL.
          </div>
        )}

        {loading && <p className="text-gray-500">Loading…</p>}

        {!loading && sites.length === 0 && (
          <div className="rounded-xl border-2 border-dashed border-gray-200 py-20 text-center">
            <p className="mb-4 text-gray-500">No sites yet.</p>
            <Link
              href="/generate"
              className="rounded-md bg-indigo-600 px-5 py-2.5 text-sm font-medium text-white hover:bg-indigo-700"
            >
              Generate your first site
            </Link>
          </div>
        )}

        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {sites.map((site) => (
            <div key={site.id} className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
              <div className="mb-3 flex items-start justify-between">
                <h2 className="font-semibold text-gray-900">{site.name}</h2>
                {site.published ? (
                  <span className="rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700">
                    Published
                  </span>
                ) : (
                  <span className="rounded-full bg-yellow-100 px-2 py-0.5 text-xs font-medium text-yellow-700">
                    Draft
                  </span>
                )}
              </div>
              <p className="mb-4 line-clamp-2 text-sm text-gray-500">{site.description}</p>

              <div className="flex flex-wrap gap-2">
                <Link
                  href={`/edit/${site.id}`}
                  className="rounded border border-gray-300 px-3 py-1 text-xs font-medium text-gray-700 hover:bg-gray-50"
                >
                  Edit
                </Link>
                {site.published ? (
                  <a
                    href={`${appUrl}/s/${site.slug}`}
                    target="_blank"
                    rel="noreferrer"
                    className="rounded border border-indigo-300 px-3 py-1 text-xs font-medium text-indigo-700 hover:bg-indigo-50"
                  >
                    View live ↗
                  </a>
                ) : (
                  <button
                    onClick={() => handlePublish(site.id)}
                    className="rounded bg-indigo-600 px-3 py-1 text-xs font-medium text-white hover:bg-indigo-700"
                  >
                    Publish ($9)
                  </button>
                )}
                <button
                  onClick={() => handleDelete(site.id)}
                  className="rounded border border-red-200 px-3 py-1 text-xs font-medium text-red-600 hover:bg-red-50"
                >
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      </main>
    </div>
  );
}
