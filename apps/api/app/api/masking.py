"""Hide cost and margin from personas that may not see them.

A persona without the `margin` capability (operations manager, counter staff) still gets the
sales, stock and forecast pages, but every cost, margin and profit figure in those JSON
responses comes back empty. It is done once, here, on the way out, so a new field named
*margin* or *cost* is hidden without anyone remembering to. Pages already show a dash for a
missing figure.
"""

import json
import re
from collections.abc import Callable
from typing import Any

from fastapi import Request, Response
from fastapi.routing import APIRoute

_KEY = re.compile(r"margin|cost|profit|cogs|markup", re.IGNORECASE)
_METRIC_KEYS = {"gross_margin", "gross_profit", "cogs", "margin_pct", "cost_coverage"}


_METRIC_FIELDS = {"value", "previous", "change", "change_pct", "series"}


def scrub(node: Any) -> Any:
    """The same structure with every cost, margin and profit value set to None."""
    if isinstance(node, list):
        return [scrub(x) for x in node]
    if not isinstance(node, dict):
        return node
    metric_card = node.get("key") in _METRIC_KEYS  # {"key": "gross_margin", "value": ...}
    out: dict[str, Any] = {}
    for k, v in node.items():
        nested = isinstance(v, (dict, list))
        hide = (_KEY.search(k) and not nested) or (metric_card and k in _METRIC_FIELDS)
        out[k] = None if hide else scrub(v)
    return out


class MaskedRoute(APIRoute):
    def get_route_handler(self) -> Callable[[Request], Any]:
        original = super().get_route_handler()

        async def handler(request: Request) -> Response:
            response: Response = await original(request)
            persona = getattr(request.state, "persona", None)
            if (
                persona is None
                or persona.can("margin")
                or "application/json" not in response.headers.get("content-type", "")
            ):
                return response
            body = scrub(json.loads(bytes(response.body)))
            headers = {k: v for k, v in response.headers.items() if k.lower() != "content-length"}
            return Response(
                json.dumps(body, separators=(",", ":")).encode(),
                status_code=response.status_code,
                headers=headers,
                media_type="application/json",
            )

        return handler
