#!/usr/bin/env python3
"""Build a separate, thin-outline font for standard filled-text renderers."""

from __future__ import annotations

import argparse
import math
from pathlib import Path

from fontTools.pens.basePen import BasePen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont
from shapely.geometry import LineString, MultiPolygon, Polygon
from shapely.geometry.polygon import orient
from shapely.ops import unary_union


class FlattenPen(BasePen):
    """Flatten TrueType curves into line strings suitable for buffering."""

    def __init__(self, glyph_set, steps: int = 6):
        super().__init__(glyph_set)
        self.steps = steps
        self.paths: list[list[tuple[float, float]]] = []
        self.path: list[tuple[float, float]] | None = None

    def _moveTo(self, point):
        self._finish()
        self.path = [point]

    def _lineTo(self, point):
        if self.path is not None and point != self.path[-1]:
            self.path.append(point)

    def _qCurveToOne(self, control, end):
        start = self._getCurrentPoint()
        for index in range(1, self.steps + 1):
            t = index / self.steps
            mt = 1.0 - t
            point = (
                mt * mt * start[0] + 2 * mt * t * control[0] + t * t * end[0],
                mt * mt * start[1] + 2 * mt * t * control[1] + t * t * end[1],
            )
            self._lineTo(point)

    def _curveToOne(self, control1, control2, end):
        start = self._getCurrentPoint()
        for index in range(1, self.steps + 1):
            t = index / self.steps
            mt = 1.0 - t
            point = (
                mt**3 * start[0] + 3 * mt * mt * t * control1[0]
                + 3 * mt * t * t * control2[0] + t**3 * end[0],
                mt**3 * start[1] + 3 * mt * mt * t * control1[1]
                + 3 * mt * t * t * control2[1] + t**3 * end[1],
            )
            self._lineTo(point)

    def _closePath(self):
        self._finish()

    def _endPath(self):
        self._finish()

    def _finish(self):
        if self.path and len(self.path) >= 2:
            self.paths.append(self.path)
        self.path = None


def polygons(geometry):
    if isinstance(geometry, Polygon):
        yield geometry
    elif isinstance(geometry, MultiPolygon):
        yield from geometry.geoms
    elif hasattr(geometry, "geoms"):
        for child in geometry.geoms:
            yield from polygons(child)


def thin_outline_glyph(glyph_set, glyph_name: str, stroke_width: float):
    flatten = FlattenPen(glyph_set)
    glyph_set[glyph_name].draw(flatten)
    flatten._finish()
    lines = [LineString(path) for path in flatten.paths if len(path) >= 2]
    if not lines:
        return TTGlyphPen(None).glyph()

    shape = unary_union(lines).buffer(
        stroke_width / 2,
        quad_segs=2,
        cap_style="round",
        join_style="round",
    )
    pen = TTGlyphPen(None)
    for polygon in polygons(shape):
        # Boolean unions can leave microscopic slivers or holes. They collapse
        # to one- or two-point contours after font-unit rounding and confuse
        # some filled-text renderers, so omit them before writing the glyph.
        if polygon.area < 4.0:
            continue
        # TrueType convention: outer rings clockwise, holes counter-clockwise.
        polygon = orient(polygon, sign=-1.0)
        rings = [polygon.exterior, *polygon.interiors]
        for ring in rings:
            points = [(round(x), round(y)) for x, y in ring.coords[:-1]]
            cleaned = []
            for point in points:
                if not cleaned or point != cleaned[-1]:
                    cleaned.append(point)
            if len(cleaned) < 3:
                continue
            area2 = sum(
                cleaned[index][0] * cleaned[(index + 1) % len(cleaned)][1]
                - cleaned[(index + 1) % len(cleaned)][0] * cleaned[index][1]
                for index in range(len(cleaned))
            )
            if area2 == 0:
                continue
            pen.moveTo(cleaned[0])
            for point in cleaned[1:]:
                pen.lineTo(point)
            pen.closePath()
    return pen.glyph()


def set_name(font, name_id: int, value: str):
    font["name"].removeNames(nameID=name_id)
    font["name"].setName(value, name_id, 3, 1, 0x0409)
    font["name"].setName(value, name_id, 1, 0, 0)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--profile", choices=("v1", "v2"), default="v1")
    parser.add_argument("--stroke-width", type=float)
    args = parser.parse_args()

    if args.profile == "v2":
        stroke_width = args.stroke_width or 24.0
        names = {
            1: "ononSingleText",
            3: "ononSingleText-Regular-0.2",
            4: "ononSingleText Regular",
            5: "Version 0.2; Rhino Text thin-outline compatibility build",
            6: "ononSingleText-Regular",
            10: (
                "Thin-outline companion to ononSingle for Rhino Text and other "
                "standard filled-text renderers. Derived from LINE Seed TW "
                "Thin 1.400."
            ),
            16: "ononSingleText",
            17: "Regular",
        }
        revision = 0.2
    else:
        stroke_width = args.stroke_width or 12.0
        names = {
            1: "ononSingle Text Experimental",
            3: "ononSingleTextExperimental-Regular-0.1",
            4: "ononSingle Text Experimental Regular",
            5: "Version 0.1; experimental thin-outline text-compatible build",
            6: "ononSingleTextExperimental-Regular",
            10: (
                "Experimental thin-outline companion to ononSingle for standard "
                "filled-text renderers. Derived from LINE Seed TW Thin 1.400."
            ),
            16: "ononSingle Text Experimental",
            17: "Regular",
        }
        revision = 0.1

    font = TTFont(args.input)
    glyph_set = font.getGlyphSet()
    glyph_order = font.getGlyphOrder()
    replacements = {}
    for index, glyph_name in enumerate(glyph_order, 1):
        replacements[glyph_name] = thin_outline_glyph(
            glyph_set, glyph_name, stroke_width
        )
        if index % 1000 == 0:
            print(f"processed {index}/{len(glyph_order)}", flush=True)

    for glyph_name, glyph in replacements.items():
        font["glyf"][glyph_name] = glyph

    for name_id, value in names.items():
        set_name(font, name_id, value)
    font["head"].fontRevision = revision
    font["OS/2"].fsType = 0
    font["OS/2"].achVendID = "ZION"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    font.save(args.output)
    print(f"saved {args.output}")


if __name__ == "__main__":
    main()
