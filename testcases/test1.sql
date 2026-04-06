CREATE TABLE products (
    price NUMERIC,
    discounted_price NUMERIC,
    status TEXT,
    discount NUMERIC,

    CONSTRAINT chk_price
    CHECK (
        (price > 100 AND discounted_price > 0)
        OR (price <= 100)
    ),

    CONSTRAINT chk_products
    CHECK (
        price BETWEEN 10 AND 100
        AND status IN ('ACTIVE', 'PENDING')
        AND discounted_price IS NOT NULL
    ),

    CONSTRAINT chk_price_minus_discount
    CHECK (
        price - discount >= 0
    )
);

CREATE TABLE users (
    email TEXT,
    CONSTRAINT chk_email_like
    CHECK (
        email LIKE '%@gmail.com'
    )
);

CREATE TABLE flags (
    dummy BOOLEAN,
    CONSTRAINT chk_true_literal
    CHECK (TRUE)
);

CREATE TABLE accounts (
    is_active BOOLEAN,

    CONSTRAINT chk_is_active_true
    CHECK (
        is_active = TRUE
    ),

    CONSTRAINT chk_is_active_is_true
    CHECK (
        is_active IS TRUE
    )
);

CREATE TABLE payments (
    amount NUMERIC,
    CONSTRAINT chk_amount_cast_numeric
    CHECK (
        amount::numeric > 0
    )
);

CREATE TABLE items (
    code NUMERIC,
    CONSTRAINT chk_code_cast_text
    CHECK (
        CAST(code AS TEXT) <> ''
    )
);