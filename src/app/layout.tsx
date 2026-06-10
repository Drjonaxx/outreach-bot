import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "Agente de Reseñas",
  description: "Clasifica reseñas, redacta respuestas en tu voz de marca y controla qué se publica.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      <body>
        <header className="border-b border-stone-200 bg-white">
          <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-3">
            <Link href="/dashboard" className="font-semibold tracking-tight">
              ⭐ Agente de Reseñas
            </Link>
            <nav className="flex items-center gap-4 text-sm text-stone-600">
              <Link href="/dashboard" className="hover:text-stone-900">Negocios</Link>
              <Link href="/billing" className="hover:text-stone-900">Facturación</Link>
              <form action="/auth/signout" method="post">
                <button className="hover:text-stone-900">Salir</button>
              </form>
            </nav>
          </div>
        </header>
        <main className="mx-auto max-w-5xl px-4 py-8">{children}</main>
      </body>
    </html>
  );
}
