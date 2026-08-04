"""The plain-text daily digest."""

from tasktrack import parse_task


def daily_digest(lines):
    """The open-task count, then every urgent open task with its tags."""
    open_count = 0
    urgent = []
    for line in lines:
        task = parse_task(line)
        if task.done:
            continue
        open_count += 1
        if task.priority == 1:
            rendered = " ".join(f"#{tag}" for tag in task.tags)
            urgent.append(f"* {task.title} {rendered}".rstrip())
    return "\n".join([f"open tasks: {open_count}", *urgent])
