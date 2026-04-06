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

CREATE TABLE users (
    email text,
    CHECK (email LIKE '%;@gmail.com')
);


CREATE TABLE products (
    price numeric,
    CHECK (price > 0)
);
ALTER TABLE products ADD CONSTRAINT chk2 CHECK (price < 100);