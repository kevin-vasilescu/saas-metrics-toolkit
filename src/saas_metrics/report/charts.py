"""Inline SVG charts."""

from __future__ import annotations

from html import escape


def line_chart(labels: list[str], values: list[float], width: int = 760, height: int = 260) -> str:
    """Render a simple line chart as an inline SVG string.

    Args:
        labels: X-axis labels, one per value.
        values: Y values.
        width: SVG viewBox width.
        height: SVG viewBox height.

    Returns:
        SVG markup, or an empty string when there are no values.
    """
    if not values:
        return ""
    left, right, top, bottom = 64, 16, 16, 32
    plot_w, plot_h = width - left - right, height - top - bottom
    low, high = min(0.0, min(values)), max(values)
    span = (high - low) or 1.0

    def x(i: int) -> float:
        return left + (plot_w * i / (len(values) - 1) if len(values) > 1 else plot_w / 2)

    def y(v: float) -> float:
        return top + plot_h * (1 - (v - low) / span)

    grid = []
    for k in range(5):
        v = low + span * k / 4
        grid.append(
            f'<line x1="{left}" x2="{width - right}" y1="{y(v):.1f}" y2="{y(v):.1f}" stroke="#e5e7eb"/>'
            f'<text x="{left - 8}" y="{y(v) + 4:.1f}" text-anchor="end" font-size="11" fill="#6b7280">{v:,.0f}</text>'
        )
    step = max(1, len(labels) // 8)
    ticks = [
        f'<text x="{x(i):.1f}" y="{height - 10}" text-anchor="middle" font-size="11" fill="#6b7280">{escape(labels[i])}</text>'
        for i in range(0, len(labels), step)
    ]
    points = " ".join(f"{x(i):.1f},{y(v):.1f}" for i, v in enumerate(values))
    dots = "".join(
        f'<circle cx="{x(i):.1f}" cy="{y(v):.1f}" r="3" fill="#4f46e5"><title>{escape(labels[i])}: {v:,.2f}</title></circle>'
        for i, v in enumerate(values)
    )
    return (
        f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="MRR by month" '
        f'style="width:100%;height:auto">{"".join(grid)}{"".join(ticks)}'
        f'<polyline points="{points}" fill="none" stroke="#4f46e5" stroke-width="2.5"/>{dots}</svg>'
    )
