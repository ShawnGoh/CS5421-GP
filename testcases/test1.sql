CREATE TABLE products (
    price NUMERIC,
    discounted_price NUMERIC,
    CONSTRAINT chk_price CHECK (
        (price > 100 AND discounted_price > 0) OR (price <= 100)
    )
);


ALTER TABLE products
ADD CONSTRAINT chk_price CHECK (
    (price > 100 AND discounted_price > 0) OR (price <= 100)
);

CREATE TABLE test (
    payload jsonb,
    CHECK (payload->>'name' <> '')
);

CREATE TABLE users (
    email text,
    CHECK (email LIKE '%;@gmail.com')
);

ALTER TABLE products
ADD CONSTRAINT chk_exists
CHECK (EXISTS (SELECT 1 FROM other_table WHERE other_table.id = products.id));

CREATE TABLE products (
    price numeric,
    CHECK (price > 0)
);
ALTER TABLE products ADD CONSTRAINT chk2 CHECK (price < 100);