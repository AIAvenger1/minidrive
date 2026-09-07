#!/usr/bin/env bash
# Build DOCX + PDF from a Markdown report.
#   tools/build-report.sh docs/reports/stage1-uml.md
# Output goes next to the source: stage1-uml.docx, stage1-uml.pdf
set -euo pipefail
SRC="${1:?usage: build-report.sh <report.md>}"
DIR="$(cd "$(dirname "$SRC")" && pwd)"
BASE="$(basename "${SRC%.md}")"
cd "$DIR"

COMMON=(--from markdown+smart-implicit_figures --toc --toc-depth=2 --number-sections -V lang=uk --resource-path=".:..:../uml/img")

echo "[report] DOCX → $DIR/$BASE.docx"
pandoc "$BASE.md" "${COMMON[@]}" -o "$BASE.docx"

echo "[report] PDF  → $DIR/$BASE.pdf"
pandoc "$BASE.md" "${COMMON[@]}" \
  --pdf-engine=xelatex \
  -V mainfont="Times New Roman" -V sansfont="Arial" -V monofont="Menlo" \
  -V fontsize=12pt -V geometry:margin=2cm -V linestretch=1.15 \
  -V colorlinks=true \
  -o "$BASE.pdf"

ls -la "$BASE.docx" "$BASE.pdf"
