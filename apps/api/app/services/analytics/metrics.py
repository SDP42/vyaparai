"""The metric registry: the single source of truth for what every number means.

Dashboards, the API and (later) the Copilot all read definitions from here. Changing a formula
means bumping its ``version`` and recording it in docs/METRICS.md.
"""

from dataclasses import dataclass
from typing import Literal

Unit = Literal["inr", "count", "percent"]
Direction = Literal["up_good", "down_good", "neutral"]

REGISTRY_VERSION = 2  # 2: added customer-intelligence metrics (each metric keeps its own version)


@dataclass(frozen=True, slots=True)
class MetricDef:
    key: str
    label: str
    unit: Unit
    version: int
    definition: str
    includes: str
    excludes: str
    good_direction: Direction = "up_good"
    # Percent metrics are compared in percentage points, not relative %.
    compare_in_points: bool = False


ELIGIBLE = "orders with status 'completed'"

METRICS: tuple[MetricDef, ...] = (
    MetricDef(
        "net_sales",
        "Net sales",
        "inr",
        1,
        "Gross sales minus line discounts",
        f"Lines of {ELIGIBLE}",
        "GST, shipping, cancelled, pending and returned orders",
    ),
    MetricDef(
        "gross_sales",
        "Gross sales",
        "inr",
        1,
        "Sum of quantity × unit price",
        f"Lines of {ELIGIBLE}",
        "GST, shipping, discounts not yet deducted",
    ),
    MetricDef(
        "discounts",
        "Discounts",
        "inr",
        1,
        "Sum of line discount amounts",
        f"Lines of {ELIGIBLE}",
        "",
        good_direction="neutral",
    ),
    MetricDef(
        "orders",
        "Orders",
        "count",
        1,
        "Distinct completed orders",
        ELIGIBLE,
        "Cancelled, pending and returned orders",
    ),
    MetricDef(
        "units",
        "Units sold",
        "count",
        1,
        "Sum of quantity",
        f"Lines of {ELIGIBLE}",
        "",
    ),
    MetricDef(
        "aov",
        "Average order value",
        "inr",
        1,
        "Net sales ÷ orders",
        f"Net sales of {ELIGIBLE}",
        "",
    ),
    MetricDef(
        "units_per_order",
        "Units per order",
        "count",
        1,
        "Units sold ÷ orders (basket depth)",
        ELIGIBLE,
        "",
    ),
    MetricDef(
        "discount_rate",
        "Discount rate",
        "percent",
        1,
        "Discounts ÷ gross sales",
        f"Lines of {ELIGIBLE}",
        "",
        good_direction="down_good",
        compare_in_points=True,
    ),
    MetricDef(
        "cogs",
        "Cost of goods sold",
        "inr",
        1,
        "Sum of quantity × unit cost snapshot",
        "Eligible lines that have a cost",
        "Lines without a cost (see cost coverage)",
        good_direction="neutral",
    ),
    MetricDef(
        "gross_profit",
        "Gross profit",
        "inr",
        1,
        "Net sales of lines with a cost minus cost of goods sold",
        "Eligible lines that have a cost",
        "Lines without a cost, so profit is understated when coverage is below 100 %",
    ),
    MetricDef(
        "gross_margin",
        "Gross margin",
        "percent",
        1,
        "Gross profit ÷ net sales of lines with a cost",
        "Eligible lines that have a cost",
        "Lines without a cost",
        compare_in_points=True,
    ),
    MetricDef(
        "cost_coverage",
        "Cost coverage",
        "percent",
        1,
        "Share of net sales that sits on lines with a cost",
        f"Net sales of {ELIGIBLE}",
        "",
        compare_in_points=True,
    ),
    MetricDef(
        "active_customers",
        "Active customers",
        "count",
        1,
        "Distinct customers with at least one completed order in the period",
        "Orders that have a customer",
        "Walk-in orders without a customer",
    ),
    MetricDef(
        "new_customers",
        "New customers",
        "count",
        1,
        "Active customers whose first-ever completed order falls in the period",
        "Orders that have a customer",
        "Walk-in orders",
    ),
    MetricDef(
        "repeat_customers",
        "Repeat customers",
        "count",
        1,
        "Active customers with two or more completed orders ever",
        "Orders that have a customer",
        "Walk-in orders",
    ),
    MetricDef(
        "anonymous_order_share",
        "Walk-in orders",
        "percent",
        1,
        "Completed orders with no customer ÷ completed orders",
        ELIGIBLE,
        "",
        good_direction="neutral",
        compare_in_points=True,
    ),
    MetricDef(
        "repeat_rate",
        "Repeat rate",
        "percent",
        1,
        "Customers with two or more completed orders in the lookback window ÷ customers",
        "Identified customers with a completed order in the window",
        "Walk-in orders",
        compare_in_points=True,
    ),
    MetricDef(
        "revenue_per_customer",
        "Revenue per customer",
        "inr",
        1,
        "Net sales in the lookback window ÷ identified customers",
        "Identified customers with a completed order in the window",
        "Walk-in orders",
    ),
    MetricDef(
        "top_decile_share",
        "Top 10% customer share",
        "percent",
        1,
        "Share of net sales from the top 10 % of customers (at least one customer)",
        "Identified customers with a completed order in the window",
        "Walk-in orders",
        good_direction="neutral",
        compare_in_points=True,
    ),
    MetricDef(
        "lapsed_regulars",
        "Lapsed regulars",
        "count",
        1,
        "Customers with two or more orders and no order for at least 45 days",
        "Identified customers",
        "Walk-in orders",
        good_direction="down_good",
    ),
)

BY_KEY: dict[str, MetricDef] = {m.key: m for m in METRICS}

# The KPI cards shown first in the command center, in order.
HEADLINE_KEYS = ("net_sales", "gross_profit", "orders", "aov")
SECONDARY_KEYS = ("units", "units_per_order", "discount_rate", "gross_margin", "active_customers")


def versions(keys: list[str] | tuple[str, ...]) -> dict[str, int]:
    return {k: BY_KEY[k].version for k in keys}
