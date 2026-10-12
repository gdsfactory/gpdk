# gpdk

A generic, foundry-agnostic PDK for demonstrating electronic-photonic design tooling: a
copy of gdsfactory's generic photonic PDK, extended with a small set of electrical and
electro-optic devices.

## Language

### Cell provenance

**Generated cell**:
A cell that re-emits a gdsfactory core component unchanged; owned by the generator.
_Avoid_: core cell, wrapper

**Hand-written cell**:
A cell gpdk owns itself because gdsfactory core has no equivalent; ported from a foundry PDK and remapped onto gpdk layers.
_Avoid_: custom cell, manual cell

### Electrical devices

**nch**:
3.3V n-channel MOSFET, ported from gf180mcu `nfet`.
_Avoid_: nmos, nfet

**pch**:
3.3V p-channel MOSFET in an n-well, ported from gf180mcu `pfet`.
_Avoid_: pmos, pfet

**cmim**:
Metal-insulator-metal capacitor: a MIM plate between M2 and M3.
_Avoid_: cap_mim, MIM cap

**cmom**:
Metal-oxide-metal capacitor: interdigitated fingers stacked over one or more metal levels.
_Avoid_: MOM cap, finger capacitor

**res_poly**:
Polysilicon resistor; silicided (`_s`) or unsilicided (`_u`), p- or n-doped.
_Avoid_: poly resistor, ppolyf

**res_metal**:
Resistor drawn in one BEOL metal (M1, M2 or M3), identified by a metal-resistor marker.
_Avoid_: rm1, metal resistor

### Electro-optic devices

**PN phase shifter**:
A rib waveguide with a lateral PN junction across its core whose depletion width, and so its effective index, is set by a reverse bias. `straight_pn_ribbed` is the corrugated (ribbed) variant.
_Avoid_: PN modulator (a modulator is the MZM or ring built from it)

### Process

**Monolithic shared BEOL**:
CMOS devices are built in the same SOI silicon as the photonic waveguides and are wired with the same M1–M3 metals and vias.
_Avoid_: co-integration, separate CMOS stack
