-- Product categories, e.g. "Electronics", "Books"
CREATE TABLE categories (
    id    SERIAL PRIMARY KEY,
    name  VARCHAR(100) NOT NULL
);

-- People who place orders
CREATE TABLE customers (
    id           SERIAL PRIMARY KEY,
    name         VARCHAR(100) NOT NULL,
    email        VARCHAR(255) UNIQUE NOT NULL,
    signup_date  DATE NOT NULL,
    country      VARCHAR(100)
);

-- Items for sale, each belonging to one category
CREATE TABLE products (
    id           SERIAL PRIMARY KEY,
    name         VARCHAR(200) NOT NULL,
    price        NUMERIC(10, 2) NOT NULL,
    category_id  INTEGER NOT NULL REFERENCES categories(id)
);

-- A purchase event by one customer
CREATE TABLE orders (
    id           SERIAL PRIMARY KEY,
    customer_id  INTEGER NOT NULL REFERENCES customers(id),
    order_date   DATE NOT NULL,
    status       VARCHAR(20) NOT NULL DEFAULT 'pending'
);

-- Links orders to products (many-to-many).
-- One row = "this order contained N units of this product."
CREATE TABLE order_items (
    id          SERIAL PRIMARY KEY,
    order_id    INTEGER NOT NULL REFERENCES orders(id),
    product_id  INTEGER NOT NULL REFERENCES products(id),
    quantity    INTEGER NOT NULL DEFAULT 1
);