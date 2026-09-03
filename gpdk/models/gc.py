"""SAX model for the fiber-chip grating coupler."""

import sax
import sax.models

sax.set_port_naming_strategy("optical")


def gc(
    wl=1.55, wl0=1.55, loss=3.0, reflection=0.1, reflection_fiber=0.1, bandwidth=0.04
) -> sax.SType:
    """Grating coupler model for fiber-chip coupling."""
    return sax.models.grating_coupler(
        wl=wl,
        wl0=wl0,
        loss=loss,
        reflection=reflection,
        reflection_fiber=reflection_fiber,
        bandwidth=bandwidth,
    )
