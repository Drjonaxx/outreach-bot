"""
Uses Claude to verify AI news and generate platform-specific posts in Spanish.
Runs an agentic loop with tool use.
"""

import json
import os
from typing import Dict, List, Optional, Tuple

import anthropic

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

SYSTEM_PROMPT = """Eres un experto en inteligencia artificial que crea contenido de calidad para redes sociales.

Tu proceso:
1. Analiza las noticias recientes de IA proporcionadas
2. Selecciona la más relevante, impactante y verificable
3. Verifica que cumpla todos los criterios antes de publicar
4. Crea posts adaptados para cada plataforma en español

Criterios de verificación (rechaza si alguno falla):
- Fuente reconocida: blogs oficiales de empresas (OpenAI, Anthropic, Google), medios especializados de tecnología
- Información concreta: anuncios reales, lanzamientos, investigaciones publicadas, no rumores
- Sin sensacionalismo sin base ni clickbait exagerado
- Relevante para profesionales de tecnología e IA

Estilo de escritura:
- Mezcla profesional y casual: informado pero accesible
- Máximo 2-3 emojis si encajan naturalmente
- Directo al punto, sin relleno
- Español neutro (válido para España y Latinoamérica)
- LinkedIn: más elaborado, contexto, 3-5 hashtags al final (#InteligenciaArtificial #IA #MachineLearning)
- Threads: más corto, directo, conversacional, con 1-2 hashtags máximo"""

TOOLS = [
    {
        "name": "publish_posts",
        "description": (
            "Publica los posts generados tras verificar que el contenido es preciso y de fuente confiable. "
            "Llama esta herramienta con verification_passed=false si ningún artículo cumple los criterios."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "article_title": {
                    "type": "string",
                    "description": "Título del artículo seleccionado",
                },
                "article_source": {
                    "type": "string",
                    "description": "Nombre de la fuente del artículo",
                },
                "verification_passed": {
                    "type": "boolean",
                    "description": "True si el artículo pasó todos los criterios de verificación",
                },
                "rejection_reason": {
                    "type": "string",
                    "description": "Si verification_passed es false, razón del rechazo",
                },
                "linkedin_post": {
                    "type": "string",
                    "description": "Post para LinkedIn (máx 1300 caracteres, profesional-casual, con hashtags)",
                },
                "threads_post": {
                    "type": "string",
                    "description": "Post para Threads (máx 500 caracteres, conversacional, 1-2 hashtags)",
                },
            },
            "required": ["article_title", "verification_passed"],
        },
    }
]


def generate_posts(articles: List[Dict]) -> Optional[Tuple[str, str, str, str]]:
    """
    Analyze articles, verify the best one, and generate platform-specific posts.

    Returns (article_title, article_source, linkedin_post, threads_post) or None.
    """
    articles_json = json.dumps(articles, ensure_ascii=False, indent=2)

    messages = [
        {
            "role": "user",
            "content": (
                "Analiza estas noticias recientes de IA y selecciona la mejor para publicar hoy.\n\n"
                f"Noticias disponibles:\n{articles_json}\n\n"
                "Pasos:\n"
                "1. Evalúa cada noticia según los criterios de verificación\n"
                "2. Selecciona la más relevante e impactante que pase la verificación\n"
                "3. Escribe el post de LinkedIn (máx 1300 chars)\n"
                "4. Escribe el post de Threads (máx 500 chars)\n"
                "5. Llama a publish_posts con el resultado\n\n"
                "Si ninguna noticia pasa la verificación, llama a publish_posts con verification_passed=false."
            ),
        }
    ]

    for _ in range(5):
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            system=[
                {
                    "type": "text",
                    "text": SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            tools=TOOLS,
            messages=messages,
        )

        tool_block = next(
            (b for b in response.content if b.type == "tool_use"),
            None,
        )

        if tool_block and tool_block.name == "publish_posts":
            data = tool_block.input
            if not data.get("verification_passed"):
                reason = data.get("rejection_reason", "Sin razón especificada")
                print(f"[content_generator] Contenido rechazado: {reason}")
                return None
            return (
                data["article_title"],
                data.get("article_source", ""),
                data["linkedin_post"],
                data["threads_post"],
            )

        # Continue loop if no tool call yet
        messages.append({"role": "assistant", "content": response.content})
        messages.append({
            "role": "user",
            "content": "Por favor llama a la herramienta publish_posts con el resultado.",
        })

    print("[content_generator] Límite de iteraciones alcanzado sin resultado.")
    return None
