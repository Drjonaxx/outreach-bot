# outreach-bot

Generates personalized Instagram DMs and cold emails in Spanish for local businesses, powered by the Anthropic Claude API.

The sender is positioned as an **AI content & web specialist** helping local businesses grow their digital presence.

---

## Setup

### 1. Install dependencies

```bash
npm install
```

### 2. Set your API key

Copy the example env file and add your key:

```bash
cp .env.example .env
```

Edit `.env`:

```
ANTHROPIC_API_KEY=sk-ant-...
```

Get your key at [console.anthropic.com](https://console.anthropic.com).

---

## Running the generator

```bash
npm start
# or
node generate.js
```

The script reads `businesses.csv`, calls Claude once per business, and writes:

- **`output.csv`** — all messages in a spreadsheet-friendly format
- **`output.md`** — a pretty Markdown file with each business in its own section, easy to copy-paste

---

## Adding businesses to businesses.csv

Open `businesses.csv` in any spreadsheet app or text editor. The columns are:

| Column | Required | Description |
|---|---|---|
| `name` | Yes | Business name |
| `niche` | Yes | What they do (e.g. "Barbería clásica", "Food truck") |
| `instagram_handle` | Yes | Their Instagram handle including `@` |
| `email` | Yes | Contact email address |
| `location` | Yes | City or neighbourhood |
| `extra_detail` | No | Optional notes — products, personality, audience, etc. |

**Example row:**

```
Taquería El Güero,Taquería tradicional,@taqueriaelguero,elguero@tacos.mx,Puebla,Especialidad en tacos de canasta y tlayudas. Clientela principalmente familiar.
```

The more you fill in `extra_detail`, the more personalized the messages will be.

---

## Output format

### output.csv columns

| Column | Content |
|---|---|
| `business_name` | Business name from the CSV |
| `instagram_handle` | Instagram handle |
| `email` | Email address |
| `dm_message` | Short Instagram DM (max 4 lines, casual) |
| `email_subject` | Cold email subject line |
| `email_body` | Cold email body with CTA |

### output.md

Each business gets a formatted section with both messages, ready to copy-paste directly into Instagram DMs or your email client.

---

## Configuration

You can tweak these constants at the top of `generate.js`:

| Constant | Default | Description |
|---|---|---|
| `MODEL` | `claude-sonnet-4-0` | Claude model to use |
| `DELAY_MS` | `1200` | Milliseconds between API calls |
| `MAX_RETRIES` | `3` | Retry attempts on API errors |

---

## Notes

- Messages are always written in **Spanish**.
- The script retries automatically on rate-limit or server errors with exponential backoff.
- If a business fails (e.g. API error), it's marked `ERROR` in the CSV and the script continues with the rest.
- `output.csv` and `output.md` are excluded from git (listed in `.gitignore`).
