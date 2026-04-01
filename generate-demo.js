import Anthropic from "@anthropic-ai/sdk";
import readline from "readline";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import dotenv from "dotenv";

dotenv.config();

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout,
});

function ask(question) {
  return new Promise((resolve) => rl.question(question, resolve));
}

function slugify(text) {
  return text
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9\s-]/g, "")
    .replace(/\s+/g, "-");
}

async function main() {
  const businessName = await ask("Business name: ");
  const category = await ask("Category (e.g. restaurant, salon, gym): ");
  const city = await ask("City: ");
  rl.close();

  const client = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });

  console.log("\nGenerating website...");

  const prompt = `Crea un sitio web HTML completo en un solo archivo para el siguiente negocio local:

- Nombre del negocio: ${businessName}
- Categoría: ${category}
- Ciudad: ${city}

El sitio debe incluir:
1. Sección hero con el nombre del negocio y un eslogan atractivo
2. Sección "Sobre nosotros" con una descripción breve
3. Sección de servicios con al menos 3 servicios típicos de la categoría
4. Llamada a la acción (CTA) con un botón de WhatsApp (usa href="https://wa.me/1234567890")
5. Footer con el nombre del negocio y la ciudad

Requisitos técnicos:
- Todo el HTML, CSS y JS en un único archivo .html
- Diseño moderno con gradientes, sombras y animaciones sutiles
- Totalmente responsive (mobile-first)
- Fuentes de Google Fonts
- Colores acordes a la categoría "${category}" (elige una paleta apropiada)
- Todo el contenido en español

Responde ÚNICAMENTE con el código HTML completo, sin explicaciones ni bloques de código markdown.`;

  const stream = client.messages.stream({
    model: "claude-sonnet-4-20250514",
    max_tokens: 8192,
    messages: [{ role: "user", content: prompt }],
  });

  let html = "";
  process.stdout.write("Generating");
  let dotCount = 0;

  for await (const event of stream) {
    if (
      event.type === "content_block_delta" &&
      event.delta.type === "text_delta"
    ) {
      html += event.delta.text;
      dotCount++;
      if (dotCount % 100 === 0) process.stdout.write(".");
    }
  }

  console.log(" done.\n");

  // Strip markdown code fences if Claude wrapped the output
  html = html
    .replace(/^```html\s*/i, "")
    .replace(/^```\s*/i, "")
    .replace(/\s*```$/i, "")
    .trim();

  const demosDir = path.join(__dirname, "demos");
  if (!fs.existsSync(demosDir)) {
    fs.mkdirSync(demosDir, { recursive: true });
  }

  const filename = `${slugify(businessName)}.html`;
  const outputPath = path.join(demosDir, filename);
  fs.writeFileSync(outputPath, html, "utf8");

  console.log(`File saved: ${outputPath}`);
}

main().catch((err) => {
  console.error("Error:", err.message);
  process.exit(1);
});
