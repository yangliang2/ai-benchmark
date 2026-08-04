"""One-block summaries of a list of scores."""


def summary(scores):
    """The whole gradebook block: count, mean, median, best and worst."""
    if not scores:
        raise ValueError("no scores to summarise")
    ordered = sorted(scores)
    count = len(ordered)
    mean = sum(ordered) / count
    middle = count // 2
    if count % 2:
        median = float(ordered[middle])
    else:
        median = (ordered[middle - 1] + ordered[middle]) / 2
    return (
        f"students: {count}\n"
        f"average: {mean:.1f}\n"
        f"median: {median:.1f}\n"
        f"best: {ordered[-1]}\n"
        f"worst: {ordered[0]}"
    )
