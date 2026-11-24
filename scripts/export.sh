#!/usr/bin/env bash
# Export schematic PDF, layout PDF, 3D STEP and 3D renders into exports/.
# Used by .github/workflows/export.yml; also runs locally:
#   scripts/export.sh
#   KICAD_CLI="flatpak run --filesystem=$PWD --command=kicad-cli org.kicad.KiCad" \
#   KICAD_PYTHON="flatpak run --filesystem=$PWD --command=python3 org.kicad.KiCad" scripts/export.sh
set -euo pipefail
cd "$(dirname "$0")/.."

KICAD_CLI=${KICAD_CLI:-kicad-cli}
KICAD_PYTHON=${KICAD_PYTHON:-python3}
# project name = the .kicad_pro in the repo root
NAME=$(basename "$(ls *.kicad_pro | head -1)" .kicad_pro)
# copper layers present on this board (2- or 4-layer)
INNER=$(grep -oE '\([0-9]+ "In[0-9]+\.Cu"' "$NAME.kicad_pcb" | grep -oE 'In[0-9]+\.Cu' | paste -sd, - || true)
COPPER="F.Cu${INNER:+,$INNER},B.Cu"
OUT=exports
# temporary board next to the real one so ${KIPRJMOD} model paths still resolve
ONBOARD=_ci_onboard.kicad_pcb
# STEP file name suffix per board piece, largest first (pieces are separated at
# the mouse-bite tabs); extra pieces get _part<N>
PIECE_SUFFIXES=("" "_sensor")
trap 'rm -f "$ONBOARD" _ci_onboard.kicad_prl _ci_onboard.kicad_pro _ci_piece*' EXIT

mkdir -p "$OUT"

echo "== Schematic PDF (root sheet + any sub-sheets)"
$KICAD_CLI sch export pdf "$NAME.kicad_sch" --output "$OUT/${NAME}_schematic.pdf"

echo "== Layout PDF (one page per layer)"
$KICAD_CLI pcb export pdf "$NAME.kicad_pcb" --output "$OUT/${NAME}_layout.pdf" \
  --mode-multipage \
  --layers F.SilkS,$COPPER,B.SilkS,F.Fab,B.Fab \
  --common-layers Edge.Cuts \
  --include-border-title

echo "== Board copy without the parts parked outside the outline"
$KICAD_PYTHON scripts/onboard_board.py "$NAME.kicad_pcb" "$ONBOARD"
cp "$NAME.kicad_pro" _ci_onboard.kicad_pro

echo "== 3D STEP, one file per board (split at the mouse-bite tabs)"
rm -f _ci_piece*
$KICAD_PYTHON scripts/split_board.py "$NAME.kicad_pcb" _ci_piece > /dev/null
k=0
for piece in $(ls _ci_piece*.kicad_pcb | sort -V); do
  suffix=${PIECE_SUFFIXES[$k]-_part$k}
  cp "$NAME.kicad_pro" "${piece%.kicad_pcb}.kicad_pro"
  $KICAD_CLI pcb export step "$piece" --output "$OUT/$NAME$suffix.step" --force --subst-models
  k=$((k + 1))
done

echo "== 3D renders"
for side in top bottom; do
  $KICAD_CLI pcb render "$ONBOARD" --output "$OUT/${NAME}_3d_${side}.png" \
    --side "$side" --rotate '-35,0,25' --perspective --quality high \
    --background opaque --width 1600 --height 1000
done

ls -la "$OUT"
