/**
 * Seed: crea un usuario demo, un negocio con BrandVoice y 10 reseñas de ejemplo
 * (mezcla de positivas, neutrales, negativas y UNA de riesgo alto), y encola su
 * procesamiento. Luego corre `npm run worker` para procesarlas.
 *
 * Uso: npm run seed
 * Login demo: demo@agente.local / demo123456
 */
import "dotenv/config";
import { createHash } from "crypto";
import { createAdminClient } from "../src/lib/supabase/admin";

const DEMO_EMAIL = "demo@agente.local";
const DEMO_PASSWORD = "demo123456";

const REVIEWS: Array<{ author: string; rating: number; text: string }> = [
  { author: "Lucía M.", rating: 5, text: "El café más rico del barrio y el personal siempre con una sonrisa. El cold brew es espectacular. ¡Volveré todas las semanas!" },
  { author: "Jorge P.", rating: 5, text: "Pedí una torta de cumpleaños por encargo y quedó perfecta. Atención de diez y precios justos." },
  { author: "Camila R.", rating: 4, text: "Muy lindo lugar para trabajar con la laptop, buen wifi. Solo le falta más variedad de opciones veganas." },
  { author: "Andrés T.", rating: 5, text: "Excelente atención de Mariana, me recomendó el blend de la casa y fue un acierto total." },
  { author: "Sofía G.", rating: 3, text: "El café está bien, pero la música estaba demasiado fuerte para conversar. Lugar limpio eso sí." },
  { author: "Martín L.", rating: 3, text: "Normal. Nada malo, nada memorable. El precio del espresso me pareció un poco alto para la zona." },
  { author: "Valentina S.", rating: 2, text: "Esperé 25 minutos por un capuchino un martes a las 10am. Cuando llegó estaba tibio. Una pena porque el lugar es lindo." },
  { author: "Diego F.", rating: 1, text: "Pedí un sándwich y el pan estaba duro. Se lo dije al mozo y me respondió de mala manera. No vuelvo." },
  { author: "Carolina B.", rating: 2, text: "Reservé mesa para seis personas y cuando llegamos no había registro de la reserva. Terminamos yéndonos a otro lado." },
  // Riesgo ALTO: acusación de salud/seguridad → debe escalar a humano siempre
  { author: "R. Quiroga", rating: 1, text: "Encontré un pelo en la comida y al rato me sentí mal del estómago. Estoy pensando en denunciarlos ante la autoridad sanitaria si no me responden." },
];

async function main() {
  const db = createAdminClient();

  // 1. Usuario demo (idempotente)
  let userId: string;
  const { data: created, error: userErr } = await db.auth.admin.createUser({
    email: DEMO_EMAIL,
    password: DEMO_PASSWORD,
    email_confirm: true,
  });
  if (userErr) {
    if (!/already.*(registered|exists)/i.test(userErr.message)) throw userErr;
    const { data: list } = await db.auth.admin.listUsers();
    const existing = list.users.find((u) => u.email === DEMO_EMAIL);
    if (!existing) throw new Error("Usuario demo existe pero no se pudo recuperar");
    userId = existing.id;
  } else {
    userId = created.user.id;
  }
  console.log(`Usuario demo: ${DEMO_EMAIL} / ${DEMO_PASSWORD} (${userId})`);

  // 2. Negocio demo con BrandVoice (idempotente por nombre+owner)
  const { data: existingBiz } = await db
    .from("businesses")
    .select("id")
    .eq("owner_user_id", userId)
    .eq("name", "Café Luna")
    .maybeSingle();

  let businessId: string;
  if (existingBiz) {
    businessId = existingBiz.id;
    console.log(`Negocio demo ya existía (${businessId})`);
  } else {
    const { data: biz, error: bizErr } = await db
      .from("businesses")
      .insert({
        owner_user_id: userId,
        name: "Café Luna",
        sector: "cafetería",
        auto_publish_policy: "auto_positive_only",
        brand_voice: {
          tono: "cálido, cercano y un poco juguetón, pero siempre profesional",
          valores: ["café de especialidad", "comunidad de barrio", "trato personal"],
          frases_firma: ["¡Te esperamos en Luna! ☕", "Gracias por ser parte del barrio"],
          frases_prohibidas: ["es culpa nuestra", "le pedimos mil disculpas por el desastre"],
          idiomas: ["español"],
        },
      })
      .select("id")
      .single();
    if (bizErr) throw bizErr;
    businessId = biz.id;
    console.log(`Negocio demo creado (${businessId})`);
  }

  // 3. Reseñas + trabajos (idempotente por hash de contenido)
  let inserted = 0;
  for (const r of REVIEWS) {
    const externalId = createHash("sha256")
      .update(`${r.author}::${r.text}`)
      .digest("hex")
      .slice(0, 32);

    const { data, error } = await db
      .from("reviews")
      .upsert(
        {
          business_id: businessId,
          source: "manual",
          external_id: externalId,
          author: r.author,
          rating: r.rating,
          text: r.text,
          raw_payload: { kind: "seed" },
        },
        { onConflict: "business_id,source,external_id", ignoreDuplicates: true }
      )
      .select("id")
      .maybeSingle();
    if (error) throw error;
    if (!data) continue;

    inserted++;
    const { error: jobErr } = await db.from("jobs").insert({
      business_id: businessId,
      type: "process_review",
      payload: { review_id: data.id },
    });
    if (jobErr) throw jobErr;
  }

  console.log(`${inserted} reseñas nuevas encoladas (${REVIEWS.length - inserted} ya existían).`);
  console.log("Listo. Arranca el worker con: npm run worker");
}

main().catch((err) => {
  console.error("Seed falló:", err);
  process.exit(1);
});
