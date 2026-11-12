"""Circulax time-domain models for active photonic devices.

Requires ``circulax`` to be installed (``uv add gpdk[active]``).
"""

from __future__ import annotations

import jax.numpy as jnp
from circulax.components.base_component import (
    PhysicsReturn,
    Signals,
    States,
    component,
)
from circulax.s_transforms import s_to_y

__all__ = [
    "ge_photodetector",
    "thermal_heater",
    "ring_modulator",
    "ring_modulator_add_drop",
]


@component(ports=("opt_in", "ele_P", "ele_N"))
def ge_photodetector(
    signals: Signals,
    s: States,
    responsivity: float = 0.95,
    reflection: float = 0.0,
    dark_current: float = 44.4e-9,
    Cj: float = 54.2e-15,
    Is: float = 1e-12,
    n: float = 1.5,
    Vt: float = 25.85e-3,
) -> PhysicsReturn:
    """Germanium waveguide photodetector (single PIN junction).

    Optical power on ``opt_in`` generates photocurrent that flows from
    anode (``ele_P``) to cathode (``ele_N``).

    Args:
        signals: Port voltages / field amplitudes.
        s: Unused (no internal state variables).
        responsivity: Photocurrent per watt of optical power (A/W).
        reflection: Power reflection coefficient at the optical port (0-1).
        dark_current: Reverse-bias leakage current (A).
        Cj: Junction capacitance (F).
        Is: Diode saturation current (A).
        n: Diode ideality factor.
        Vt: Thermal voltage (V).
    """
    r = jnp.sqrt(reflection)
    y_opt = (1.0 - r) / (1.0 + r + 1e-30)
    i_opt = y_opt * signals.opt_in

    P_opt = jnp.abs(signals.opt_in) ** 2 * (1.0 - reflection)
    I_photo = responsivity * P_opt + dark_current

    v_diode = jnp.real(signals.ele_P - signals.ele_N)
    v_safe = jnp.clip(v_diode, -5.0, 2.0)
    I_diode = Is * (jnp.exp(v_safe / (n * Vt)) - 1.0)

    I_P = I_diode - I_photo
    I_N = -(I_diode - I_photo)

    Q_P = Cj * v_diode
    Q_N = -Cj * v_diode

    return (
        {"opt_in": i_opt, "ele_P": I_P, "ele_N": I_N},
        {"opt_in": 0.0, "ele_P": Q_P, "ele_N": Q_N},
    )


@component(ports=("opt_in", "opt_out", "ele_P", "ele_N"), states=("dT",))
def thermal_heater(
    signals: Signals,
    s: States,
    resistivity_ohm_per_um: float = 1.448,
    alpha_R: float = 557e-6,
    T_ref: float = 25.0,
    eta_pi_per_W: float = 85.0,
    length_um: float = 320.0,
    loss_dBcm: float = 3.0,
    neff0: float = 2.38,
    wl: float = 1.55,
    R_th: float = 647.0,
    C_th: float = 4.64e-9,
    T_env: float = 25.0,
) -> PhysicsReturn:
    """Resistive heater / thermal phase shifter (C-band).

    Current through the heater strip dissipates Joule heat, raising the
    local waveguide temperature via a first-order thermal RC network.  The
    temperature rise shifts the effective index (thermo-optic effect),
    producing a phase shift on the guided optical mode.

    The internal state ``dT`` tracks the temperature rise above ambient (K).

    Args:
        signals: Port voltages / field amplitudes.
        s: Internal state -- ``s.dT`` is temperature rise above ambient (K).
        resistivity_ohm_per_um: Heater resistance per unit length (ohm/um).
        alpha_R: Temperature coefficient of resistance (1/K).
        T_ref: Reference temperature for the TCR model (deg C).
        eta_pi_per_W: Heater efficiency -- pi phase shifts per watt.
        length_um: Heater (and waveguide) length (um).
        loss_dBcm: Waveguide propagation loss under the heater (dB/cm).
        neff0: Effective index of the guided mode at T_env.
        wl: Operating wavelength (um).
        R_th: Thermal resistance, heater-to-ambient (K/W).
        C_th: Thermal capacitance of the heated volume (J/K).
        T_env: Ambient (heat-sink) temperature (deg C).
    """
    dT = jnp.real(s.dT)

    V_heater = jnp.real(signals.ele_P - signals.ele_N)
    R0 = resistivity_ohm_per_um * length_um
    R_T = R0 * (1.0 + alpha_R * (dT + T_env - T_ref))
    R_T = jnp.maximum(R_T, 1.0)
    I_heater = V_heater / R_T
    P_elec = V_heater * I_heater

    rhs_dT = (P_elec - dT / R_th) / C_th

    dphi_thermo = jnp.pi * eta_pi_per_W * dT / R_th
    phi_total = 2.0 * jnp.pi * neff0 * length_um / wl + dphi_thermo

    loss_dB = loss_dBcm * length_um * 1e-4
    t_amp = jnp.minimum(10.0 ** (-loss_dB / 20.0), 1.0 - 1e-6)

    s21 = t_amp * jnp.exp(-1j * phi_total)
    S = jnp.array([[0.0 + 0j, s21], [s21, 0.0 + 0j]])
    Y = s_to_y(S)

    v_opt = jnp.array([signals.opt_in, signals.opt_out])
    i_opt = Y @ v_opt

    return (
        {
            "opt_in": i_opt[0],
            "opt_out": i_opt[1],
            "ele_P": I_heater,
            "ele_N": -I_heater,
            "dT": -rhs_dT,
        },
        {"opt_in": 0.0, "opt_out": 0.0, "ele_P": 0.0, "ele_N": 0.0, "dT": s.dT},
    )


@component(
    ports=("opt_in", "opt_out", "ele_P", "ele_N"),
    states=("a", "i_out"),
)
def ring_modulator(
    signals: Signals,
    s: States,
    init: dict,
    ng: float = 4.30,
    radius: float = 5.0,
    gamma: float = 0.05,
    alpha_wg: float = 460.0,
    f_resonance: float = 193.4e12,
    f_operating: float = 193.4e12,
    v_to_wr: float = 1.57e10,
    R_pn: float = 500.0,
    C_pn: float = 50e-15,
) -> PhysicsReturn:
    """All-pass ring modulator via temporal coupled-mode theory (C-band).

    Args:
        signals: Port voltages / field amplitudes.
        s: Internal states -- ``a`` (ring energy), ``i_out`` (output constraint).
        init: Dict from ``@ring_modulator.setup`` with ``tau_e`` and ``tau_l``.
        ng: Group index of the ring waveguide.
        radius: Ring radius (um).
        gamma: Power coupling coefficient (0-1).
        alpha_wg: Waveguide propagation loss (1/m, power).
        f_resonance: Resonant frequency of the ring (Hz).
        f_operating: Carrier frequency of the optical signal (Hz).
        v_to_wr: Electro-optic tuning coefficient (rad/s per volt).
        R_pn: Series resistance of the PN junction (ohm).
        C_pn: Junction capacitance of the PN junction (F).
    """
    tau_e = init["tau_e"]
    tau_l = init["tau_l"]

    V_pn = jnp.real(signals.ele_P - signals.ele_N)
    I_pn = V_pn / R_pn

    omega_0 = 2.0 * jnp.pi * f_resonance
    omega_op = 2.0 * jnp.pi * f_operating
    delta_omega = (omega_0 - omega_op) + v_to_wr * V_pn

    kappa = jnp.sqrt(2.0 / tau_e)

    decay = 1.0 / tau_e + 1.0 / tau_l
    rhs_a = (1j * delta_omega - decay) * s.a - 1j * kappa * signals.opt_in

    E_out = signals.opt_in - 1j * kappa * s.a

    return (
        {
            "opt_in": signals.opt_in,
            "opt_out": s.i_out,
            "ele_P": I_pn,
            "ele_N": -I_pn,
            "a": -rhs_a,
            "i_out": signals.opt_out - E_out,
        },
        {
            "opt_in": 0.0,
            "opt_out": 0.0,
            "ele_P": C_pn * V_pn,
            "ele_N": -C_pn * V_pn,
            "a": s.a,
            "i_out": 0.0,
        },
    )


@ring_modulator.setup
def _ring_modulator_setup(
    ng: float = 4.30,
    radius: float = 5.0,
    gamma: float = 0.05,
    alpha_wg: float = 460.0,
) -> dict:
    """Pre-compute photon lifetimes from ring geometry."""
    c0 = 299792458.0
    L = 2.0 * jnp.pi * radius * 1e-6
    vg = c0 / ng
    tau_rt = L * ng / c0
    tau_e = 2.0 * tau_rt / gamma
    alpha_half = alpha_wg / 2.0
    tau_l = jnp.where(alpha_half > 0.0, 1.0 / (vg * alpha_half), 1e30)
    return {"tau_e": tau_e, "tau_l": tau_l}


@component(
    ports=(
        "opt_in",
        "opt_thru",
        "opt_add",
        "opt_drop",
        "ele_P_left",
        "ele_N_left",
        "ele_P_right",
        "ele_N_right",
        "htr_top_P",
        "htr_top_N",
        "htr_bot_P",
        "htr_bot_N",
    ),
    states=("a", "dT", "i_thru", "i_drop"),
)
def ring_modulator_add_drop(
    signals: Signals,
    s: States,
    init: dict,
    ng: float = 4.30,
    radius: float = 5.0,
    gamma1: float = 0.05,
    gamma2: float = 0.05,
    alpha_wg: float = 460.0,
    f_resonance: float = 193.4e12,
    f_operating: float = 193.4e12,
    v_to_wr: float = 1.57e10,
    R_pn: float = 1000.0,
    C_pn: float = 25e-15,
    R_htr: float = 500.0,
    eta_thermo: float = 1.0e11,
    R_th: float = 3000.0,
    C_th: float = 5.0e-9,
) -> PhysicsReturn:
    """Add-drop ring modulator with EO + thermal tuning via t-CMT (C-band).

    Dual-bus ring with separate coupling coefficients for thru and drop
    buses.  Two PN junction sections (left/right) provide electro-optic
    modulation; two doped heater pairs share one thermal node for coarse
    wavelength tuning.

    Each PN section models half the total ring junction: ``R_pn`` and
    ``C_pn`` are per-section values (total ring capacitance = 2 * C_pn).

    Args:
        signals: Port voltages / field amplitudes.
        s: Internal states.
        init: Dict from setup with ``tau_e1``, ``tau_e2``, ``tau_l``.
        ng: Group index of the ring waveguide.
        radius: Ring radius (um).
        gamma1: Power coupling coefficient for the bottom (thru) bus (0-1).
        gamma2: Power coupling coefficient for the top (drop) bus (0-1).
        alpha_wg: Waveguide propagation loss (1/m, power).
        f_resonance: Resonant frequency of the ring (Hz).
        f_operating: Carrier frequency of the optical signal (Hz).
        v_to_wr: Electro-optic tuning coefficient per PN section (rad/s per volt).
        R_pn: Series resistance of each PN section (ohm).
        C_pn: Junction capacitance of each PN section (F).
        R_htr: Resistance of each heater element (ohm).
        eta_thermo: Thermal frequency tuning coefficient (rad/s per K).
        R_th: Thermal resistance, ring-to-ambient (K/W).
        C_th: Thermal capacitance of the heated ring volume (J/K).
    """
    tau_e1 = init["tau_e1"]
    tau_e2 = init["tau_e2"]
    tau_l = init["tau_l"]
    dT = jnp.real(s.dT)

    V_pn_left = jnp.real(signals.ele_P_left - signals.ele_N_left)
    V_pn_right = jnp.real(signals.ele_P_right - signals.ele_N_right)
    I_pn_left = V_pn_left / R_pn
    I_pn_right = V_pn_right / R_pn

    V_htr_top = jnp.real(signals.htr_top_P - signals.htr_top_N)
    V_htr_bot = jnp.real(signals.htr_bot_P - signals.htr_bot_N)
    I_htr_top = V_htr_top / R_htr
    I_htr_bot = V_htr_bot / R_htr
    P_elec = V_htr_top * I_htr_top + V_htr_bot * I_htr_bot

    rhs_dT = (P_elec - dT / R_th) / C_th

    omega_0 = 2.0 * jnp.pi * f_resonance
    omega_op = 2.0 * jnp.pi * f_operating
    delta_omega = (
        (omega_0 - omega_op) + v_to_wr * (V_pn_left + V_pn_right) + eta_thermo * dT
    )

    kappa1 = jnp.sqrt(2.0 / tau_e1)
    kappa2 = jnp.sqrt(2.0 / tau_e2)

    decay = 1.0 / tau_e1 + 1.0 / tau_e2 + 1.0 / tau_l
    rhs_a = (
        (1j * delta_omega - decay) * s.a
        - 1j * kappa1 * signals.opt_in
        - 1j * kappa2 * signals.opt_add
    )

    E_thru = signals.opt_in - 1j * kappa1 * s.a
    E_drop = signals.opt_add - 1j * kappa2 * s.a

    return (
        {
            "opt_in": signals.opt_in,
            "opt_thru": s.i_thru,
            "opt_add": signals.opt_add,
            "opt_drop": s.i_drop,
            "ele_P_left": I_pn_left,
            "ele_N_left": -I_pn_left,
            "ele_P_right": I_pn_right,
            "ele_N_right": -I_pn_right,
            "htr_top_P": I_htr_top,
            "htr_top_N": -I_htr_top,
            "htr_bot_P": I_htr_bot,
            "htr_bot_N": -I_htr_bot,
            "a": -rhs_a,
            "dT": -rhs_dT,
            "i_thru": signals.opt_thru - E_thru,
            "i_drop": signals.opt_drop - E_drop,
        },
        {
            "opt_in": 0.0,
            "opt_thru": 0.0,
            "opt_add": 0.0,
            "opt_drop": 0.0,
            "ele_P_left": C_pn * V_pn_left,
            "ele_N_left": -C_pn * V_pn_left,
            "ele_P_right": C_pn * V_pn_right,
            "ele_N_right": -C_pn * V_pn_right,
            "htr_top_P": 0.0,
            "htr_top_N": 0.0,
            "htr_bot_P": 0.0,
            "htr_bot_N": 0.0,
            "a": s.a,
            "dT": s.dT,
            "i_thru": 0.0,
            "i_drop": 0.0,
        },
    )


@ring_modulator_add_drop.setup
def _ring_modulator_add_drop_setup(
    ng: float = 4.30,
    radius: float = 5.0,
    gamma1: float = 0.05,
    gamma2: float = 0.05,
    alpha_wg: float = 460.0,
) -> dict:
    """Pre-compute photon lifetimes for the add-drop ring."""
    c0 = 299792458.0
    L = 2.0 * jnp.pi * radius * 1e-6
    tau_rt = L * ng / c0
    tau_e1 = 2.0 * tau_rt / gamma1
    tau_e2 = 2.0 * tau_rt / gamma2
    vg = c0 / ng
    alpha_half = alpha_wg / 2.0
    tau_l = jnp.where(alpha_half > 0.0, 1.0 / (vg * alpha_half), 1e30)
    return {"tau_e1": tau_e1, "tau_e2": tau_e2, "tau_l": tau_l}
