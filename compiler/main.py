from contracts import (
    AndExpr,
    BetweenExpr,
    BoolExpr,
    ColumnExpr,
    CompareExpr,
    Expr,
    FunctionExpr,
    InExpr,
    IsNullExpr,
    LiteralExpr,
    LiteralType,
    NotExpr,
    OrExpr,
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