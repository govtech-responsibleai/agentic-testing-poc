"""Database helpers used by the CLI agent."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, Mapping

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection, Engine

DB_PATH = Path(__file__).parent / "business.sqlite"
ENGINE: Engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)


def get_connection() -> Connection:
    """Return a connection to the SQLite business database."""

    return ENGINE.connect()


def _rows_to_dicts(rows: Iterable[Any]) -> list[dict[str, Any]]:
    """Convert SQLAlchemy row objects to plain dictionaries."""

    return [dict(row._mapping) for row in rows]


def list_products(limit: int = 10) -> list[dict[str, Any]]:
    """Return a collection of products limited to the specified count."""

    with get_connection() as conn:
        result = conn.execute(
            text("SELECT * FROM products LIMIT :limit"), {"limit": limit}
        )
        return _rows_to_dicts(result)


def list_customers(limit: int = 10) -> list[dict[str, Any]]:
    """Return a collection of customers limited to the specified count."""

    with get_connection() as conn:
        result = conn.execute(
            text("SELECT * FROM customers LIMIT :limit"), {"limit": limit}
        )
        return _rows_to_dicts(result)


def list_orders(limit: int = 10) -> list[dict[str, Any]]:
    """Return recent orders with summary statistics."""

    with get_connection() as conn:
        result = conn.execute(
            text(
                """
                SELECT o.order_id,
                       c.name as customer_name,
                       o.order_date,
                       o.status,
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
        return _rows_to_dicts(result)


def get_order_details(order_id: int) -> list[dict[str, Any]]:
    """Return order line items for the provided order identifier."""

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
        return _rows_to_dicts(result)


def get_sales_summary() -> dict[str, Any]:
    """Return aggregate sales metrics across all non-cancelled orders."""

    with get_connection() as conn:
        result = conn.execute(
            text(
                """
                SELECT COUNT(DISTINCT o.order_id) as total_orders,
                       COUNT(DISTINCT o.customer_id) as unique_customers,
                       ROUND(SUM(od.total), 2) as total_revenue,
                       ROUND(AVG(od.total), 2) as avg_order_value
                FROM orders o
                JOIN order_details od ON o.order_id = od.order_id
                WHERE o.status != 'Cancelled'
                """
            )
        )
        row = result.first()
        return dict(row._mapping) if row else {}


def execute_query(
    query: str, params: Mapping[str, Any] | None = None
) -> list[dict[str, Any]]:
    """Execute an arbitrary SQL query used by the agent tools."""

    with get_connection() as conn:
        result = conn.execute(text(query), params or {})
        return _rows_to_dicts(result)
