"""Run collections of jobs in dependency order."""

import heapq


def execution_order(jobs):
    """The names in run order: dependencies first, then priority (higher
    first), then name. ValueError on unknown dependencies and cycles."""
    by_name = {job.name: job for job in jobs}
    for job in jobs:
        for need in job.needs:
            if need not in by_name:
                raise ValueError(f"{job.name} needs unknown job {need!r}")
    blocking = {job.name: set(job.needs) for job in jobs}
    dependants = {job.name: [] for job in jobs}
    for job in jobs:
        for need in set(job.needs):
            dependants[need].append(job.name)
    ready = [
        (-job.priority, job.name) for job in jobs if not blocking[job.name]
    ]
    heapq.heapify(ready)
    order = []
    while ready:
        _, name = heapq.heappop(ready)
        order.append(name)
        for dependant in dependants[name]:
            blocking[dependant].discard(name)
            if not blocking[dependant]:
                heapq.heappush(
                    ready, (-by_name[dependant].priority, dependant)
                )
    if len(order) < len(by_name):
        stuck = sorted(set(by_name) - set(order))
        raise ValueError(f"dependency cycle among {stuck}")
    return order


def run_all(jobs):
    """Run every job, dependencies first, returning the names in run order."""
    by_name = {job.name: job for job in jobs}
    order = execution_order(jobs)
    for name in order:
        by_name[name].run()
    return order
