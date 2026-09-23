"""Validate the standalone BYgram Android XML translation catalog."""

import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parent / "locales"
FILES = ("bygram_strings.xml", "bygram_preferences.xml")
PLACEHOLDER = re.compile(r"%(?:\d+\$)?[-+# 0,(]*\d*(?:\.\d+)?[a-zA-Z%]")


def placeholders(node: ET.Element) -> Counter[str]:
    text = "".join(node.itertext())
    return Counter(token for token in PLACEHOLDER.findall(text) if token != "%%")


def resources(path: Path) -> dict[str, ET.Element]:
    root = ET.parse(path).getroot()
    if root.tag != "resources":
        raise ValueError(f"{path}: expected <resources> root")
    result = {}
    for node in root:
        if node.tag not in ("string", "string-array"):
            continue
        name = node.get("name")
        if not name or name in result:
            raise ValueError(f"{path}: missing or duplicate resource name: {name}")
        result[name] = node
    return result


def validate() -> list[str]:
    errors = []
    english = {name: resources(ROOT / "en" / name) for name in FILES}
    for directory in sorted(ROOT.iterdir()):
        if not directory.is_dir() or directory.name == "en":
            continue
        for filename in FILES:
            path = directory / filename
            if not path.exists():
                continue
            try:
                translated = resources(path)
            except (ET.ParseError, ValueError) as error:
                errors.append(str(error))
                continue
            source = english[filename]
            for name, node in translated.items():
                label = f"{path}: {name}"
                original = source.get(name)
                if original is None:
                    errors.append(f"{label}: unknown resource")
                elif node.tag != original.tag:
                    errors.append(f"{label}: resource type differs from English")
                elif node.tag == "string-array":
                    source_items = original.findall("item")
                    target_items = node.findall("item")
                    if len(target_items) != len(source_items):
                        errors.append(f"{label}: array has {len(target_items)} items; expected {len(source_items)}")
                    for index, (source_item, target_item) in enumerate(zip(source_items, target_items), 1):
                        if placeholders(source_item) != placeholders(target_item):
                            errors.append(f"{label}[{index}]: format placeholders differ from English")
                elif placeholders(original) != placeholders(node):
                    errors.append(f"{label}: format placeholders differ from English")
    return errors


if __name__ == "__main__":
    try:
        problems = validate()
    except (ET.ParseError, ValueError, OSError) as error:
        problems = [str(error)]
    if problems:
        print("\n".join(problems), file=sys.stderr)
        raise SystemExit(1)
    print("BYgram translations: valid")
