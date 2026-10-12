"""Tests for the sax circuit models."""

import jax
import numpy as np
import pytest

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


@pytest.mark.parametrize("name", ["coupler", "coupler_ring"])
def test_composite_models_evaluate_under_jax_tracing(name):
    """Composite models build their sub-circuit once, so they trace under jit.

    Circuit simulators that wrap SAX models (e.g. Circulax) evaluate them on
    traced arrays; building a KLU-backed ``sax.circuit`` per call needs
    concrete values and fails there.
    """
    model = gpdk.models.get_models()[name]
    eager = model(wl=1.55)
    traced = jax.jit(lambda wl: model(wl=wl))(1.55)
    assert set(traced) == set(eager)
    for key, value in eager.items():
        np.testing.assert_allclose(traced[key], value, rtol=1e-6, atol=1e-12)
