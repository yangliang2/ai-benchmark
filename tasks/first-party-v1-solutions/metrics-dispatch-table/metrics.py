"""Human-readable formatting for dashboard metrics."""


def _format_count(value):
    return f"{value:,}"


def _format_percent(value):
    return f"{value * 100:.1f}%"


def _format_duration(value):
    minutes, seconds = divmod(int(value), 60)
    return f"{minutes}m{seconds:02d}s"


def _format_size(value):
    if value >= 1024 * 1024:
        return f"{value / (1024 * 1024):.1f}MiB"
    if value >= 1024:
        return f"{value / 1024:.1f}KiB"
    return f"{value}B"


FORMATTERS = {
    "count": _format_count,
    "percent": _format_percent,
    "duration": _format_duration,
    "size": _format_size,
}


def format_metric(kind, value):
    """One metric value rendered for the dashboard, by kind."""
    try:
        formatter = FORMATTERS[kind]
    except KeyError:
        raise KeyError(f"unknown metric kind: {kind}") from None
    return formatter(value)


def metric_row(name, kind, value):
    """One aligned "name value" dashboard row."""
    return f"{name:<12}{format_metric(kind, value)}"
