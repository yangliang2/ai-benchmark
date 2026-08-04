"""Run collections of jobs."""


def run_all(jobs):
    """Run every job in the order given, returning the names in run order."""
    executed = []
    for job in jobs:
        job.run()
        executed.append(job.name)
    return executed
