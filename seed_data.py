# ============================================================
# seed_data.py — fills the empty ecommerce tables with fake data
# ============================================================

import random                  # Python's built-in random number generator
import psycopg2                # the driver that lets Python talk to PostgreSQL
from faker import Faker        # generates realistic fake names, emails, dates

fake = Faker()                 # create the fake-data generator we'll call throughout
Faker.seed(42)                 # fix Faker's randomness so every run produces identical data
random.seed(42)                # same for Python's random — makes our ground truth stable

# Open a live connection to the running Postgres server, targeting our database.
# No user/password needed: Postgres.app trusts local connections from your Mac account.
conn = psycopg2.connect(dbname="ecommerce")

# A cursor is the channel we send queries through and read results back from.
# Connection = the phone line. Cursor = the conversation happening on it.
cur = conn.cursor()


# ------------------------------------------------------------
# CATEGORIES — inserted first because nothing depends on them
# ------------------------------------------------------------

CATEGORIES = ["Electronics", "Books", "Clothing", "Home & Kitchen", "Sports"]

category_ids = []              # we must remember the generated IDs to use as foreign keys
for name in CATEGORIES:
    # %s is a PARAMETERIZED placeholder — psycopg2 safely escapes the value.
    # Never build SQL with f-strings; that's how SQL injection happens.
    # RETURNING id asks Postgres to hand back the auto-generated SERIAL id.
    cur.execute("INSERT INTO categories (name) VALUES (%s) RETURNING id;", (name,))
    category_ids.append(cur.fetchone()[0])   # fetchone() → a row tuple; [0] → the id itself


# ------------------------------------------------------------
# PRODUCTS — depend on categories, so they come second
# ------------------------------------------------------------

product_ids = []
for _ in range(50):            # "_" means we don't care about the loop counter
    cur.execute(
        "INSERT INTO products (name, price, category_id) VALUES (%s, %s, %s) RETURNING id;",
        (
            fake.catch_phrase(),                    # corporate-sounding fake product name
            round(random.uniform(5, 2000), 2),      # price between 5 and 2000, 2 decimals
            random.choice(category_ids),            # FK: always a category that really exists
        ),
    )
    product_ids.append(cur.fetchone()[0])


# ------------------------------------------------------------
# CUSTOMERS — independent table, but needed before orders
# ------------------------------------------------------------

customer_ids = []
for _ in range(200):
    # Deliberately leave ~10% of countries NULL so our data has realistic gaps.
    # This is why we left `country` nullable in the schema.
    country = None if random.random() < 0.1 else fake.country()

    cur.execute(
        "INSERT INTO customers (name, email, signup_date, country) VALUES (%s, %s, %s, %s) RETURNING id;",
        (
            fake.name(),
            fake.unique.email(),                              # .unique respects the UNIQUE constraint
            fake.date_between(start_date="-2y", end_date="today"),  # signup within last 2 years
            country,                                          # None becomes SQL NULL
        ),
    )
    customer_ids.append(cur.fetchone()[0])


# ------------------------------------------------------------
# ORDERS + ORDER_ITEMS — the many-to-many relationship
# ------------------------------------------------------------

STATUSES = ["pending", "shipped", "delivered", "cancelled"]

for _ in range(500):
    cur.execute(
        "INSERT INTO orders (customer_id, order_date, status) VALUES (%s, %s, %s) RETURNING id;",
        (
            random.choice(customer_ids),                            # FK to a real customer
            fake.date_between(start_date="-1y", end_date="today"),  # order within last year
            random.choice(STATUSES),
        ),
    )
    order_id = cur.fetchone()[0]   # we need this order's id for its line items below

    # Each order contains 1–4 DISTINCT products. random.sample picks without repeats,
    # so the same product can't appear twice in one order.
    for product_id in random.sample(product_ids, random.randint(1, 4)):
        cur.execute(
            "INSERT INTO order_items (order_id, product_id, quantity) VALUES (%s, %s, %s);",
            (order_id, product_id, random.randint(1, 3)),   # two FKs + a quantity
        )


# ------------------------------------------------------------
# FINALIZE
# ------------------------------------------------------------

# Everything above ran inside a TRANSACTION — provisional, invisible, not yet saved.
# commit() makes all ~1,950 inserts permanent atomically: all or nothing.
# Had the script crashed midway, the database would roll back to empty — no half-mess.
conn.commit()

cur.close()                    # close the conversation
conn.close()                   # hang up the phone line

print("Seed complete.")