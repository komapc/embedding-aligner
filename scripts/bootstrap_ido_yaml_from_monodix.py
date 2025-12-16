#!/usr/bin/env python3
"""
Bootstrap a YAML lexicon for Ido from the existing monolingual dictionary.

This script reads `apertium/apertium-ido/apertium-ido.ido.dix` and extracts
lemma + paradigm information, then writes a YAML file that will become the
single source of truth for generating the monodix in the future.

It does NOT modify any XML files; it only creates/overwrites the YAML.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, Any, List

import xml.etree.ElementTree as ET
import yaml


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Bootstrap Ido YAML lexicon from existing monodix"
    )
    parser.add_argument(
        "--monodix",
        default="../../apertium/apertium-ido/apertium-ido.ido.dix",
        help="Path to existing Ido monodix XML (default: %(default)s)",
    )
    parser.add_argument(
        "--output",
        default="../../apdata/ido_lexicon.yaml",
        help="Path to write YAML lexicon (default: %(default)s)",
    )
    return parser.parse_args()


def build_paradigm_map() -> Dict[str, str]:
    """
    Map pardef names used in monodix to friendly YAML paradigm names.

    These must correspond to real <pardef n="..."> names in the monodix.
    """
    return {
        "o__n": "noun_o",
        "a__adj": "adj_a",
        "e__adv": "adv_e",
        "ar__vblex": "verb_ar",
        "__pr": "prep",
        "__det": "det",
        "__prn": "prn",
        "__cnjcoo": "conj_coo",
        "__cnjsub": "conj_sub",
        "num": "num",
        "num_regex": "num_regex",
    }


def infer_pos_from_par(par_name: str) -> str:
    """Best-effort POS inference from pardef name."""
    if par_name.endswith("__n") or par_name == "o__n":
        return "noun"
    if par_name.endswith("__adj") or par_name == "a__adj":
        return "adj"
    if par_name.endswith("__adv") or par_name == "e__adv":
        return "adv"
    if par_name.endswith("__vblex") or par_name == "ar__vblex":
        return "verb"
    if par_name == "__pr":
        return "prep"
    if par_name == "__det":
        return "det"
    if par_name == "__prn":
        return "prn"
    if par_name == "__cnjcoo":
        return "conj_coo"
    if par_name == "__cnjsub":
        return "conj_sub"
    if par_name.startswith("num"):
        return "num"
    return "other"


def extract_entries(monodix_path: Path) -> List[Dict[str, Any]]:
    tree = ET.parse(monodix_path)
    root = tree.getroot()

    section = root.find(".//section[@id='main']")
    if section is None:
        raise RuntimeError("Could not find <section id='main'> in monodix")

    entries: Dict[str, Dict[str, Any]] = {}

    for e in section.findall("e"):
        lm = e.get("lm")
        if not lm:
            continue

        i_el = e.find("i")
        par_el = e.find("par")
        if i_el is None or par_el is None:
            continue

        surface = (i_el.text or "").strip()
        par_name = par_el.get("n") or ""
        if not surface or not par_name:
            continue

        # Skip numeric regex entry; it's special
        if par_name == "num_regex":
            continue

        pos = infer_pos_from_par(par_name)

        # Deduplicate by lemma; first occurrence wins
        if lm not in entries:
            entries[lm] = {
                "lemma": lm,
                "surface": surface,
                "paradigm": par_name,
                "pos": pos,
            }

    return list(entries.values())


def build_yaml(entries: List[Dict[str, Any]]) -> Dict[str, Any]:
    paradigm_map = build_paradigm_map()

    yaml_paradigms: Dict[str, str] = {}
    yaml_entries: List[Dict[str, Any]] = []

    # Collect only paradigms that actually appear
    for e in entries:
        par_name = e["paradigm"]
        friendly = paradigm_map.get(par_name, par_name)
        yaml_paradigms[friendly] = par_name

        yaml_entries.append(
            {
                "lemma": e["lemma"],
                "pos": e["pos"],
                "paradigm": friendly,
            }
        )

    yaml_root: Dict[str, Any] = {
        "meta": {
            "version": 1,
            "source": "bootstrap_from_monodix",
            "note": "This file was bootstrapped from apertium-ido.ido.dix; edit and extend here.",
        },
        "paradigms": yaml_paradigms,
        "entries": sorted(yaml_entries, key=lambda x: x["lemma"]),
    }
    return yaml_root


def main() -> None:
    args = parse_args()
    monodix_path = Path(args.monodix).resolve()
    out_path = Path(args.output).resolve()

    print(f"Reading monodix from {monodix_path}")
    if not monodix_path.exists():
        raise SystemExit(f"Monodix not found: {monodix_path}")

    entries = extract_entries(monodix_path)
    print(f"Extracted {len(entries)} lemmas from monodix")

    data = build_yaml(entries)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)

    print(f"✅ Wrote YAML lexicon to {out_path}")


if __name__ == "__main__":
    main()



