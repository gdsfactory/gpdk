"""Material cards supplied by the generic photonics PDK."""

from pdk_schema import (
    Band,
    MaterialCard,
    Provenance,
    Regime,
    Sellmeier,
    SellmeierTerm,
    Validity,
)


def _silicon_salzberg_card() -> MaterialCard:
    """Return the Salzberg crystalline-silicon card as ``Si``."""
    optical = Regime(
        temperature_ref=299.15,
        provenance=Provenance(
            source="literature",
            label="Salzberg silicon Sellmeier model",
            maturity="empirical",
            citations=[],
            comment=None,
            url=None,
            data_url=None,
            info={},
        ),
        permittivity=Sellmeier(
            validity=Validity(
                at=None,
                over={
                    "wavelength": Band(
                        min=1.357,
                        max=11.04,
                        unit="um",
                        label=None,
                    )
                },
                on_out_of_range="raise",
            ),
            variation=None,
            conductivity=None,
            terms=(
                SellmeierTerm(b=10.6684293, c_um=0.301516485),
                SellmeierTerm(b=0.0030434748, c_um=1.13475115),
                SellmeierTerm(b=1.54133408, c_um=1104.0),
            ),
            offset=0.0,
        ),
        conductivity=None,
        permeability=None,
        perturbations=[],
        info={},
    )
    return MaterialCard(name="Si", optical=optical, rf=None, info={})


MATERIAL_CARDS: dict[str, MaterialCard] = {"Si": _silicon_salzberg_card()}

__all__ = ["MATERIAL_CARDS"]
