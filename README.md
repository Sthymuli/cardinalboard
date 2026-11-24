# Sthymuli-cardinalboard
companion boardto the sthymuli motherboard

## 3D view

| Top | Bottom |
|---|---|
| ![Top side 3D render](exports/Sthymuli-cardinalboard_3d_top.png) | ![Bottom side 3D render](exports/Sthymuli-cardinalboard_3d_bottom.png) |

## Exports

Regenerated automatically by the [export workflow](.github/workflows/export.yml) on every push to `main` that changes the design:

* [Schematic (PDF)](exports/Sthymuli-cardinalboard_schematic.pdf)
* [Layout (PDF, one page per layer)](exports/Sthymuli-cardinalboard_layout.pdf)
* [3D model (STEP)](exports/Sthymuli-cardinalboard.step), with only the parts placed on the board
* [3D render, top](exports/Sthymuli-cardinalboard_3d_top.png) / [bottom](exports/Sthymuli-cardinalboard_3d_bottom.png)

To run the same export locally: `scripts/export.sh` (see the comment at the top of the script for the Flatpak KiCad variant).
