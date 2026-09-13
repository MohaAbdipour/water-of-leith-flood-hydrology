import pandas as pd

from water_of_leith.event_classification import classification_agreement


def test_agreement_is_exact_paired_fraction():
    reference = pd.Series(["a", "b", "c", "d"])
    candidate = pd.Series(["a", "x", "c", "y"])
    assert classification_agreement(reference, candidate) == 0.5
