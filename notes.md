# Project Notes — Text-to-SQL with Guardrails

A running log of every command, query, and concept used while building this project.
Format: what I ran → what it does → why it mattered.

---

## Milestone 0 — Environment Setup

### PostgreSQL

```bash
psql postgres
```
Connects to the running Postgres server using the default admin database. Landing on a
`postgres=#` prompt proves the **server is running**. A database is not a file you open —
it's a background program you connect to. Most setup errors come from forgetting this.

```
psql: error: connection to server on socket "/tmp/.s.PGSQL.5432" failed
```
Means the client exists but **no server is running**. Fix: start Postgres.app (its server
only runs while the app is started).

```bash
which psql
```
Shows which `psql` binary the shell is actually using. Useful when multiple installs exist
(conda ships a client with no server; Postgres.app ships both).

| psql command | Meaning |
|---|---|
| `\l` | **l**ist all databases on the server |
| `\dt` | list **t**ables in the current database |
| `\c dbname` | **c**onnect to a different database |
| `\q` | **q**uit back to the shell |

### Git

```bash
git config --global user.name      # read current value (no value = read, value = set)
git config --global user.email
git config --global --list         # dump every global setting
```
Git stamps each commit with this identity. Matching the email to the GitHub account makes
commits link to the profile.

```bash
git init
```
Creates the hidden `.git` folder — the whole version history lives there, locally.

`.gitignore` contents and why:
```
venv/            # huge, machine-specific, rebuildable from requirements
__pycache__/     # Python's auto-generated cache junk
.env             # SECRETS — API keys. Never commit this.
*.pyc
.DS_Store        # macOS Finder clutter
```

### Python environment

```bash
conda create -n text-to-sql python=3.12 -y
conda activate text-to-sql
```
Creates and enters an **isolated** environment. Isolation matters because projects need
conflicting package versions; one shared Python eventually breaks. Must re-run `activate`
in every new terminal — check the `(text-to-sql)` prefix before running project code.

```bash
pip install faker psycopg2-binary
```
- `faker` — generates realistic fake data (names, emails, dates) for seeding test databases.
- `psycopg2-binary` — the **driver** that lets Python talk to PostgreSQL. `-binary` is
  pre-compiled so it installs without build tools.

---

## Milestone 1 — Database Schema

```sql
CREATE DATABASE ecommerce;
```
One server can hold many isolated databases. Keeping the project separate from the default
`postgres` database is both hygiene and a safety boundary.

```bash
psql ecommerce -f schema.sql
```
`-f` runs an entire **f**ile of SQL, top to bottom.

```bash
psql ecommerce -c "\dt"
```
`-c` runs a single **c**ommand and exits (no interactive prompt). Multiple `-c` flags chain.

### Schema concepts

| Concept | Meaning |
|---|---|
| `SERIAL` | auto-incrementing integer; Postgres assigns 1, 2, 3… automatically |
| `PRIMARY KEY` | uniquely identifies a row; implies NOT NULL + UNIQUE |
| `REFERENCES table(col)` | **foreign key** — value must match a real row in another table |
| `NOT NULL` | column must always have a value |
| `UNIQUE` | no two rows may share this value |
| `DEFAULT 'x'` | value used when none supplied on insert |
| `VARCHAR(n)` | text up to n characters (`TEXT` = unlimited, `CHAR` = fixed/padded) |
| `NUMERIC(10,2)` | **exact** decimal — always use for money, never `FLOAT` |
| `DATE` | calendar date, no time (`TIMESTAMP` includes time) |

**Table creation order matters:** tables without foreign keys first (`categories`,
`customers`), then tables that reference them. A foreign key can only point at a table that
already exists.

**Junction table (`order_items`):** databases can't express many-to-many directly. An order
has many products; a product appears in many orders. Solution: a middle table holding two
foreign keys. One row = "order X contained N units of product Y." Same pattern as
playlist↔song, student↔course.

**Deliberate design choice:** `customers.country` is nullable so ~10% of rows are NULL.
Real data has gaps; overly clean test data hides bugs.

---

## Milestone 2 — Seeding Data

```bash
python seed_data.py
```

```bash
psql ecommerce -c "SELECT COUNT(*) FROM customers;"
```
`COUNT(*)` is an **aggregate function** — collapses many rows into one value. That's why the
result is a single row, even though 200 were examined.

```sql
SELECT COUNT(*), COUNT(country) FROM customers;
```
Returns different numbers (200 vs ~180). **`COUNT(*)` counts rows; `COUNT(col)` skips NULLs.**
Silent, invisible, and exactly the kind of subtle error an LLM makes writing SQL.

### Reset the data

```bash
psql ecommerce -c "TRUNCATE categories, customers, products, orders, order_items RESTART IDENTITY CASCADE;"
```
Empties all tables and resets id counters to 1. Needed because the seeder **adds** rows —
running it twice duplicates data.

### Key Python/DB concepts from `seed_data.py`

**Parameterized queries** — the single most important security habit:
```python
cur.execute("INSERT INTO categories (name) VALUES (%s);", (name,))   # SAFE
cur.execute(f"INSERT INTO categories (name) VALUES ('{name}');")     # SQL INJECTION RISK
```
`%s` sends SQL and values *separately*; the driver escapes them. A value like
`'; DROP TABLE users;--` becomes harmless text instead of executable commands.

**`RETURNING id`** — Postgres generates the SERIAL id, and this hands it back in the same
round trip. Needed to wire up foreign keys correctly.

**Transactions** — every statement ran provisionally until:
```python
conn.commit()
```
Makes all ~1,950 inserts permanent **atomically**: all or nothing. A crash midway would roll
back to empty rather than leaving a half-populated mess. The twin, `rollback()`, becomes a
core guardrail later — it lets us execute suspicious LLM-generated SQL and undo it.

**Reproducibility** — `Faker.seed(42)` / `random.seed(42)` make every run generate identical
data, so verified answers ("revenue = $40,320") stay stable as ground truth.

---

## Git workflow

Standard rhythm at the end of each milestone:
```bash
git add .                      # stage changes ("." = whole folder)
git status                     # ALWAYS check — confirm no .env or venv/ staged
git commit -m "message"        # snapshot, LOCAL only
git push                       # upload to GitHub
```

One-time GitHub connection:
```bash
git remote add origin https://github.com/kreitika/text-to-sql.git
git branch -M main
git push -u origin main        # -u links local main to remote main; future pushes = just `git push`
```

**commit ≠ push.** Commit saves locally (works offline). Push uploads to GitHub. Nothing
appears online until pushed.

Create the GitHub repo **empty** — no README, no .gitignore, no license. Any starter file
creates a commit the laptop doesn't have, causing a merge conflict on first push.

**Commit the recipe, not the meal:** `seed_data.py` is committed; the generated data is not.
Anyone cloning the repo regenerates identical data by running the script.

---

## macOS / shell

```bash
mkdir ~/text-to-sql && cd ~/text-to-sql
pwd                            # print working directory — confirm location before acting
```

```bash
sudo rm /usr/local/bin/code
```
`sudo` runs as administrator. Used here to remove a stale VS Code shortcut blocking
reinstall. **Only run `sudo` when the exact effect is understood** — never paste unknown
`sudo` commands from the internet.

VS Code: `Cmd+Shift+P` → Command Palette. `Ctrl+` ` → built-in terminal (opens already
inside the project folder).

---

## Running question list

Questions worth revisiting as the project develops:

- **Can the model overfit if we know the data perfectly?** No — GPT-4o's weights are frozen;
  we never train it. Knowing ground truth is just *having labels*, which is required to
  evaluate anything. The real risk is **us** overfitting development to one small dataset.
  Mitigations: read the schema at runtime (schema-agnostic), hold back untuned test
  questions, and keep the seed data deliberately messy.


  ---

## SQL Fundamentals (practice — not a milestone)

Getting fluent in the language the LLM will generate, so its output can be judged.

### Basic SELECT

```sql
SELECT name, price FROM products LIMIT 5;
```
`SELECT` picks columns, `FROM` picks the table, `LIMIT` caps output. Always use `LIMIT` when
exploring. Returns rows one-for-one (unlike `COUNT(*)`, which collapses them).

### Filtering and sorting

```sql
SELECT name, price FROM products WHERE price > 1000 ORDER BY price DESC LIMIT 5;
```
`WHERE` filters rows before they return. `ORDER BY ... DESC` sorts high→low (`ASC` is the
default).

### NULL — the silent trap

```sql
SELECT COUNT(*) FROM customers WHERE country != 'India';
SELECT COUNT(*) FROM customers WHERE country IS NULL;
```
These two don't add up to 200. **NULL means "unknown," and comparing anything to unknown
yields unknown — not true.** So `country != 'India'` silently DROPS the NULL rows.

Must write `IS NULL` / `IS NOT NULL` — never `= NULL`. This is the most common source of
quietly-wrong SQL, and a prime LLM failure mode.

### JOIN — following a foreign key

Problem: `products.category_id` is just a number. The human-readable name lives in another
table.

```sql
SELECT p.name, p.price, c.name AS category
FROM products p
JOIN categories c ON p.category_id = c.id
LIMIT 5;
```

Read as: take `products` (aliased `p`), and for each row find the `categories` row (aliased
`c`) where `p.category_id = c.id`.

| Piece | Meaning |
|---|---|
| `p`, `c` | **aliases** — shorthand so `p.name` replaces `products.name` |
| `ON` | the **join condition** — the matching rule |
| `AS category` | renames a column in the output (needed here: both tables have `name`) |

The `ON` clause is almost always `foreign_key = primary_key` — literally the arrows in the
schema diagram.

### GROUP BY — aggregate per bucket

```sql
SELECT c.name AS category, COUNT(*) AS product_count
FROM products p
JOIN categories c ON p.category_id = c.id
GROUP BY c.name
ORDER BY product_count DESC;
```
`GROUP BY` buckets rows; the aggregate then runs *within each bucket*. 5 categories in →
5 rows out.

**The rule that trips everyone up:** every column in `SELECT` must either appear in
`GROUP BY` or be wrapped in an aggregate. A bare `p.name` here is rejected — there are many
product names per bucket and Postgres can't guess which one was meant.

### Multi-table query — revenue by category

Revenue = price × quantity, and those live in different tables, so the full chain is needed:
`categories → products → order_items`.

```sql
SELECT c.name AS category,
       ROUND(SUM(p.price * oi.quantity), 2) AS revenue
FROM order_items oi
JOIN products p   ON oi.product_id = p.id
JOIN categories c ON p.category_id = c.id
GROUP BY c.name
ORDER BY revenue DESC;
```

Each JOIN follows one arrow in the schema diagram.

**Pattern to internalize:** start from the most granular table (here `order_items`, the
junction table) and join outward. The finest-grained table is usually the anchor.

### Why this matters for the project

The output of that revenue query is **ground truth**. Later, the same question gets asked in
English, the LLM generates SQL, and the results get compared.

Failure modes to watch for:
- **Column hallucination** — inventing `products.category` (doesn't exist; it's
  `category_id` → `categories.name`)
- **Join hallucination** — joining `order_items` straight to `categories`, skipping
  `products` entirely
- **NULL mishandling** — using `!=` where `IS NOT NULL` is needed

Knowing the true answer is what makes catching these possible.



---

## Milestone 2 — Schema Extraction

**The problem:** the LLM knows SQL in general but has never seen *this* database. With no
context it invents table and column names — a `users` table, a `created_at` column. Not
stupidity; just uninformed. So the schema description is the single most important input to
the whole system. Good schema text = accurate SQL.

**The technique — introspection:** asking the database to describe itself. Postgres stores
its own structure in the `information_schema` views, which are queried like normal tables.

```bash
python schema_extractor.py
```

### Why extract automatically instead of hardcoding the schema

1. Schemas change — hardcoded text goes stale and silently wrong.
2. **It makes the system schema-agnostic.** Point it at a hospital database and it works.
   This is the concrete answer to the overfitting question: the pipeline isn't specialized
   to e-commerce at all.

### The three system views used

| View | Gives |
|---|---|
| `information_schema.tables` | every table name |
| `information_schema.columns` | column names, data types, nullability |
| `information_schema.table_constraints` + `key_column_usage` + `constraint_column_usage` | foreign keys |

**Critical filter:** `WHERE table_schema = 'public'` restricts results to *our* tables.
Without it, hundreds of Postgres internal tables come back and bloat the prompt.

`ORDER BY ordinal_position` returns columns in declared order rather than alphabetical —
reads far more naturally to a model.

**Foreign keys need a 3-way JOIN** because Postgres splits FK metadata across three views
(the constraint, the local column, the referenced column), stitched back together on
`constraint_name`. Same JOIN pattern as the practice queries, applied to system tables.

**Why FKs matter most:** column lists alone don't tell the model that
`orders.customer_id` points at `customers.id`. Without that, it invents joins —
a **join hallucination**.

### Extracted output (current state)

```
5 tables, 4 relationships:
  products.category_id  -> categories.id
  orders.customer_id    -> customers.id
  order_items.order_id  -> orders.id
  order_items.product_id -> products.id
```

### Gaps in this output — each one is a future hallucination

- **`status` values are invisible.** The model sees `status: character varying` but not that
  the real values are `pending / shipped / delivered / cancelled`. Ask "how many orders were
  completed?" and it writes `WHERE status = 'completed'` → matches zero rows → returns **0**
  with no error. *The most dangerous failure mode in the project: wrong answers that look
  right.* Fix: query `SELECT DISTINCT` on low-cardinality columns and inject the real values.
- **Primary keys aren't marked** — the model infers `id` is the key from its name. Usually
  fine, occasionally not.
- **No semantics, only structure** — nothing states that revenue = `price × quantity`, or
  that `order_items` is a junction table. The model must guess intent from names.

Structurally complete, semantically thin. Enriching this is Milestone 3's job — and a large
share of real Text-to-SQL accuracy comes from exactly that enrichment.

**Cosmetic note:** `character varying` is Postgres's formal name for `VARCHAR`. Worth mapping
to the short form, since that's what appears most in the model's training data.

### Python note

```python
if __name__ == "__main__":
```
Runs only when the file is executed directly, not when imported by another file. Prevents
stray prints once `build_schema_text()` gets imported into the prompt constructor.


---

## Milestone 3 — Prompt Generation

### Storing the API key safely (`.env`)

```
OPENAI_API_KEY=sk-...
```
Secrets NEVER go in code — code gets committed, shared, screenshotted. A key on a public
repo is scraped by bots within minutes and billed to the account. The `.gitignore` line for
`.env` is what protects it. **Always `git status` before committing to confirm `.env` is
invisible.**

Separating config from source is the "twelve-factor app" principle — worth naming in an
interview. Code reads the key from the environment; the value lives in a file that never
leaves the laptop.

```bash
pip install python-dotenv openai
```
- `python-dotenv` — loads `.env` into environment variables.
- `openai` — official API client.

### Schema enrichment (the key idea)

**Structure vs. contents:** `information_schema` gives table/column structure for free
(the DB maintains it as metadata). But the *values inside* a column are not metadata —
the only way to know them is to read the rows with `SELECT DISTINCT`.

`get_distinct_values()` runs on EVERY text column, but only **categorical** (low-cardinality)
columns keep their result. The `≤ 10` rule is a proxy for "is this categorical?":

| Column | Distinct values | Listed? |
|---|---|---|
| `orders.status` | 4 | ✅ yes — categorical |
| `categories.name` | 5 | ✅ yes — categorical |
| `customers.email` | ~200 | ❌ no — free-form, would be noise |

**Why it matters:** without the values, the model sees `status: varchar` and guesses
`WHERE status = 'completed'` → 0 rows → silent wrong answer. With
`status: varchar [values: shipped, cancelled, pending, delivered]` injected into the prompt,
it maps "completed" → "delivered" or returns CANNOT_ANSWER.

**Caveat — string interpolation here, not `%s`:** table/column *names* can't be
parameterized (only values can). Mitigation: names come from `information_schema`, not user
input, plus double-quoting. Also doesn't scale — `SELECT DISTINCT` on a 50M-row column is
expensive; production would sample or cache.

### The prompt (`prompt_builder.py`)

System prompt rules and why each exists:

| Rule | Purpose |
|---|---|
| "Output ONLY SQL, no markdown" | output is executed directly; prose breaks it |
| "Use ONLY listed tables/columns" | reduces schema hallucination (not sufficient alone) |
| "Never INSERT/UPDATE/DELETE/DROP" | **weakest** safety layer — a polite request, ignorable |
| "Always LIMIT 100" | stops runaway result sets |
| "Output CANNOT_ANSWER if impossible" | escape hatch — without one, the model invents tables |

**Prompt-level safety is the weakest layer.** Real defense comes in M5: read-only DB user +
SQL parsing. Principle: **defense in depth** — multiple independent layers, no single failure
is fatal.

---

## Milestone 4 — SQL Generation via API

```bash
python generate_sql.py
```

### API concepts

| Concept | Meaning |
|---|---|
| `messages` roles | `system` = standing orders (schema + rules), `user` = the question. Models weight system as higher authority — which is why safety rules go there, and also why prompt injection via the user message is a threat. |
| `model="gpt-4o-mini"` | cheap/fast; develop here, only use full `gpt-4o` to test top quality |
| `temperature=0` | deterministic output — same question → same SQL. Correct for structured output; opposite of creative writing. |
| `response.choices[0].message.content` | API returns candidates; `[0]` = first, `.message.content` = the text |

### Results — proof the pipeline works

- Q "How many customers?" → `SELECT COUNT(*) FROM customers;` ✅
- Q "Which category earned most revenue?" → correct 4-table join, arrived at same answer as
  the hand-written query (started from a different table — both valid) ✅
- Q "How many orders were **completed**?" → `WHERE status = 'delivered'` ✅
  **This is the enrichment proving itself.** No "completed" value exists; the model mapped it
  to the real value because the injected value list told it what exists. Without enrichment
  this would have silently returned 0.

### What's still fragile (→ motivates M5/M6)

- Output was clean bare SQL **this time** — models don't always comply (markdown fences,
  preambles). We feed this string straight to the DB, so any stray character breaks it.
- **Nothing is checked before execution.** No validation that referenced columns exist, no
  block on destructive statements, no read-only enforcement. We got lucky the output was safe.

Next: M5 strips formatting, parses SQL to confirm read-only SELECT, and connects via a DB
user that *physically cannot* write.



