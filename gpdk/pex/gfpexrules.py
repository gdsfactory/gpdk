"""gf-pex parasitic extraction rules (techfile) for the generic PDK.

Mirrors the gf-pex gf180mcuD template (``kpex_schema/gen_tech_pb/pdk/gf180mcuD.py``):
layers -> LVS computed layers -> process stack -> parasitics -> ``build_tech()``.

GDS layers and stack heights come from ``gpdk.layer_map.LAYER`` and
``gpdk.layer_stack.LAYER_STACK`` so the rules never drift from the PDK.
gpdk is generic, so there is no foundry parasitics data:

- metal / poly sheet resistance: gpdk's own ``gpdk.cells.resistor.SHEET_RESISTANCE``
- via / contact resistance and capacitances: gf180mcuD template values, mapped by
  ``GF180_TEMPLATE_LAYER`` (M1 -> Metal1, M2 -> Metal2, M3 -> Metal3, POLY -> Poly2,
  HEATER -> Metal1 (same height), NPP / PPP -> COMP)
- layers / pairs with no gf180 counterpart (heater / MIM / doped-slab sheet R, MIM and
  slab capacitances): physics-based estimates, marked ``estimate``

Units follow the gf-pex techfile: resistance in mΩ (per square / per via),
capacitance in aF/µm² (area) and aF/µm (length), heights in µm.

Usage::

    from gpdk.pex.gfpexrules import build_tech

    build_tech().save("gpdk_tech.pb.json")
"""

from __future__ import annotations

from itertools import combinations
from pathlib import Path
from typing import NamedTuple

from gf_pex.techfile import (
    CapacitanceInfo,
    ComputedLayerInfo,
    ComputedLayerKind,
    Contact,
    ContactResistance,
    DiffusionLayer,
    FieldOxideLayer,
    GDSPair,
    LayerInfo,
    LayerPurpose,
    LayerResistance,
    MetalLayer,
    OverlapCapacitance,
    ProcessParasiticsInfo,
    ProcessStackInfo,
    ResistanceInfo,
    SideOverlapCapacitance,
    SidewallCapacitance,
    SimpleDielectricLayer,
    StackLayerInfo,
    StackLayerType,
    SubstrateCapacitance,
    SubstrateLayer,
    Techfile,
    ViaResistance,
)

from gpdk.cells.resistor import SHEET_RESISTANCE
from gpdk.layer_map import LAYER
from gpdk.layer_stack import DOPING, LAYER_STACK, LayerStackParameters

DIFF = LayerPurpose.PURPOSE_DIFF
NWELL = LayerPurpose.PURPOSE_NWELL
NIMP = LayerPurpose.PURPOSE_N_IMPLANT
PIMP = LayerPurpose.PURPOSE_P_IMPLANT
CONT = LayerPurpose.PURPOSE_CONTACT
METAL = LayerPurpose.PURPOSE_METAL
VIA = LayerPurpose.PURPOSE_VIA
MIM = LayerPurpose.PURPOSE_MIM_CAP

KREG = ComputedLayerKind.KIND_REGULAR

STACK = LayerStackParameters
OHM_TO_MILLIOHM = 1e3
UM_TO_CM = 1e-4
UM_TO_M = 1e-6
ELEMENTARY_CHARGE_C = 1.602e-19
VACUUM_PERMITTIVITY_AF_PER_UM = 8.854
OXIDE_K = 3.9
AIR_K = 1.0

# gf-pex heights start at the substrate top; gpdk's z = 0 is the BOX top (silicon bottom).
Z_SILICON_UM = STACK.box_thickness

# gpdk.cells.vias defaults (via / via1 / via2): 0.7 µm cut, 2 µm pitch, 1 µm enclosure.
VIA_SIZE_UM = 0.7
VIA_PITCH_UM = 2.0
VIA_ENCLOSURE_UM = 1.0

# gf180mcuD template values (gf-pex kpex_schema/gen_tech_pb/pdk/gf180mcuD.py).
GF180_TEMPLATE_LAYER = {
    "POLY": "Poly2",
    "M1": "Metal1",
    "HEATER": "Metal1",
    "M2": "Metal2",
    "M3": "Metal3",
    "NPP": "COMP",
    "PPP": "COMP",
}
# contact resistance (mΩ/contact): M1-Nplus, M1-Pplus, M1-Poly
GF180_CONTACT_RESISTANCE = {"NPP": 6300, "PPP": 5200, "POLY": 5900}
# via resistance (mΩ/via): Via1 ... Via5
GF180_VIA_RESISTANCE = 4500
# substrate capacitance (aF/µm² area, aF/µm perimeter)
GF180_SUBSTRATE_CAPACITANCE = {
    "Poly2": (110.67, 50.72),
    "Metal1": (29.304, 39.431),
    "Metal2": (15.016, 33.298),
    "Metal3": (10.094, 30.021),
}
# overlap capacitance (aF/µm²), (top, bottom)
GF180_OVERLAP_CAPACITANCE = {
    ("Metal1", "COMP"): 30.502,
    ("Metal1", "Poly2"): 51.434,
    ("Metal2", "COMP"): 17.305,
    ("Metal2", "Poly2"): 19.263,
    ("Metal2", "Metal1"): 59.027,
    ("Metal3", "COMP"): 11.079,
    ("Metal3", "Poly2"): 11.85,
    ("Metal3", "Metal1"): 20.238,
    ("Metal3", "Metal2"): 59.027,
}
# sidewall capacitance (aF/µm, offset µm)
GF180_SIDEWALL_CAPACITANCE = {
    "Poly2": (11.098, -0.082),
    "Metal1": (40.512, -0.053),
    "Metal2": (46.736, 0.289),
    "Metal3": (70.675, 0.534),
}
# sidewall-overlap capacitance (aF/µm), (in, out)
GF180_SIDEOVERLAP_CAPACITANCE = {
    ("Metal1", "COMP"): 43.406,
    ("Metal1", "Poly2"): 46.700,
    ("Poly2", "Metal1"): 17.946,
    ("Metal2", "COMP"): 35.189,
    ("Metal2", "Poly2"): 36.169,
    ("Poly2", "Metal2"): 8.706,
    ("Metal2", "Metal1"): 47.566,
    ("Metal1", "Metal2"): 32.048,
    ("Metal3", "COMP"): 31.40,
    ("Metal3", "Poly2"): 31.927,
    ("Poly2", "Metal3"): 5.895,
    ("Metal3", "Metal1"): 36.609,
    ("Metal1", "Metal3"): 18.135,
    ("Metal3", "Metal2"): 49.011,
    ("Metal2", "Metal3"): 36.626,
}

# Estimates, only where gf180 has no counterpart.
TIN_RESISTIVITY_OHM_M = 1.0e-6  # TiN heater / MIM plate film (~100 µΩ·cm)
# Majority-carrier mobility at ~1e20 cm^-3 (cm²/Vs), for the doped-slab sheet resistance.
HEAVY_DOPING_MOBILITY_CM2_PER_VS = {"NPP": 90.0, "PPP": 50.0}
# Sakurai-Tamaru wire-over-plane fringe: C/L = eps * 2.80 * (T/H)^0.222 for both edges.
SAKURAI_FRINGE_COEFFICIENT_PER_EDGE = 2.80 / 2
SAKURAI_FRINGE_EXPONENT = 0.222


class Conductor(NamedTuple):
    """A conducting stack layer: techfile name, GDS layer, bottom / top height (µm)."""

    name: str
    gds: tuple[int, int]
    z_bottom: float
    z_top: float

    @property
    def thickness(self) -> float:
        """Layer thickness in µm."""
        return self.z_top - self.z_bottom


def _make_conductor(name: str, gds: tuple[int, int], level_name: str) -> Conductor:
    level = LAYER_STACK.layers[level_name]
    z_bottom = Z_SILICON_UM + level.zmin
    return Conductor(name, gds, z_bottom, z_bottom + level.thickness)


# techfile name -> (GDS layer, gpdk LAYER_STACK level)
CONDUCTORS = {
    name: _make_conductor(name, gds, level_name)
    for name, gds, level_name in (
        ("NPP", LAYER.NPP, "npp"),
        ("PPP", LAYER.PPP, "ppp"),
        ("POLY", LAYER.POLY, "poly"),
        ("M1", LAYER.M1, "metal1"),
        ("HEATER", LAYER.HEATER, "heater"),
        ("M2", LAYER.M2, "metal2"),
        ("MIM", LAYER.MIM, "mim"),
        ("M3", LAYER.M3, "metal3"),
    )
}

# (contact / via computed name, drawn cut layer name, cut GDS, conductor below, conductor above)
CUTS = (
    ("viac_npp_con", "VIAC", LAYER.VIAC, "NPP", "M1"),
    ("viac_ppp_con", "VIAC", LAYER.VIAC, "PPP", "M1"),
    ("viac_poly_con", "VIAC", LAYER.VIAC, "POLY", "M1"),
    ("via1_con", "VIA1", LAYER.VIA1, "M1", "M2"),
    ("via1_heater_con", "VIA1", LAYER.VIA1, "HEATER", "M2"),
    ("via2_con", "VIA2", LAYER.VIA2, "M2", "M3"),
    ("via2_mim_con", "VIA2", LAYER.VIA2, "MIM", "M3"),
)
DEVICE_CONTACTS = {"viac_npp_con", "viac_ppp_con", "viac_poly_con"}


def _gds_pair(gds: tuple[int, int]) -> GDSPair:
    return GDSPair(layer=gds[0], datatype=gds[1])


def build_layers(tech: Techfile) -> None:
    """Drawn gpdk layers that carry current or define wells / implants."""
    drawn_layers = (
        (NWELL, "NWELL", LAYER.NWELL, "N-well region"),
        (DIFF, "ACTIVE", LAYER.ACTIVE, "CMOS active silicon"),
        (NIMP, "NPP", LAYER.NPP, "N++ doped silicon (contact region)"),
        (PIMP, "PPP", LAYER.PPP, "P++ doped silicon (contact region)"),
        (METAL, "POLY", LAYER.POLY, "Gate polysilicon"),
        (CONT, "VIAC", LAYER.VIAC, "Contact from silicon / poly to M1"),
        (METAL, "M1", LAYER.M1, "Metal 1"),
        (METAL, "HEATER", LAYER.HEATER, "TiN heater"),
        (VIA, "VIA1", LAYER.VIA1, "Via from M1 / HEATER to M2"),
        (METAL, "M2", LAYER.M2, "Metal 2"),
        (MIM, "MIM", LAYER.MIM, "MIM capacitor top plate over M2"),
        (VIA, "VIA2", LAYER.VIA2, "Via from M2 / MIM to M3"),
        (METAL, "M3", LAYER.M3, "Metal 3 (MTOP)"),
    )
    for purpose, name, gds, description in drawn_layers:
        tech.layers.append(
            LayerInfo(
                purpose=purpose,
                name=name,
                drw_gds_pair=_gds_pair(gds),
                description=description,
            )
        )


def build_lvs_computed_layers(tech: Techfile) -> None:
    """Connectivity names used in the stack; contacts map back to their drawn cut layer."""
    for conductor in CONDUCTORS.values():
        tech.lvs_computed_layers.append(
            ComputedLayerInfo(
                kind=KREG,
                layer_info=LayerInfo(
                    purpose=METAL,
                    name=conductor.name,
                    drw_gds_pair=_gds_pair(conductor.gds),
                    description=f"Computed layer for {conductor.name}",
                ),
                original_layer_name=conductor.name,
            )
        )
    for cut_name, original_name, gds, below, above in CUTS:
        tech.lvs_computed_layers.append(
            ComputedLayerInfo(
                kind=KREG,
                layer_info=LayerInfo(
                    purpose=CONT if cut_name in DEVICE_CONTACTS else VIA,
                    name=cut_name,
                    drw_gds_pair=_gds_pair(gds),
                    description=f"Computed {original_name} between {below} and {above}",
                ),
                original_layer_name=original_name,
            )
        )


def _make_contact(cut_name: str, below: str, above: str) -> Contact:
    return Contact(
        name=cut_name,
        layer_below=below,
        metal_above=above,
        thickness=CONDUCTORS[above].z_bottom - CONDUCTORS[below].z_top,
        width=VIA_SIZE_UM,
        spacing=VIA_PITCH_UM - VIA_SIZE_UM,
        border=VIA_ENCLOSURE_UM,
    )


def build_process_stack_info(tech: Techfile) -> None:
    """SOI stack: Si substrate, BOX, doped slab, poly, M1 / heater, M2, MIM, M3, oxide."""
    tech.process_stack = ProcessStackInfo()
    layers = tech.process_stack.layers
    contacts_by_lower = {below: [] for _, _, _, below, _ in CUTS}
    for cut_name, _, _, below, above in CUTS:
        contacts_by_lower[below].append(_make_contact(cut_name, below, above))

    layers.append(
        StackLayerInfo(
            name="subs",
            layer_type=StackLayerType.LAYER_TYPE_SUBSTRATE,
            substrate_layer=SubstrateLayer(
                height=0.0, thickness=STACK.substrate_thickness, reference="box"
            ),
        )
    )
    layers.append(
        StackLayerInfo(
            name="box",
            layer_type=StackLayerType.LAYER_TYPE_FIELD_OXIDE,
            field_oxide_layer=FieldOxideLayer(dielectric_k=OXIDE_K),
        )
    )
    for name in ("NPP", "PPP"):
        layers.append(
            StackLayerInfo(
                name=name,
                layer_type=StackLayerType.LAYER_TYPE_DIFFUSION,
                diffusion_layer=DiffusionLayer(
                    z=CONDUCTORS[name].z_bottom,
                    reference="box",
                    contact_above=contacts_by_lower[name][0],
                ),
            )
        )
    for name in ("POLY", "M1", "HEATER", "M2", "MIM", "M3"):
        conductor = CONDUCTORS[name]
        contact_above = contacts_by_lower.get(name, [None])[0]
        layers.append(
            StackLayerInfo(
                name=name,
                layer_type=StackLayerType.LAYER_TYPE_METAL,
                metal_layer=MetalLayer(
                    z=conductor.z_bottom,
                    thickness=conductor.thickness,
                    contact_above=contact_above,
                ),
            )
        )
    layers.append(
        StackLayerInfo(
            name="clad",
            layer_type=StackLayerType.LAYER_TYPE_SIMPLE_DIELECTRIC,
            simple_dielectric_layer=SimpleDielectricLayer(
                dielectric_k=OXIDE_K, reference="box"
            ),
        )
    )
    layers.append(
        StackLayerInfo(
            name="air",
            layer_type=StackLayerType.LAYER_TYPE_SIMPLE_DIELECTRIC,
            simple_dielectric_layer=SimpleDielectricLayer(
                dielectric_k=AIR_K, reference="clad"
            ),
        )
    )


def get_doped_slab_sheet_resistance_milliohm(name: str) -> float:
    """R□ = 1 / (q N µ t) for the uniformly doped slab (DOPING from gpdk.layer_stack)."""
    concentration_per_cm3 = next(
        concentration
        for _, layer, _, concentration in DOPING
        if layer == getattr(LAYER, name)
    )
    resistivity_ohm_cm = 1.0 / (
        ELEMENTARY_CHARGE_C
        * concentration_per_cm3
        * HEAVY_DOPING_MOBILITY_CM2_PER_VS[name]
    )
    thickness_cm = CONDUCTORS[name].thickness * UM_TO_CM
    return resistivity_ohm_cm / thickness_cm * OHM_TO_MILLIOHM


def _get_permittivity_af_per_um(dielectric_k: float = OXIDE_K) -> float:
    return VACUUM_PERMITTIVITY_AF_PER_UM * dielectric_k


def _get_fringe_af_per_um(thickness_um: float, height_um: float) -> float:
    ratio = thickness_um / height_um
    return (
        _get_permittivity_af_per_um()
        * SAKURAI_FRINGE_COEFFICIENT_PER_EDGE
        * ratio**SAKURAI_FRINGE_EXPONENT
    )


def _get_template_name(name: str) -> str | None:
    return GF180_TEMPLATE_LAYER.get(name)


def _get_tin_sheet_resistance_milliohm(name: str) -> float:
    return (
        TIN_RESISTIVITY_OHM_M / (CONDUCTORS[name].thickness * UM_TO_M) * OHM_TO_MILLIOHM
    )


def build_process_parasitics_info(tech: Techfile) -> None:
    """Sheet / via / contact R and area / edge capacitances for the gpdk stack."""
    tech.process_parasitics = ProcessParasiticsInfo(
        side_halo=8.0,
        resistance=ResistanceInfo(),
        capacitance=CapacitanceInfo(),
    )
    resistance = tech.process_parasitics.resistance
    capacitance = tech.process_parasitics.capacitance

    # sheet resistance (mΩ/sq): gpdk SHEET_RESISTANCE (Ω/sq), estimates where missing
    sheet_resistance_milliohm = {
        "POLY": SHEET_RESISTANCE["npolyf_s"] * OHM_TO_MILLIOHM,
        "M1": SHEET_RESISTANCE["M1"] * OHM_TO_MILLIOHM,
        "M2": SHEET_RESISTANCE["M2"] * OHM_TO_MILLIOHM,
        "M3": SHEET_RESISTANCE["M3"] * OHM_TO_MILLIOHM,
        "HEATER": _get_tin_sheet_resistance_milliohm("HEATER"),  # estimate
        "MIM": _get_tin_sheet_resistance_milliohm("MIM"),  # estimate
        "NPP": get_doped_slab_sheet_resistance_milliohm("NPP"),  # estimate
        "PPP": get_doped_slab_sheet_resistance_milliohm("PPP"),  # estimate
    }
    for layer_name, sheet_milliohm in sheet_resistance_milliohm.items():
        resistance.layers.append(
            LayerResistance(layer_name=layer_name, resistance=sheet_milliohm)
        )

    # contact resistance (mΩ/contact): gf180 M1-Nplus / M1-Pplus / M1-Poly
    for cut_name, _, _, below, above in CUTS:
        if cut_name in DEVICE_CONTACTS:
            resistance.contacts.append(
                ContactResistance(
                    contact_name=cut_name,
                    device_layer_name=below,
                    layer_above=above,
                    resistance=GF180_CONTACT_RESISTANCE[below],
                )
            )

    # via resistance (mΩ/via): gf180 Via1..Via5, keyed by the drawn cut layer
    for via_name in ("VIA1", "VIA2"):
        resistance.vias.append(
            ViaResistance(via_name=via_name, resistance=GF180_VIA_RESISTANCE)
        )

    # estimates below use oxide everywhere (k = 3.9): parallel plate + Sakurai-Tamaru fringe
    permittivity = _get_permittivity_af_per_um()

    # substrate capacitance (aF/µm² area, aF/µm perimeter)
    for conductor in CONDUCTORS.values():
        area, perimeter = GF180_SUBSTRATE_CAPACITANCE.get(
            _get_template_name(conductor.name),
            (  # estimate: through BOX + cladding
                permittivity / conductor.z_bottom,
                _get_fringe_af_per_um(conductor.thickness, conductor.z_bottom),
            ),
        )
        capacitance.substrates.append(
            SubstrateCapacitance(
                layer_name=conductor.name,
                area_capacitance=area,
                perimeter_capacitance=perimeter,
            )
        )

    # overlap (aF/µm²) and side-overlap (aF/µm) for every vertically separated pair
    for lower, upper in combinations(
        sorted(CONDUCTORS.values(), key=lambda conductor: conductor.z_bottom), 2
    ):
        gap_um = upper.z_bottom - lower.z_top
        if gap_um <= 0:
            continue
        upper_template = _get_template_name(upper.name)
        lower_template = _get_template_name(lower.name)
        capacitance.overlaps.append(
            OverlapCapacitance(
                top_layer_name=upper.name,
                bottom_layer_name=lower.name,
                capacitance=GF180_OVERLAP_CAPACITANCE.get(
                    (upper_template, lower_template), permittivity / gap_um
                ),
            )
        )
        for in_layer, out_layer, in_template, out_template in (
            (upper, lower, upper_template, lower_template),
            (lower, upper, lower_template, upper_template),
        ):
            capacitance.sideoverlaps.append(
                SideOverlapCapacitance(
                    in_layer_name=in_layer.name,
                    out_layer_name=out_layer.name,
                    capacitance=GF180_SIDEOVERLAP_CAPACITANCE.get(
                        (in_template, out_template),
                        _get_fringe_af_per_um(in_layer.thickness, gap_um),
                    ),
                )
            )

    # sidewall capacitance (aF/µm, offset µm); gf-pex: C = c · L / (gap + offset),
    # so the parallel-plate estimate is c = ε · thickness
    for conductor in CONDUCTORS.values():
        coefficient, offset = GF180_SIDEWALL_CAPACITANCE.get(
            _get_template_name(conductor.name),
            (permittivity * conductor.thickness, 0.0),
        )
        capacitance.sidewalls.append(
            SidewallCapacitance(
                layer_name=conductor.name, capacitance=coefficient, offset=offset
            )
        )


def build_tech() -> Techfile:
    """Assemble the gpdk gf-pex techfile."""
    tech = Techfile(name="gpdk")
    build_layers(tech)
    build_lvs_computed_layers(tech)
    build_process_stack_info(tech)
    build_process_parasitics_info(tech)
    return tech


if __name__ == "__main__":
    output_path = Path(__file__).with_name("gpdk_tech.pb.json")
    build_tech().save(output_path)
    print(f"wrote {output_path}")
