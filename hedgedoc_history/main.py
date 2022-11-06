from __future__ import annotations
import collections

import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Any
from uuid import uuid4
import yaml

import attrs
from attrs_strict import type_validator
import cattrs
from loguru import logger as log

PROG = "/home/cny/.local/bin/hedgedoc"
MULTI_TAG_REGEX = re.compile(r"^[#]\((.*)\)$")
STRUCTURE_PATH = Path(__file__).parent.parent / "hd.structure.yaml"
REFERENCE_ID = "l1U9OB_cQJK0G2mjGa12Bg"


@attrs.define
class Config:
    """Hedgedoc config."""

    server: str = attrs.field(validator=type_validator(empty_ok=False))
    user: str = attrs.field(validator=type_validator(empty_ok=False))


@attrs.define
class HistoryEntry:
    time: int
    id: str
    text: str = ""
    tags: list[str] = attrs.field(factory=list)
    pinned: bool = False

    def from_json(o: bytes | str) -> list[HistoryEntry]:
        dct = json.loads(o)
        return cattrs.structure(dct["history"], list[HistoryEntry])


def get_config() -> Config:
    out = run_command([PROG, "profile"])
    config = parse_profile(out.decode("utf-8"))
    return config


def run_command(argv: list[str]) -> bytes | None:
    log.info(f"Running command: {argv}")
    proc = subprocess.Popen(
        args=argv,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    stdout, stderr = proc.communicate(timeout=15)
    if proc.returncode != 0:
        log.error(f"Failed to execute: {argv}")
        log.error(f"stderr: {stderr}")
        sys.exit(1)

    return stdout


def login(username: str, password: str) -> None:
    log.debug("Logging in")
    run_command([PROG, "login", "--email", username, password])
    log.trace("Done")


def parse_profile(o: bytes) -> Config:
    server, user = None, None
    for line in o.splitlines(keepends=False):
        if line.startswith("HEDGEDOC_SERVER="):
            server = line.split("=", 1)[1].strip()
        elif line.startswith("USER_NAME="):
            user = line.split("=", 1)[1].strip()
    return Config(server=server, user=user)


def get_history() -> list[HistoryEntry]:
    out = run_command([PROG, "history", "--json"])

    if out is None:
        log.error("Failed to get history")
        sys.exit(0)

    history = HistoryEntry.from_json(out)
    return history


@attrs.define
class StructureConfig:
    """Structured config for creating structured history."""

    capitalize: bool = False
    items: list[StructureItem] = attrs.field(factory=list)
    misc: list[StructureItem] = attrs.field(factory=list)


@attrs.define
class StructureItem:
    """Structure item."""

    name: str
    tags: list[str]
    level: int = 0
    id: str = attrs.field(factory=lambda: str(uuid4()))
    parent: StructureItem | None = attrs.field(default=None, repr=False)


def structure_history(cfg: Config, structure: Path) -> StructureConfig:
    struct_cfg = parse_structure_config(structure)
    return struct_cfg


def parse_structure_config(path: Path) -> StructureConfig:
    tag_dct = yaml.safe_load(path.read_text())["tags"]
    cap = tag_dct.get("capitalize", False)
    items = parse_levels(tag_dct["levels"], level=0, items=[])
    cfg = StructureConfig(capitalize=cap, items=items)
    return cfg


def parse_levels(
    _o: Any,
    level: int = 0,
    items: list[StructureItem] = [],
    parent: StructureItem | None = None,
) -> list[StructureItem]:
    log.trace(f"{level}: {_o}, type={type(_o)}")

    if isinstance(_o, str):
        tags = _tags_from_key(_o)
        name = _name_from_tags(tags)
        _item = StructureItem(name=name, tags=tags, level=level, parent=parent)
        items.append(_item)
        return items

    if isinstance(_o, dict):
        explicit = False
        e_keys = ["name", "tags"]
        for key in _o.keys():
            if key in e_keys:
                e_keys.remove(key)

            if len(e_keys) != 2:
                explicit = True
                break

        if explicit is True:
            tags = _o.get("tags")
            if isinstance(tags, str):
                tags = _tags_from_key(tags)
            elif isinstance(tags, list):
                tags = tags
            else:
                raise ValueError(f"Invalid tags: {tags}")

            _items = _o.get("children", [])
            name = _o.get("name", _name_from_tags(tags))
            items.append(StructureItem(name=name, tags=tags, level=level, parent=parent))
            return parse_levels(_items, level=level + 1, items=items, parent=items[-1])

        for key, value in _o.items():
            tags = _tags_from_key(key)
            name = _name_from_tags(tags)
            _item = StructureItem(name=name, tags=tags, level=level, parent=parent)
            items.append(_item)
            if not value:
                continue

            parse_levels(value, level=level + 1, items=items, parent=_item)

    if isinstance(_o, list):
        for it in _o:
            parse_levels(it, level=level, items=items, parent=parent)
    return items


def _tags_from_key(key: str) -> list[str]:
    if m := MULTI_TAG_REGEX.search(key):
        tags = m.group(1).split("|")
    else:
        tags = [key]
    return tags


def _name_from_tags(tags: list[str]) -> str:
    return ", ".join(tags)


@attrs.define
class Section:
    """Section."""

    name: str
    level: int
    items: list[HistoryEntry]


def generate_markdown(cfg: Config, structure: Path, history: list[HistoryEntry]) -> str:
    lines = []
    uncategorized: list[HistoryEntry] = []
    sections: list[Section] = []
    struct = structure_history(cfg, structure)

    # Group everything by tags
    used_ids: dict[str, list[StructureItem]] = collections.defaultdict(list)
    nonused: list[HistoryEntry] = history.copy()
    for i, _struct in enumerate(struct.items):
        _s_items: list[str] = []
        for entry in history:
            for etag in entry.tags:
                if etag not in _struct.tags:
                    continue

                _s_items.append(_line_from_entry(cfg, entry))
                used_ids[entry.id].append(_struct)
                if entry in nonused:
                    nonused.remove(entry)

                break

        _section = Section(name=_struct.name, level=_struct.level, items=_s_items)
        sections.append(_section)

    # Filter out entries that are already used.
    for i, curr_s in enumerate(sections[1:], start=1):
        for j, prev_s in enumerate(sections[:i]):
            log.trace(f"{i}.{j}: c:{curr_s.name} -> p:{prev_s.name}")
            for p_it in prev_s.items:
                log.trace(f" : p:{p_it} in c:{curr_s.items}?")
                if p_it in curr_s.items:
                    log.trace(f"Duplicate: {p_it}")
                    prev_s.items.remove(p_it)

    for entry in history:
        if entry.id not in used_ids:
            uncategorized.append(_line_from_entry(cfg, entry))

    if uncategorized:
        _section = Section(name="Uncategorized", level=0, items=uncategorized)
        sections.append(_section)

    # Generate markdown
    lines.append("# History Reference\n")
    for prev_s in sections:
        lines.append(f"{'#' * (prev_s.level + 2)} {prev_s.name}\n")
        if prev_s.items:
            lines.extend(prev_s.items)
            lines.append("\n")

    return "\n".join(lines)


def _line_from_entry(cfg: Config, entry: HistoryEntry) -> str:
    line = f"- [{entry.text}]({cfg.server}/{entry.id})"
    if entry.tags:
        line += f" ({', '.join(entry.tags)})"
    return line


def upload_md_reference(output: Path, reference_id: str = REFERENCE_ID) -> None:
    """Upload markdown reference."""
    log.info("Deleting existing reference.")
    out = run_command([PROG, "delete", reference_id])
    log.debug(f"Delete: {out}")

    log.info("Importing reference.")
    out = run_command([PROG, "import", str(output), reference_id])
    log.debug(f"Import: {out}")
