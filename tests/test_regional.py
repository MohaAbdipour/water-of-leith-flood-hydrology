import numpy as np

from water_of_leith.regional import coefficient_of_variation


def test_coefficient_of_variation_uses_sample_standard_deviation():
    values = np.array([1.0, 2.0, 3.0])
    assert np.isclose(coefficient_of_variation(values), 0.5)
