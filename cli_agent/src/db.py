from sqlalchemy import create_engine, text
import pathlib

DB_PATH = pathlib.Path(__file__).parent / "business.sqlite"
ENGINE = create_engine(f"sqlite:///{DB_PATH}", echo=False)


def get_connection():
    return ENGINE.connect()


def list_products(limit=10):
    with get_connection() as conn:
        result = conn.execute(
            text("SELECT * FROM products LIMIT :limit"), {"limit": limit}
        )
        return [dict(row._mapping) for row in result]


def list_customers(limit=10):
    with get_connection() as conn:
        result = conn.execute(
            text("SELECT * FROM customers LIMIT :limit"), {"limit": limit}
        )
        return [dict(row._mapping) for row in result]


def list_orders(limit=10):
    with get_connection() as conn:
        result = conn.execute(
            text(
                """
            SELECT o.order_id, c.name as customer_name, o.order_date, o.status,
                   COUNT(od.sku) as item_count,
                   ROUND(SUM(od.total), 2) as order_total
            FROM orders o
            JOIN customers c ON o.customer_id = c.customer_id
            LEFT JOIN order_details od ON o.order_id = od.order_id
            GROUP BY o.order_id, c.name, o.order_date, o.status
            ORDER BY o.order_date DESC
            LIMIT :limit
        """
            ),
            {"limit": limit},
        )
        return [dict(row._mapping) for row in result]


def get_order_details(order_id):
    with get_connection() as conn:
        result = conn.execute(
            text(
                """
            SELECT od.*, p.name as product_name
            FROM order_details od
            JOIN products p ON od.sku = p.sku
            WHERE od.order_id = :order_id
        """
            ),
            {"order_id": order_id},
        )
        return [dict(row._mapping) for row in result]


def get_sales_summary():
    with get_connection() as conn:
        result = conn.execute(
            text(
                """
            SELECT 
                COUNT(DISTINCT o.order_id) as total_orders,
                COUNT(DISTINCT o.customer_id) as unique_customers,
                ROUND(SUM(od.total), 2) as total_revenue,
                ROUND(AVG(od.total), 2) as avg_order_value
            FROM orders o
            JOIN order_details od ON o.order_id = od.order_id
            WHERE o.status != 'Cancelled'
        """
            )
        )
        return dict(result.first()._mapping)


def execute_query(query, params=None):
    """Execute a custom SQL query - useful for agent interactions"""
    with get_connection() as conn:
        result = conn.execute(text(query), params or {})
        return [dict(row._mapping) for row in result]
