"""Tests for route_bundle_3d: registration, routing, and connection by abutment."""

from __future__ import annotations

import gdsfactory as gf
import pytest
from doroutes.multilayer.port_keepouts import PortStackKeepouts
from kfactory import kdb

import gpdk
import gpdk.routing_3d as routing_3d
from gpdk.routing_3d import route_bundle_3d


def _pads(
    positions: list[tuple[float, float]],
) -> tuple[gf.Component, list[gf.ComponentReference]]:
    gpdk.PDK.activate()
    c = gf.Component()
    refs = []
    for x, y in positions:
        ref = c << gf.c.pad(size=(80, 80))
        ref.dmove((x, y))
        refs.append(ref)
    return c, refs


def _route_cells(c: gf.Component) -> list[gf.ComponentReference]:
    return [inst for inst in c.insts if "electrical_route" in inst.cell.name]


def _abuts(c: gf.Component, device_port: gf.Port) -> bool:
    """True if some route cell has a port on ``device_port``, facing it."""
    for inst in _route_cells(c):
        for p in inst.ports:
            if (
                p.dcenter == device_port.dcenter
                and (p.orientation - device_port.orientation) % 360 == 180
            ):
                return True
    return False


def test_route_bundle_3d_registered_in_pdk():
    """route_bundle_3d is registered as a PDK routing strategy."""
    assert "route_bundle_3d" in gpdk.PDK.routing_strategies
    assert callable(gpdk.PDK.routing_strategies["route_bundle_3d"])


def test_route_bundle_3d_single_net():
    """A single net routes with one route cell abutting both pads."""
    c, (a, b) = _pads([(0, 0), (400, 0)])
    result = route_bundle_3d(
        c, [a.ports["e4"]], [b.ports["e2"]], grid_unit=10.0, clearance=5.0
    )
    assert result == []
    assert len(_route_cells(c)) == 1
    assert _abuts(c, a.ports["e4"])
    assert _abuts(c, b.ports["e2"])


def test_route_bundle_3d_two_nets():
    """Two nets route independently and abut their pads."""
    c, (a1, a2, b1, b2) = _pads([(0, 0), (0, 200), (400, 0), (400, 200)])
    route_bundle_3d(
        c,
        [a1.ports["e4"], a2.ports["e4"]],
        [b1.ports["e2"], b2.ports["e2"]],
        grid_unit=10.0,
        clearance=5.0,
        require_all=True,
    )
    assert len(_route_cells(c)) == 2
    for port in (a1.ports["e4"], a2.ports["e4"], b1.ports["e2"], b2.ports["e2"]):
        assert _abuts(c, port)


def test_route_bundle_3d_rejects_mismatched_bundles():
    """Mismatched bundle lengths raise ValueError."""
    c, (a, b) = _pads([(0, 0), (400, 0)])
    with pytest.raises(ValueError, match="equal length"):
        route_bundle_3d(c, [a.ports["e4"]], [], grid_unit=10.0)


def test_route_bundle_3d_empty_bundle_is_noop():
    """An empty bundle is a no-op."""
    c, _ = _pads([(0, 0)])
    assert route_bundle_3d(c, [], []) == []
    assert not _route_cells(c)


@pytest.mark.parametrize("width,length", [(11.0, 11.0), (15.0, 19.0)])
def test_routing_via_enclosure_matches_the_factory_metal(width, length):
    """The via metal matches the factory width/length plus enclosure."""
    gpdk.PDK.activate()
    via = routing_3d.via_m2_m3(width=width, length=length)
    extra = 2 * routing_3d.GPDK_CONFIG.via_metal_enclosure_add
    for spec in routing_3d.GPDK_CONFIG.metal_layers:
        metal = kdb.Region(via.begin_shapes_rec(via.kcl.layer(spec.layer_tuple)))
        box = metal.bbox().to_dtype(via.kcl.dbu)
        assert box.width() == pytest.approx(width + extra)
        assert box.height() == pytest.approx(length + extra)


def test_full_pdk_switch_export_keeps_routes_out_from_under_pads(monkeypatch, tmp_path):
    """Exercise the actual sample and PDK config, including exported-metal LVS."""
    from gpdk.samples.test_1x16_switch import switch_nxn_with_fiber_array

    gpdk.PDK.activate()
    endpoints = {}
    widths = []
    original = routing_3d.route_batch_multilayer

    def capture(component, **kwargs):
        widths.append(kwargs["width"])
        for net in kwargs["nets"]:
            pins = []
            for port in (net.start, net.stop):
                key = tuple(round(v / component.kcl.dbu) for v in port.dcenter)
                geom = kwargs["geom_cache"][key]
                pins.append((geom.layer_tuple, geom.dev_center_dbu))
            endpoints[net.name] = pins
        result = original(component, **kwargs)
        assert result[1] == []
        assert set(result[0]) == set(endpoints)
        return result

    monkeypatch.setattr(routing_3d, "route_batch_multilayer", capture)
    component = switch_nxn_with_fiber_array.__wrapped__(noutputs=16)
    assert len(endpoints) == 30
    assert len(PortStackKeepouts.capture(component).footprints) == 30
    path = tmp_path / "photonics_full_switch_1x16.gds"
    component.write_gds(path)
    layout = kdb.Layout()
    layout.read(str(path))
    top = layout.top_cell()
    pads = kdb.Region()
    route_refs = []
    for ref in top.each_inst():
        if "electrical_route" in ref.cell.name:
            route_refs.append(ref)
        else:
            for polygon in (
                kdb.Region(ref.cell.begin_shapes_rec(layout.layer(49, 0)))
                .transformed(ref.cplx_trans)
                .each()
            ):
                if polygon.bbox().width() * layout.dbu >= 99:
                    pads.insert(polygon)
    assert pads.count() == 30
    assert len(route_refs) == 30
    # The reserved straight approach below the pad row must maintain the same
    # cross-section: no width step or lateral shift along the final 30 um.
    assert len(set(widths)) == 1
    pad_bottom = pads.bbox().bottom
    approach_sections = [1.0, 15.0, 29.0]
    short_vertical_m2_sections = 0
    for ref in route_refs:
        metal = kdb.Region(ref.cell.begin_shapes_rec(layout.layer(45, 0))).transformed(
            ref.cplx_trans
        )
        assert (metal & pads.sized(round(5.0 / layout.dbu))).is_empty(), ref.cell.name
        m3 = kdb.Region(ref.cell.begin_shapes_rec(layout.layer(49, 0))).transformed(
            ref.cplx_trans
        )
        sections = []
        for distance in approach_sections:
            y = pad_bottom - round(distance / layout.dbu)
            slice_box = kdb.Box(pads.bbox().left, y, pads.bbox().right, y + 1)
            section = (m3 & kdb.Region(slice_box)).bbox()
            assert section.width() * layout.dbu == pytest.approx(widths[0]), (
                ref.cell.name,
                distance,
                section,
            )
            sections.append((section.left, section.right))
        assert len(set(sections)) == 1, ref.cell.name
        # Check the merged straight interior of vertical M2 pieces, including
        # short jogs, then check individual long rectangles on both metals.
        for piece in ref.cell.each_inst():
            m2_piece = kdb.Region(
                piece.cell.begin_shapes_rec(layout.layer(45, 0))
            ).transformed(ref.cplx_trans * piece.cplx_trans)
            box_dbu = m2_piece.bbox()
            width_dbu = round(widths[0] / layout.dbu)
            # Router versions use different cell names; identify the straight
            # by its metal dimensions so short-jog coverage cannot be skipped.
            if box_dbu.width() == width_dbu and box_dbu.height() > width_dbu:
                # Measure merged metal, so offset repair patches cannot hide
                # behind the correct width of the original vertical segment.
                section_bottom = box_dbu.bottom + width_dbu // 2
                section_top = box_dbu.top - width_dbu // 2
                band = kdb.Region(
                    kdb.Box(
                        box_dbu.left - width_dbu,
                        section_bottom,
                        box_dbu.right + width_dbu,
                        section_top,
                    )
                )
                expected_section = kdb.Region(
                    kdb.Box(
                        box_dbu.left,
                        section_bottom,
                        box_dbu.right,
                        section_top,
                    )
                )
                assert ((metal & band) ^ expected_section).is_empty(), (
                    ref.cell.name,
                    piece.cell.name,
                    box_dbu,
                )
                if box_dbu.height() < 2 * width_dbu:
                    short_vertical_m2_sections += 1
            for layer in ((45, 0), (49, 0)):
                region = kdb.Region(piece.cell.begin_shapes_rec(layout.layer(*layer)))
                box = region.bbox().to_dtype(layout.dbu)
                if (
                    not region.is_empty()
                    and max(box.width(), box.height()) > 2 * widths[0]
                ):
                    assert min(box.width(), box.height()) == pytest.approx(widths[0]), (
                        ref.cell.name,
                        piece.cell.name,
                        layer,
                        box,
                    )

    assert short_vertical_m2_sections > 0

    # Compare flattened conductive nets with the terminal-pair schematic,
    # without retaining route/via cell hierarchy as schematic devices.
    top.flatten(-1, True)
    extractor = kdb.LayoutToNetlist(kdb.RecursiveShapeIterator(layout, top, []))
    metal_layers = ((45, 0), (43, 0), (49, 0))
    regions = {
        layer: extractor.make_layer(layout.layer(*layer), str(layer))
        for layer in metal_layers
    }
    for region in regions.values():
        extractor.connect(region)
    extractor.connect(regions[(45, 0)], regions[(43, 0)])
    extractor.connect(regions[(43, 0)], regions[(49, 0)])
    extractor.extract_netlist()
    actual = extractor.netlist().circuit_by_name(top.name)
    expected = kdb.Netlist()
    schematic = kdb.Circuit()
    schematic.name = top.name
    expected.add(schematic)
    for name, pins in endpoints.items():
        reference_net = schematic.create_net(name)
        for index, (layer, xy) in enumerate(pins):
            net = extractor.probe_net(regions[layer], kdb.Point(*xy))
            assert net is not None
            pin_name = f"{name}_{index}"
            actual.connect_pin(actual.create_pin(pin_name), net)
            schematic.connect_pin(schematic.create_pin(pin_name), reference_net)
    actual.purge_nets()
    assert kdb.NetlistComparer().compare(extractor.netlist(), expected)
