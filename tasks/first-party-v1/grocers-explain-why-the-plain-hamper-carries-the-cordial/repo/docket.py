"""The dockets: one per hamper, written out when the van is loaded."""

from typing import Any


def docket(hamper: dict[str, Any]) -> str:
    """One docket, reading straight off the hamper it rides in."""
    lines = [f"Hamper for {hamper['customer']}"]
    for item in hamper["contents"]:
        lines.append(f"  - {item}")
    lines.append(f"  {len(hamper['contents'])} item(s)")
    return "\n".join(lines)
