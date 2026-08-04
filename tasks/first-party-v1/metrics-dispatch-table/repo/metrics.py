"""Human-readable formatting for dashboard metrics."""


def format_metric(kind, value):
    """One metric value rendered for the dashboard, by kind."""
    if kind == "count":
        return f"{value:,}"
    elif kind == "percent":
        return f"{value * 100:.1f}%"
    elif kind == "duration":
        minutes, seconds = divmod(int(value), 60)
        return f"{minutes}m{seconds:02d}s"
    elif kind == "size":
        if value >= 1024 * 1024:
            return f"{value / (1024 * 1024):.1f}MiB"
        elif value >= 1024:
            return f"{value / 1024:.1f}KiB"
        return f"{value}B"
    else:
        raise KeyError(f"unknown metric kind: {kind}")


def metric_row(name, kind, value):
    """One aligned "name value" dashboard row."""
    return f"{name:<12}{format_metric(kind, value)}"
