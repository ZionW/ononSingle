#!/usr/bin/env python3
"""Build a one-way-contour probe modeled after Rhino's bundled SLF fonts."""

from __future__ import annotations

import argparse
import math
from pathlib import Path

from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont

from build_text_compatible import FlattenPen, set_name


def distance(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def centerline_half(path):
    """Remove the mirrored return half while preserving real closed loops."""
    if len(path) < 3:
        return path
    half = (len(path) + 1) // 2
    forward = path[:half]
    reverse = list(reversed(path[half:]))
    if abs(len(forward) - len(reverse)) > 1 or not reverse:
        return path
    errors = [distance(a, b) for a, b in zip(forward, reverse)]
    if errors and max(errors) <= 0.75:
        return forward
    return path


def collapse_nearly_straight(path, tolerance=2.5):
    """Restore two-point straight contours like Rhino's bundled SLF fonts."""
    if len(path) < 3:
        return path
    start, end = path[0], path[-1]
    dx, dy = end[0] - start[0], end[1] - start[1]
    length = math.hypot(dx, dy)
    if not length:
        return path
    deviation = max(
        abs(dx * (point[1] - start[1]) - dy * (point[0] - start[0])) / length
        for point in path
    )
    return [start, end] if deviation <= tolerance else path


def single_stroke_glyph(glyph_set, glyph_name):
    flatten = FlattenPen(glyph_set)
    glyph_set[glyph_name].draw(flatten)
    flatten._finish()
    pen = TTGlyphPen(None)
    for path in flatten.paths:
        path = collapse_nearly_straight(centerline_half(path))
        cleaned = []
        for x, y in path:
            point = (round(x), round(y))
            if not cleaned or point != cleaned[-1]:
                cleaned.append(point)
        if len(cleaned) < 2:
            continue
        pen.moveTo(cleaned[0])
        for point in cleaned[1:]:
            pen.lineTo(point)
        # TrueType contours must close. Rhino's recognized single-stroke path
        # removes this implicit closing segment when text is exploded.
        pen.closePath()
    return pen.glyph()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    font = TTFont(args.input)
    glyph_set = font.getGlyphSet()
    glyph_order = font.getGlyphOrder()
    replacements = {}
    for index, glyph_name in enumerate(glyph_order, 1):
        replacements[glyph_name] = single_stroke_glyph(glyph_set, glyph_name)
        if index % 1000 == 0:
            print(f"processed {index}/{len(glyph_order)}", flush=True)
    for glyph_name, glyph in replacements.items():
        font["glyf"][glyph_name] = glyph

    names = {
        1: "ononSingle Rhino Experimental",
        3: "ononSingleRhinoExperimental-Regular-0.1",
        4: "ononSingle Rhino Experimental Regular",
        5: "Version 0.1; Rhino single-stroke recognition probe",
        6: "ononSingleRhinoExperimental-Regular",
        10: "Engraving: Singlestroke",
        16: "ononSingle Rhino Experimental",
        17: "Regular",
    }
    for name_id, value in names.items():
        set_name(font, name_id, value)
    font["head"].fontRevision = 0.1
    font["head"].lowestRecPPEM = 6
    font["OS/2"].fsType = 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    font.save(args.output)
    print(f"saved {args.output}")


if __name__ == "__main__":
    main()
