import numpy as np

from water_of_leith.gis import cell_area_km2, hillshade


def test_flat_surface_has_uniform_hillshade():
    result = hillshade(np.ones((5, 5)), cell_size=30)
    assert result.shape == (5, 5)
    assert np.allclose(result, result[0, 0])
    assert np.all((result >= 0) & (result <= 1))


def test_cell_area_uses_projected_cell_dimensions():
    mask = np.array([[True, False], [True, True]])
    assert cell_area_km2(mask, cell_size=100) == 0.03
