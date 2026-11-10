"""Render a saved report as PDF (reportlab, BSD) or CSV.

The built-in PDF fonts have no rupee sign or Devanagari, so amounts are written "Rs 1,23,456" and
reports are in English.
"""

import csv
import io
from typing import Any

from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.shapes import Drawing
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

INK, MUTED, LINE, ACCENT = (
    colors.HexColor("#2a2118"),
    colors.HexColor("#7a6a58"),
    colors.HexColor("#e4d8c4"),
    colors.HexColor("#c8452d"),
)


def rs(x: Any) -> str:
    if x is None:
        return "-"
    v = round(float(x))
    s, sign = str(abs(v)), "-" if v < 0 else ""
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        parts: list[str] = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        s = ",".join(parts) + "," + tail
    return f"{sign}Rs {s}"


def _val(k: dict[str, Any]) -> str:
    v = k["value"]
    if v is None:
        return "-"
    return (
        rs(v)
        if k["unit"] == "inr"
        else f"{float(v):.1f}%"
        if k["unit"] == "percent"
        else f"{float(v):,.0f}"
        if float(v) == int(float(v))
        else f"{float(v):,.2f}"
    )


def _chg(k: dict[str, Any]) -> str:
    return "-" if k["change_pct"] is None else f"{float(k['change_pct']):+.1f}%"


def _table(rows: list[list[str]], widths: list[float], head: bool = True) -> Table:
    t = Table(rows, colWidths=widths, repeatRows=1 if head else 0)
    st = [("FONT", (0, 0), (-1, -1), "Helvetica", 8.5), ("TEXTCOLOR", (0, 0), (-1, -1), INK), ("LINEBELOW", (0, 0), (-1, -1), 0.25, LINE),
          ("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]  # fmt: skip
    if head:
        st += [
            ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 8),
            ("TEXTCOLOR", (0, 0), (-1, 0), MUTED),
        ]
    for c in range(1, len(widths)):
        st.append(("ALIGN", (c, 0), (c, -1), "RIGHT"))
    t.setStyle(TableStyle(st))
    return t


def to_pdf(rep: dict[str, Any]) -> bytes:
    buf = io.BytesIO()
    ss = getSampleStyleSheet()
    h1 = ParagraphStyle(
        "h1",
        parent=ss["Title"],
        fontName="Helvetica-Bold",
        fontSize=20,
        textColor=INK,
        alignment=0,
        spaceAfter=2,
    )
    h2 = ParagraphStyle(
        "h2",
        parent=ss["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=11.5,
        textColor=INK,
        spaceBefore=12,
        spaceAfter=4,
    )
    body = ParagraphStyle(
        "b", parent=ss["BodyText"], fontName="Helvetica", fontSize=9, leading=12.5, textColor=INK
    )
    small = ParagraphStyle("s", parent=body, fontSize=7.5, textColor=MUTED, leading=10)
    p = rep["period"]

    def foot(c: Any, d: Any) -> None:
        c.saveState()
        c.setFont("Helvetica", 7.5)
        c.setFillColor(MUTED)
        c.drawString(
            18 * mm,
            10 * mm,
            f"{rep['shop']} - business summary - data through {rep['data_through']}",
        )
        c.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Page {d.page}")
        c.restoreState()

    el: list[Any] = [Paragraph(rep["shop"], h1), Paragraph(f"Business summary, {p['from']} to {p['to']}", body),
                     Paragraph(f"Generated {rep['generated_at'][:16].replace('T', ' ')} UTC. Compared with the period of the same length before.", small), Spacer(1, 6)]  # fmt: skip
    k = {x["key"]: x for x in rep["kpis"]}
    cells = [
        [
            Paragraph(
                f"<font size=7 color='#7a6a58'>{k[key]['label'].upper()}</font><br/><font size=13><b>{_val(k[key])}</b></font><br/><font size=8 color='#7a6a58'>{_chg(k[key])}</font>",
                body,
            )
            for key in ("net_sales", "gross_profit", "orders", "aov")
        ]
    ]
    t = Table(cells, colWidths=[43 * mm] * 4)
    t.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.5, LINE),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, LINE),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    el += [t, Paragraph("What changed", h2)]
    el.append(
        Paragraph(
            f"Net sales changed by {rs(rep['drivers']['net_change'])}. "
            + "; ".join(
                f"{e['label']} {rs(e['amount'])}"
                for e in rep["drivers"]["effects"]
                if float(e["amount"]) != 0
            )
            + ".",
            body,
        )
    )
    dec, gai = rep["drivers"]["decliners"][:3], rep["drivers"]["gainers"][:3]
    if dec:
        el.append(
            Paragraph(
                "Fell most: " + ", ".join(f"{d['name']} ({rs(d['delta'])})" for d in dec) + ".",
                body,
            )
        )
    if gai:
        el.append(
            Paragraph(
                "Rose most: " + ", ".join(f"{d['name']} ({rs(d['delta'])})" for d in gai) + ".",
                body,
            )
        )

    chart = rep.get("trend")
    if chart:
        d = Drawing(170 * mm, 45 * mm)
        bc = VerticalBarChart()
        bc.x, bc.y, bc.width, bc.height = 10, 8, 160 * mm, 38 * mm
        bc.data = [[float(v) for v in chart]]
        bc.bars[0].fillColor = ACCENT
        bc.valueAxis.valueMin = 0
        bc.categoryAxis.visible = False
        d.add(bc)
        el += [Paragraph("Net sales over the period", h2), d]

    el.append(Paragraph("All measures", h2))
    el.append(
        _table(
            [["Measure", "This period", "Change"]]
            + [[x["label"], _val(x), _chg(x)] for x in rep["kpis"]],
            [80 * mm, 45 * mm, 40 * mm],
        )
    )
    pr = rep["products"]
    el.append(
        KeepTogether(
            [
                Paragraph("Top products", h2),
                _table(
                    [["Product", "Units", "Net sales"]]
                    + [[x["name"], f"{float(x['units']):,.0f}", rs(x["net"])] for x in pr["top"]],
                    [90 * mm, 30 * mm, 45 * mm],
                ),
            ]
        )
    )
    el.append(
        KeepTogether(
            [
                Paragraph("Lowest sellers", h2),
                _table(
                    [["Product", "Units", "Net sales"]]
                    + [
                        [x["name"], f"{float(x['units']):,.0f}", rs(x["net"])] for x in pr["bottom"]
                    ],
                    [90 * mm, 30 * mm, 45 * mm],
                ),
            ]
        )
    )
    c = rep["customers"]
    el += [
        Paragraph("Customers", h2),
        Paragraph(
            f"{c['customers']} customers, {float(c['repeat_rate']):.0f}% repeat buyers; {c['lapsed_regulars']} regulars have gone quiet.",
            body,
        ),
    ]
    if rep.get("stock"):
        s = rep["stock"]
        el += [
            Paragraph("Stock", h2),
            Paragraph(
                f"{s['urgent']} products run out before a new order can arrive, {s['reorder']} to order soon. Cash tied up in stock: {rs(s['cash_tied'])}; in dead stock: {rs(s['dead_cash'])}.",
                body,
            ),
        ]
    if rep.get("udhaar"):
        u = rep["udhaar"]
        el += [
            Paragraph("Udhaar (credit)", h2),
            Paragraph(
                f"{u['parties_owing']} people owe {rs(u['outstanding'])}; {rs(u['overdue'])} ({u['overdue_pct']:.0f}%) is older than 30 days.",
                body,
            ),
        ]
    if rep.get("forecast"):
        f = rep["forecast"]
        el += [
            Paragraph("Forecast", h2),
            Paragraph(
                f"Next {f['horizon']} days: about {f['kpis']['units_next']:.0f} units (likely {f['kpis']['units_next_low']:.0f} to {f['kpis']['units_next_high']:.0f}). Past forecasts were off by {float(f['wape']) * 100:.0f}% on average. Built {f['as_of']}{' (out of date)' if f['stale'] else ''}.",
                body,
            ),
        ]
    if rep["recommendations"]:
        rows = [["Suggested action", "Status", "Likely impact"]]
        for r in rep["recommendations"]:
            i = r["impact"]
            rows.append(
                [
                    Paragraph(r["title"], body),
                    r["status"],
                    "not estimated"
                    if i.get("expected") is None
                    else f"{rs(i['low'])} to {rs(i['high'])}",
                ]
            )
        el += [Paragraph("Suggested actions", h2), _table(rows, [100 * mm, 22 * mm, 43 * mm])]
    el.append(Paragraph("Notes and limits", h2))
    for w in rep["warnings"] + rep["limits"]:
        el.append(Paragraph("- " + w, small))
    SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=18 * mm,
        title=f"{rep['shop']} business summary",
        author="Vyapar AI",
    ).build(el, onFirstPage=foot, onLaterPages=foot)
    return buf.getvalue()


def to_csv(rep: dict[str, Any]) -> str:
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["Section", "Item", "Value", "Previous", "Change %"])
    for k in rep["kpis"]:
        w.writerow(["Measures", k["label"], k["value"], k["previous"], k["change_pct"]])
    for e in rep["drivers"]["effects"]:
        w.writerow(["Drivers", e["label"], e["amount"], "", ""])
    for x in rep["products"]["top"]:
        w.writerow(["Top products", x["name"], x["net"], x["units"], ""])
    for x in rep["products"]["bottom"]:
        w.writerow(["Lowest sellers", x["name"], x["net"], x["units"], ""])
    for r in rep["recommendations"]:
        w.writerow(["Recommendations", r["title"], r["impact"].get("expected"), r["status"], ""])
    return out.getvalue()
