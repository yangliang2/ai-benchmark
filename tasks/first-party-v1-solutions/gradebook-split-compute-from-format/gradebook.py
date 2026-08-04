"""One-block summaries of a list of scores."""


def compute_stats(scores):
    """The gradebook's numbers: count, mean, median, best and worst."""
    if not scores:
        raise ValueError("no scores to summarise")
    ordered = sorted(scores)
    count = len(ordered)
    middle = count // 2
    if count % 2:
        median = float(ordered[middle])
    else:
        median = (ordered[middle - 1] + ordered[middle]) / 2
    return {
        "count": count,
        "mean": sum(ordered) / count,
        "median": median,
        "best": ordered[-1],
        "worst": ordered[0],
    }


def format_summary(stats):
    """The gradebook block rendered from already-computed stats."""
    return (
        f"students: {stats['count']}\n"
        f"average: {stats['mean']:.1f}\n"
        f"median: {stats['median']:.1f}\n"
        f"best: {stats['best']}\n"
        f"worst: {stats['worst']}"
    )


def summary(scores):
    """The whole gradebook block: count, mean, median, best and worst."""
    return format_summary(compute_stats(scores))
