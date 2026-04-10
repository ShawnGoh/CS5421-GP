CREATE TABLE products (
    price NUMERIC,
    discounted_price NUMERIC,
    status TEXT,
    discount NUMERIC,
    test_val NUMERIC,

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
    ),

    CONSTRAINT chk_discount_is_null
    CHECK (
        discount IS NULL
    )
);

CREATE TABLE users (
    email TEXT,
    username TEXT,
    name TEXT,
    status TEXT,

    CONSTRAINT chk_email_like
    CHECK (
        email LIKE '%@gmail.com'
    ),

    CONSTRAINT chk_username_pattern_single_char
    CHECK (
        username LIKE 'a_c'
    )
);

CREATE TABLE flags (
    dummy BOOLEAN,
    CONSTRAINT chk_true_literal
    CHECK (TRUE),

    CONSTRAINT chk_false_literal
    CHECK (FALSE)
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
    amount TEXT,
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

CREATE TABLE employees (
    id INT,
    position TEXT,
    salary NUMERIC,

    CONSTRAINT fd_position_salary
    CHECK (
        NOT EXISTS (
            SELECT *
            FROM employees e1, employees e2
            WHERE e1.position = e2.position
              AND e1.salary <> e2.salary
        )
    )
);