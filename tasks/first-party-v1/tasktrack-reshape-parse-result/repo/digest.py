"""The plain-text daily digest."""

from tasktrack import parse_task


def daily_digest(lines):
    """The open-task count, then every urgent open task with its tags."""
    open_count = 0
    urgent = []
    for line in lines:
        title, priority, tags, done = parse_task(line)
        if done:
            continue
        open_count += 1
        if priority == 1:
            rendered = " ".join(f"#{tag}" for tag in tags)
            urgent.append(f"* {title} {rendered}".rstrip())
    return "\n".join([f"open tasks: {open_count}", *urgent])
