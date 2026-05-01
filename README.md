# AI Outreach Bot

Genera emails de cold outreach hiperpersonalizados con Claude y los crea como borradores en tu Gmail. En segundos.

Lo que hacen Lemlist, Apollo e Instantly por $300/mes — en tu máquina, gratis.

## Setup (5 minutos)

### 1. Instala dependencias
```bash
pip install -r requirements.txt
```

### 2. Configura tu API key de Anthropic
```bash
cp .env.example .env
# edita .env con tu ANTHROPIC_API_KEY
export $(cat .env | xargs)
```

### 3. (Opcional) Conecta Gmail para crear borradores automáticamente

1. Ve a [Google Cloud Console](https://console.cloud.google.com/)
2. Crea un proyecto → habilita Gmail API
3. Credenciales → OAuth 2.0 → descarga como `credentials.json`
4. Primera vez que corras el bot abrirá el browser para autorizar

### 4. Prepara tu CSV de leads

```csv
nombre,empresa,rol,email,contexto
Carlos Ramírez,TechStartup MX,CEO,carlos@example.com,Acaban de levantar una ronda seed
```

Columnas mínimas: `nombre` (o `name`), `email` (o `correo`)  
Columnas opcionales: `empresa`/`company`, `rol`/`role`, `contexto`/`context`

## Uso

```bash
# Con Gmail — crea borradores automáticamente
python outreach.py leads.csv --sender "Soy Juan, tengo una agencia de automatización"

# Solo ver los emails generados (sin tocar Gmail)
python outreach.py leads.csv --sender "..." --dry-run

# Guardar en archivo específico
python outreach.py leads.csv --sender "..." --output mis_emails.json
```

## Resultado

- Borradores listos en tu Gmail → solo entras y das Send
- Archivo `emails_generados.json` con todos los emails para referencia

## Casos de uso

| Quién | Para qué |
|-------|----------|
| Agencia | Conseguir nuevos clientes |
| Influencer | Cerrar brand deals |
| Startup | Validar mercado con early adopters |
| Freelancer | Conseguir proyectos |
| Reclutador | Sourcing de talento |
| Vendedor | Pipeline de ventas |
