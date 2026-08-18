"""The existence proof of the planted finding ('ringers.py', 'Band.ringer').

Read by the task-set lint and by nothing else: it fails on `repo/`, which ships
the change under review already applied, and passes on `corrected/`.

The house rule is that a ringer is asked for by name and the name is matched
however it was written down. The change normalises the name it was asked with
and then compares it against the name in the band exactly as that was written,
so a ringer written into the band with a capital or a stray space is nobody the
band can find.
"""

from ringers import Band, Ringer


def test_a_ringer_is_found_however_their_name_was_written_down():
    band = Band()
    band.take_on(Ringer("Ann Fisk", "treble"))

    assert band.ringer(" ann fisk ").bell == "treble"
