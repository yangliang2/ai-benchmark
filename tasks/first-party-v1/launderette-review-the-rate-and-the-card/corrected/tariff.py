"""What one wash comes to."""

PENCE_BY_SIZE = {"small": 260, "medium": 340, "large": 420}
SOAP_PENCE = 40

# In with the late rate: a wash started from eight at night onwards is sixty
# pence off, whichever drum it goes in.
LATE_FROM_HOUR = 20
LATE_OFF_PENCE = 60


def price_for(size, hour, soap=False):
    """What a wash of this size, started at this hour, comes to in pence."""
    pence = PENCE_BY_SIZE[size]
    if hour >= LATE_FROM_HOUR:
        pence -= LATE_OFF_PENCE
    if soap:
        pence += SOAP_PENCE
    return pence
