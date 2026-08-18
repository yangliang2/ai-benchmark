"""The existence proof of the planted finding ('graziers.py',
'Register.turned_out').

Read by the task-set lint and by nothing else: it fails on `repo/`, which
ships the change under review already applied, and passes on `corrected/`.

The house rule is that what the register hands out is a copy, and that a beast
is turned out by writing it in the register and in no other way. The change
hands out the register's own list, so a hand that takes what a commoner has
turned out can put a beast on the common without the reeve ever writing it
down.
"""

from graziers import Beast, Register


def test_what_the_register_hands_out_is_a_copy():
    register = Register()
    register.enter(Beast("ada", "cow", "AB"))

    register.turned_out("ada").append(Beast("ada", "horse", "CD"))

    assert [beast.mark for beast in register.turned_out("ada")] == ["AB"]
