import gdsfactory as gf


@gf.cell
def gc(taper_length: float = 36.6) -> gf.Component:
    c = gf.c.grating_coupler_elliptical(taper_length=taper_length)
    return c
