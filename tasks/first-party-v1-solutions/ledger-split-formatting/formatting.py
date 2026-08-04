"""Money formatting for the ledger."""


def format_amount(cents):
    """Render an integer number of cents as a signed currency string."""
    sign = "-" if cents < 0 else ""
    whole, remainder = divmod(abs(cents), 100)
    return f"{sign}${whole}.{remainder:02d}"


def format_line(description, cents):
    """Render one ledger line as "<description>: <amount>"."""
    return f"{description}: {format_amount(cents)}"
