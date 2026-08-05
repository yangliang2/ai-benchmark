"""How `labels` is graded: against the label the despatch team specified.

Every decision behind a label is stated in the prompt, so the expected strings
can be written out here in full — this is the zero-crux control the packing
task is compared against, and there is nothing about it left to invent.
"""

import pytest
from cartons import Item, labels

DESPATCH = [
    [Item("kx-1", 300), Item("kx-2", 250)],
    [Item("mm-9", 900)],
]


def test_a_label_names_the_destination_the_number_and_the_contents():
    assert labels(DESPATCH, "LON") == [
        "LON-001 kx-1,kx-2 550g",
        "LON-002 mm-9 900g",
    ]


def test_the_destination_is_written_in_upper_case():
    assert labels([[Item("kx-1", 300)]], "ams") == ["AMS-001 kx-1 300g"]


def test_the_carton_number_keeps_three_digits_past_the_ninth():
    despatch = [[Item(f"s{number}", 100)] for number in range(11)]

    numbered = [label.split(" ")[0] for label in labels(despatch, "LON")]

    assert numbered[8:] == ["LON-009", "LON-010", "LON-011"]


@pytest.mark.parametrize(
    "weight, written",
    [(999, "999g"), (1000, "1.0kg"), (1250, "1.2kg"), (1299, "1.2kg")],
)
def test_a_carton_of_a_kilogram_or_more_is_weighed_in_kilograms(weight, written):
    assert labels([[Item("kx-1", weight)]], "LON") == [f"LON-001 kx-1 {written}"]


def test_a_carton_with_nothing_in_it_says_so():
    assert labels([[]], "LON") == ["LON-001 (empty) 0g"]


@pytest.mark.parametrize("destination", ["LON", "ams"])
def test_no_cartons_gives_no_labels(destination):
    assert list(labels([], destination)) == []
