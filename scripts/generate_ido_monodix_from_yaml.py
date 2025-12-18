#!/usr/bin/env python3
"""
Generate the Ido monolingual dictionary (apertium-ido.ido.dix) from a YAML lexicon.

Workflow:
- YAML (`apdata/ido_lexicon.yaml`) is the source of truth for lemmas and paradigms.
- This script:
  - Reads the existing monodix XML.
  - Removes previously auto-generated entries (marked with gen="yaml").
  - Appends fresh entries based on the YAML file.

It does NOT touch pardefs or sdefs; it only manages <e> entries in <section id="main">.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, Any, List

import xml.etree.ElementTree as ET
import yaml


AUTOGEN_ATTR = "gen"
AUTOGEN_VALUE = "yaml"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate apertium-ido.ido.dix <e> entries from YAML lexicon"
    )
    parser.add_argument(
        "--yaml",
        default="../../apdata/ido_lexicon.yaml",
        help="Path to YAML lexicon (default: %(default)s)",
    )
    parser.add_argument(
        "--monodix",
        default="../../apertium/apertium-ido/apertium-ido.ido.dix",
        help="Path to existing monodix XML to update (default: %(default)s)",
    )
    return parser.parse_args()


def load_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise SystemExit(f"YAML lexicon not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise SystemExit("YAML root must be a mapping")
    return data


def extract_stem(lemma: str, pardef: str) -> str:
    """
    Extract the stem from a lemma by removing the paradigm suffix.
    
    Paradigm suffixes:
    - o__n: suffix "o" (e.g., "acero" -> "acer")
    - a__adj: suffix "a" (e.g., "bona" -> "bon")
    - e__adv: suffix "e" (e.g., "bone" -> "bon")
    - ar__vblex: suffix "ar" (e.g., "irar" -> "ir")
    - Others: no suffix (use full lemma)
    """
    suffix_map = {
        "o__n": "o",
        "a__adj": "a",
        "e__adv": "e",
        "ar__vblex": "ar",
    }
    
    suffix = suffix_map.get(pardef, "")
    if suffix and lemma.endswith(suffix):
        return lemma[:-len(suffix)]
    return lemma


def generate_entries_from_yaml(data: Dict[str, Any]) -> List[ET.Element]:
    paradigms: Dict[str, str] = data.get("paradigms", {}) or {}
    entries_cfg: List[Dict[str, Any]] = data.get("entries", []) or []

    entries: List[ET.Element] = []

    for item in entries_cfg:
        lemma = item.get("lemma")
        paradigm_name = item.get("paradigm")
        if not lemma or not paradigm_name:
            continue

        pardef = paradigms.get(paradigm_name, paradigm_name)
        stem = extract_stem(lemma, pardef)

        e_el = ET.Element("e")
        e_el.set(AUTOGEN_ATTR, AUTOGEN_VALUE)
        e_el.set("lm", lemma)

        i_el = ET.SubElement(e_el, "i")
        i_el.text = stem

        par_el = ET.SubElement(e_el, "par")
        par_el.set("n", pardef)

        entries.append(e_el)

    return entries


def update_monodix(monodix_path: Path, new_entries: List[ET.Element]) -> None:
    tree = ET.parse(monodix_path)
    root = tree.getroot()

    section = root.find(".//section[@id='main']")
    if section is None:
        raise SystemExit("Could not find <section id='main'> in monodix")

    # Remove previous auto-generated entries
    to_remove: List[ET.Element] = []
    for e in section.findall("e"):
        if e.get(AUTOGEN_ATTR) == AUTOGEN_VALUE:
            to_remove.append(e)
    for e in to_remove:
        section.remove(e)

    # Append new auto-generated entries at the end of the section
    for e in new_entries:
        section.append(e)

    # Write back
    tree.write(monodix_path, encoding="UTF-8", xml_declaration=True)


def main() -> None:
    args = parse_args()
    yaml_path = Path(args.yaml).resolve()
    monodix_path = Path(args.monodix).resolve()

    print(f"Loading YAML lexicon from {yaml_path}")
    data = load_yaml(yaml_path)

    print("Generating monodix entries from YAML...")
    new_entries = generate_entries_from_yaml(data)
    print(f"  Entries to generate: {len(new_entries)}")

    print(f"Updating monodix at {monodix_path}")
    if not monodix_path.exists():
        raise SystemExit(f"Monodix not found: {monodix_path}")

    update_monodix(monodix_path, new_entries)
    print("✅ Monodix updated with YAML-generated entries")


if __name__ == "__main__":
    main()



