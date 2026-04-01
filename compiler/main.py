from contracts import (
    AndExpr,
    BetweenExpr,
    BinaryValueExpr,
    BoolExpr,
    BoolLiteralExpr,
    CastExpr,
    ColumnExpr,
    CompareExpr,
    Expr,
    LikeExpr,
    FunctionExpr,
    InExpr,
    IsBoolExpr,
    IsNullExpr,
    LiteralExpr,
    LiteralType,
    NotExpr,
    OrExpr,
    UnaryValueExpr,
    TransformedCheckConstraint,
    OutputCheck,
)
from codegen import CheckCodeGenerator

def main():
    constraints = []
    constraints.append(
        TransformedCheckConstraint(
            table_name="products",
            constraint_name="chk_price",
            condition=OrExpr(
                left=AndExpr(
                    left=CompareExpr(
                        left=ColumnExpr("price", "NEW.price"),
                        operator=">",
                        right=LiteralExpr(100, LiteralType.NUMBER),
                    ),
                    right=CompareExpr(
                        left=ColumnExpr("discounted_price", "NEW.discounted_price"),
                        operator=">",
                        right=LiteralExpr(0, LiteralType.NUMBER),
                    ),
                ),
                right=CompareExpr(
                    left=ColumnExpr("price", "NEW.price"),
                    operator="<=",
                    right=LiteralExpr(100, LiteralType.NUMBER),
                ),
            ),
            referenced_columns=[("price", "NUMERIC"), ("discounted_price", "NUMERIC")],
            original_check_sql="CHECK ((price > 100 AND discounted_price > 0) OR (price <= 100))",
        )
    )
    constraints.append(
        TransformedCheckConstraint(
            table_name="products",
            constraint_name="chk_products",
            condition=AndExpr(
                left=AndExpr(
                    left=BetweenExpr(
                        value=ColumnExpr("price", "NEW.price"),
                        lower=LiteralExpr(10, LiteralType.NUMBER),
                        upper=LiteralExpr(100, LiteralType.NUMBER),
                    ),
                    right=InExpr(
                        value=ColumnExpr("status", "NEW.status"),
                        options=[
                            LiteralExpr("ACTIVE", LiteralType.STRING),
                            LiteralExpr("PENDING", LiteralType.STRING),
                        ],
                    ),
                ),
                right=IsNullExpr(
                    expr=ColumnExpr("discounted_price", "NEW.discounted_price"),
                    negated=True,
                ),
            ),
            referenced_columns=[("price", "NUMERIC"), ("status", "TEXT"), ("discounted_price", "NUMERIC")],
            original_check_sql="CHECK (price BETWEEN 10 AND 100 AND status IN ('ACTIVE', 'PENDING') AND discounted_price IS NOT NULL)",
        )
    )

    constraints.append(
        TransformedCheckConstraint(
            table_name="products",
            constraint_name="chk_price_minus_discount",
            condition=CompareExpr(
                left=BinaryValueExpr(
                    left=ColumnExpr("price", "NEW.price"),
                    operator="-",
                    right=ColumnExpr("discount", "NEW.discount"),
                ),
                operator=">=",
                right=LiteralExpr(0, LiteralType.NUMBER),
            ),
            referenced_columns=[("price", "NUMERIC"), ("discount", "NUMERIC")],
            original_check_sql="CHECK (price - discount >= 0)",
        )
    )

    constraints.append(
        TransformedCheckConstraint(
            table_name="users",
            constraint_name="chk_email_like",
            condition=LikeExpr(
                value=ColumnExpr("email", "NEW.email"),
                pattern=LiteralExpr("%@gmail.com", LiteralType.STRING),
                negated=False,
                case_insensitive=False,
            ),
            referenced_columns=[("email", "TEXT")],
            original_check_sql="CHECK (email LIKE '%@gmail.com')",
        )
    )

    constraints.append(
        TransformedCheckConstraint(
            table_name="flags",
            constraint_name="chk_true_literal",
            condition=BoolLiteralExpr(True),
            referenced_columns=[],
            original_check_sql="CHECK (TRUE)",
        )
    )

    constraints.append(
        TransformedCheckConstraint(
            table_name="accounts",
            constraint_name="chk_is_active_true",
            condition=CompareExpr(
                left=ColumnExpr("is_active", "NEW.is_active"),
                operator="=",
                right=LiteralExpr(True, LiteralType.BOOLEAN),
            ),
            referenced_columns=[("is_active", "BOOLEAN")],
            original_check_sql="CHECK (is_active = TRUE)",
        )
    )

    constraints.append(
        TransformedCheckConstraint(
            table_name="accounts",
            constraint_name="chk_is_active_is_true",
            condition=IsBoolExpr(
                expr=CompareExpr(
                    left=ColumnExpr("is_active", "NEW.is_active"),
                    operator="=",
                    right=LiteralExpr(True, LiteralType.BOOLEAN),
                ),
                check_for="TRUE",
                negated=False,
            ),
            referenced_columns=[("is_active", "BOOLEAN")],
            original_check_sql="CHECK (is_active IS TRUE)",
        )
    )

    constraints.append(
        TransformedCheckConstraint(
            table_name="payments",
            constraint_name="chk_amount_cast_numeric",
            condition=CompareExpr(
                left=CastExpr(
                    expr=ColumnExpr("amount", "NEW.amount"),
                    target_type="NUMERIC",
                    use_pg_style=True,
                ),
                operator=">",
                right=LiteralExpr(0, LiteralType.NUMBER),
            ),
            referenced_columns=[("amount", "NUMERIC")],
            original_check_sql="CHECK (amount::numeric > 0)",
        )
    )

    constraints.append(
        TransformedCheckConstraint(
            table_name="items",
            constraint_name="chk_code_cast_text",
            condition=CompareExpr(
                left=CastExpr(
                    expr=ColumnExpr("code", "NEW.code"),
                    target_type="TEXT",
                    use_pg_style=False,
                ),
                operator="<>",
                right=LiteralExpr("", LiteralType.STRING),
            ),
            referenced_columns=[("code", "NUMERIC")],
            original_check_sql="CHECK (CAST(code AS TEXT) <> '')",
        )
    )

    generator = CheckCodeGenerator()
    for constraint in constraints:
        print(f"\n===== {constraint.constraint_name} =====")

        artifacts = generator.generate(constraint)

        print("=== FUNCTION SQL ===")
        print(artifacts.function_sql)
        print("\n=== TRIGGER SQL ===")
        print(artifacts.trigger_sql)
        print("\n=== COMBINED SQL ===")
        print(artifacts.combined_sql)

if __name__ == "__main__":
    main()