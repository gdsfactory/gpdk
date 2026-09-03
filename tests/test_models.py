"""Tests for the sax circuit models."""

import gpdk


def test_get_models_returns_callables():
    """Every model is a callable keyed by name."""
    models = gpdk.models.get_models()
    assert models
    assert all(callable(m) for m in models.values())


def test_models_are_registered_on_the_pdk():
    """The PDK exposes the models."""
    assert gpdk.PDK.models
    assert set(gpdk.PDK.models) == set(gpdk.models.get_models())


def test_straight_model_returns_an_sdict():
    """The straight model evaluates to an S-dict with the expected ports."""
    models = gpdk.models.get_models()
    s = models["straight"](wl=1.55)
    assert ("o1", "o2") in s or ("o2", "o1") in s
