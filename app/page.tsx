import Link from "next/link";
import { SignedIn, SignedOut } from "@clerk/nextjs";
import Navbar from "@/components/Navbar";

export default function LandingPage() {
  return (
    <div className="min-h-screen">
      <Navbar />
      <main className="mx-auto max-w-4xl px-6 py-24 text-center">
        <h1 className="mb-6 text-5xl font-extrabold tracking-tight text-gray-900">
          Your business website,{" "}
          <span className="text-indigo-600">ready in seconds</span>
        </h1>
        <p className="mx-auto mb-10 max-w-2xl text-xl text-gray-600">
          Describe your business and InstaBiz Sites generates a complete, professional
          website using AI. Preview for free — pay once to publish.
        </p>
        <div className="flex flex-col items-center gap-4 sm:flex-row sm:justify-center">
          <SignedIn>
            <Link
              href="/generate"
              className="rounded-lg bg-indigo-600 px-8 py-4 text-lg font-semibold text-white shadow hover:bg-indigo-700"
            >
              Generate my site →
            </Link>
            <Link
              href="/dashboard"
              className="rounded-lg border border-gray-300 bg-white px-8 py-4 text-lg font-semibold text-gray-700 hover:bg-gray-50"
            >
              My dashboard
            </Link>
          </SignedIn>
          <SignedOut>
            <Link
              href="/sign-up"
              className="rounded-lg bg-indigo-600 px-8 py-4 text-lg font-semibold text-white shadow hover:bg-indigo-700"
            >
              Start for free →
            </Link>
            <Link
              href="/sign-in"
              className="rounded-lg border border-gray-300 bg-white px-8 py-4 text-lg font-semibold text-gray-700 hover:bg-gray-50"
            >
              Sign in
            </Link>
          </SignedOut>
        </div>

        <div className="mt-24 grid gap-8 text-left sm:grid-cols-3">
          {[
            {
              title: "1. Describe your business",
              body: "Tell us what you do, your name, and the style you want.",
            },
            {
              title: "2. AI generates your site",
              body: "Claude builds a full HTML page tailored to your business in seconds.",
            },
            {
              title: "3. Pay once to publish",
              body: "Preview for free. Pay $9 to get a permanent public URL.",
            },
          ].map((step) => (
            <div key={step.title} className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
              <h3 className="mb-2 font-semibold text-gray-900">{step.title}</h3>
              <p className="text-gray-600">{step.body}</p>
            </div>
          ))}
        </div>
      </main>
    </div>
  );
}
