#!/usr/bin/env python3
"""Local content editor for the Dukyong Kim site.

From the repository root:

    python editor.py

Uses only the Python standard library. Pillow is optional; without it, a JPEG
can still replace a photo, and the editor tells you how to install Pillow
when a conversion is needed.
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import threading
import urllib.parse
import webbrowser
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EN_PATH = ROOT / "src" / "data" / "en.json"
KO_PATH = ROOT / "src" / "data" / "ko.json"
IMAGE_DIR = ROOT / "public" / "images"
CV_DIR = ROOT / "public" / "cv"
BACKUP_DIR = ROOT / ".editor-backups"
EDITOR_DIR = ROOT / "editor"
PREVIEW_PORT = 43123
MAX_UPLOAD = 20 * 1024 * 1024
MAX_EDGE = 2400

SYNC_KEYS = {
    "id",
    "href",
    "doi",
    "youtubeId",
    "year",
    "venue",
    "event",
    "date",
    "affiliationHref",
    "piHref",
    "orgUrl",
    "url",
    "src",
    "webp",
    "avif",
    "width",
    "height",
}
LAYOUT_FIELDS = {
    "portrait": "portrait",
    "campus": "campus",
    "research-overview": "overview",
    "spallation-system": "spallation",
    "lab": "lab",
    "lmd-diagram": "lmd",
}
DENY = ("YONHEE", "kQS7nwHt0t0", "kdy0414@")
YOUTUBE_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")
CV_FILES = {"pdf": "Dukyong-Kim-CV.pdf", "docx": "Dukyong-Kim-CV.docx"}
IMAGE_LABELS = {
    "portrait": ("Portrait", "프로필 사진"),
    "campus": ("Campus", "캠퍼스"),
    "lab": ("Laboratory", "실험실"),
    "lmd-diagram": ("Process diagram", "공정 도식"),
    "research-overview": ("Research overview", "연구 개요"),
    "spallation-system": ("Spallation system", "레이저 스폴레이션"),
}
IMAGE_ORDER = [
    "portrait",
    "campus",
    "research-overview",
    "spallation-system",
    "lab",
    "lmd-diagram",
]
PUBLISH_PATHS = [
    "src/data/en.json",
    "src/data/ko.json",
    "src/components/Page.astro",
    "public/images",
    "public/cv",
]

try:
    from PIL import Image, ImageOps
except ImportError:  # Pillow is optional.
    Image = None
    ImageOps = None

LOCK = threading.Lock()
PREVIEW_PROCESS: subprocess.Popen | None = None


def msg(en: str, ko: str) -> dict[str, str]:
    return {"en": en, "ko": ko}


def dump_json(data: object) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def stable(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def load_pair() -> tuple[dict, dict]:
    en = json.loads(EN_PATH.read_text(encoding="utf-8"))
    ko = json.loads(KO_PATH.read_text(encoding="utf-8"))
    if not isinstance(en, dict) or not isinstance(ko, dict):
        raise ValueError("content files must be JSON objects")
    return en, ko


def title_synced(parts: list[str]) -> bool:
    if len(parts) != 4 or parts[3] != "title":
        return False
    if parts[0] == "publications" and parts[1] == "items":
        return True
    if parts[0] == "talks" and parts[1] == "items":
        return True
    return parts[0] == "research" and parts[1] == "beamtimes"


def enum_synced(parts: list[str]) -> bool:
    """kind/role are shared tokens on entries, and translated labels under ui."""
    if len(parts) != 4:
        return False
    if parts[0] == "publications" and parts[1] == "items" and parts[3] in {"kind", "role"}:
        return True
    if parts[0] == "talks" and parts[1] == "items" and parts[3] == "role":
        return True
    return parts[0] == "timeline" and parts[1] == "items" and parts[3] == "kind"


def authors_path(parts: list[str]) -> bool:
    return (
        len(parts) == 4
        and parts[0] == "publications"
        and parts[1] == "items"
        and parts[3] == "authors"
    )


def normalize(node: object) -> None:
    """Drop empty optional keys so a save matches the hand-written files."""
    if isinstance(node, dict):
        for key in ("equal", "corresponding"):
            if node.get(key) is False:
                node.pop(key, None)
        for key in ("youtubeId", "doi", "orgUrl"):
            if node.get(key) == "":
                node.pop(key, None)
        for key in ("width", "height"):
            if isinstance(node.get(key), str) and node[key].isdigit():
                node[key] = int(node[key])
        for value in list(node.values()):
            normalize(value)
    elif isinstance(node, list):
        for value in node:
            normalize(value)


def shape_errors(a: object, b: object, path: str = "$") -> list[str]:
    errors: list[str] = []
    if type(a) is not type(b):
        errors.append(f"{path} has different types in English and Korean")
        return errors
    if isinstance(a, dict):
        if set(a) != set(b):
            missing_ko = sorted(set(a) - set(b))
            missing_en = sorted(set(b) - set(a))
            errors.append(f"{path} keys differ (en only {missing_ko}, ko only {missing_en})")
        for key in a.keys() & b.keys():
            errors.extend(shape_errors(a[key], b[key], f"{path}.{key}"))
    elif isinstance(a, list):
        if len(a) != len(b):
            errors.append(f"{path} has {len(a)} English entries and {len(b)} Korean entries")
        for index, (left, right) in enumerate(zip(a, b)):
            errors.extend(shape_errors(left, right, f"{path}[{index}]"))
    return errors


def sync_errors(a: object, b: object, parts: list[str] | None = None) -> list[str]:
    parts = parts or []
    errors: list[str] = []
    if isinstance(a, dict) and isinstance(b, dict):
        for key, value in a.items():
            if key not in b:
                continue
            child = parts + [key]
            if key in SYNC_KEYS or title_synced(child) or enum_synced(child) or authors_path(child):
                if stable(value) != stable(b[key]):
                    shown = ".".join(child)
                    errors.append(f"{shown} must be the same in English and Korean")
            else:
                errors.extend(sync_errors(value, b[key], child))
    elif isinstance(a, list) and isinstance(b, list):
        for index, value in enumerate(a[: len(b)]):
            errors.extend(sync_errors(value, b[index], parts + [str(index)]))
    return errors


def youtube_errors(node: object, path: str = "$") -> list[str]:
    errors: list[str] = []
    if isinstance(node, dict):
        if "youtubeId" in node and not (isinstance(node["youtubeId"], str) and YOUTUBE_RE.fullmatch(node["youtubeId"])):
            errors.append(f"{path}.youtubeId must be an 11-character YouTube id")
        for key, value in node.items():
            if key != "youtubeId":
                errors.extend(youtube_errors(value, f"{path}.{key}"))
    elif isinstance(node, list):
        for index, value in enumerate(node):
            errors.extend(youtube_errors(value, f"{path}[{index}]"))
    return errors


def author_name_error(en: dict) -> list[str]:
    names: list[str] = []
    for item in en.get("publications", {}).get("items", []):
        if isinstance(item, dict):
            for author in item.get("authors", []):
                if isinstance(author, dict) and isinstance(author.get("name"), str):
                    names.append(author["name"])
    if "Dukyong Kim" not in names:
        return ["At least one publication must list the author name Dukyong Kim, so the site can highlight it."]
    return []


def validate(en: object, ko: object) -> list[dict[str, str]]:
    if not isinstance(en, dict) or not isinstance(ko, dict):
        return [msg("Both language files must be objects.", "두 언어 파일은 객체여야 합니다.")]
    errors: list[dict[str, str]] = []
    blob = dump_json(en) + dump_json(ko)
    for needle in DENY:
        if needle in blob:
            errors.append(msg(
                "That text is not allowed on the public site.",
                "공개 사이트에 넣을 수 없는 문구가 있습니다.",
            ))
            break
    if not re.search(r"[가-힣]", dump_json(ko)):
        errors.append(msg("The Korean file has no Hangul.", "한국어 파일에 한글이 없습니다."))
    for problem in shape_errors(en, ko) + sync_errors(en, ko) + youtube_errors(en) + youtube_errors(ko) + author_name_error(en):
        errors.append(msg(problem, problem))
    return errors


def backup(paths: list[Path]) -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    dest = BACKUP_DIR / stamp
    for path in paths:
        if not path.is_file():
            continue
        target = dest / path.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
    return dest


def save_pair(en: dict, ko: dict) -> Path:
    en["lang"] = "en"
    en["home"] = "/"
    ko["lang"] = "ko"
    ko["home"] = "/ko/"
    normalize(en)
    normalize(ko)
    problems = validate(en, ko)
    if problems:
        raise ValueError(problems)
    dest = backup([EN_PATH, KO_PATH])
    EN_PATH.write_text(dump_json(en), encoding="utf-8", newline="\n")
    KO_PATH.write_text(dump_json(ko), encoding="utf-8", newline="\n")
    return dest


def extract_youtube_id(text: str) -> str | None:
    raw = (text or "").strip()
    if YOUTUBE_RE.fullmatch(raw):
        return raw
    if not raw:
        return None
    try:
        parsed = urllib.parse.urlparse(raw)
    except ValueError:
        return None
    host = parsed.netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    if host.startswith("m."):
        host = host[2:]
    parts = [part for part in parsed.path.split("/") if part]
    if host == "youtu.be" and parts and YOUTUBE_RE.fullmatch(parts[0]):
        return parts[0]
    if host in {"youtube.com", "music.youtube.com", "youtube-nocookie.com"}:
        video = urllib.parse.parse_qs(parsed.query).get("v", [""])[0]
        if YOUTUBE_RE.fullmatch(video):
            return video
        for marker in ("embed", "shorts", "live", "v"):
            if marker in parts:
                index = parts.index(marker)
                if index + 1 < len(parts) and YOUTUBE_RE.fullmatch(parts[index + 1]):
                    return parts[index + 1]
    return None


IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".avif", ".gif"}
DELETED_DIR = BACKUP_DIR / "deleted-images"
COMPONENT_SUFFIXES = {".astro", ".ts", ".tsx", ".js", ".mjs", ".css", ".svg"}


def image_paths() -> list[Path]:
    if not IMAGE_DIR.is_dir():
        return []
    return [
        path for path in sorted(IMAGE_DIR.iterdir())
        if path.is_file() and not path.name.startswith(".") and path.suffix.lower() in IMAGE_SUFFIXES
    ]


def variant_base(stem: str, stems: set[str]) -> str | None:
    best = None
    for other in stems:
        if other != stem and (stem.startswith(other + "-") or stem.startswith(other + "_")):
            if best is None or len(other) > len(best):
                best = other
    return best


def ultimate_base(stem: str, stems: set[str]) -> str | None:
    base = variant_base(stem, stems)
    seen = set()
    while base and base not in seen:
        seen.add(base)
        nxt = variant_base(base, stems)
        if not nxt:
            return base
        base = nxt
    return None


def image_groups() -> list[dict]:
    by_stem: dict[str, list[Path]] = {}
    for path in image_paths():
        by_stem.setdefault(path.stem, []).append(path)
    stems = set(by_stem)
    folded: dict[str, list[Path]] = {stem: list(paths) for stem, paths in by_stem.items()}
    for stem in list(by_stem):
        base = ultimate_base(stem, stems)
        if base and base != stem and stem in folded:
            folded[base].extend(folded.pop(stem))
    items = []
    for stem, paths in folded.items():
        names = sorted({path.name for path in paths})
        hero = stem == "portrait" or any(path.suffix.lower() in {".webp", ".avif"} for path in paths)
        label_en, label_ko = IMAGE_LABELS.get(stem, (stem.replace("-", " ").replace("_", " "), stem))
        thumb = next((name for name in names if name.lower().endswith((".jpg", ".jpeg"))), names[0])
        items.append({
            "id": stem,
            "label": {"en": label_en, "ko": label_ko},
            "hero": hero,
            "files": names,
            "thumb": thumb,
            "mtime": max(int(path.stat().st_mtime) for path in paths),
        })
    items.sort(key=lambda item: (IMAGE_ORDER.index(item["id"]) if item["id"] in IMAGE_ORDER else 100, item["id"]))
    return items


def group_by_id(stem: str) -> dict | None:
    if not re.fullmatch(r"[A-Za-z0-9_-]+", stem):
        return None
    for item in image_groups():
        if item["id"] == stem:
            return item
    return None


def exact_image_ref(value: str, names: set[str]) -> bool:
    text = value.strip().split("?", 1)[0].split("#", 1)[0]
    for name in names:
        if text == name or text.endswith("/" + name):
            return True
    return False


def filename_in_text(text: str, name: str) -> bool:
    """Match a file name as its own token, so lab.jpg does not match mylab.jpg."""
    return re.search(r"(?<![\w.-])" + re.escape(name) + r"(?![\w.-])", text) is not None


def mentions_image(value: str, names: set[str]) -> bool:
    if exact_image_ref(value, names):
        return False
    return any(filename_in_text(value, name) for name in names)


def json_path(parts: list) -> str:
    text = ""
    for part in parts:
        if isinstance(part, int):
            text += f"[{part}]"
        else:
            text += ("." if text else "") + str(part)
    return text or "$"


def image_slot(value: dict, names: set[str]) -> bool:
    """A layout image object is only a path plus pixel size, so it can be removed whole."""
    saw_file = False
    for item in value.values():
        if isinstance(item, str) and exact_image_ref(item, names):
            saw_file = True
        elif isinstance(item, (int, float)) and not isinstance(item, bool):
            continue
        else:
            return False
    return saw_file


def collect_json_usage(node: object, parts: list, names: set[str], content: list, mentions: list, in_item: bool = False) -> None:
    if isinstance(node, dict):
        if in_item and any(isinstance(value, str) and exact_image_ref(value, names) for value in node.values()):
            sample = next(value for value in node.values() if isinstance(value, str) and exact_image_ref(value, names))
            content.append({"path": json_path(parts), "parts": parts, "kind": "item", "value": sample})
            return
        for key, value in node.items():
            child = parts + [key]
            if isinstance(value, dict) and image_slot(value, names):
                sample = next(item for item in value.values() if isinstance(item, str) and exact_image_ref(item, names))
                content.append({"path": json_path(child), "parts": child, "kind": "field", "value": sample})
            elif isinstance(value, str) and exact_image_ref(value, names):
                content.append({"path": json_path(child), "parts": child, "kind": "field", "value": value})
            elif isinstance(value, str) and mentions_image(value, names):
                mentions.append({"path": json_path(child), "value": value[:160]})
            else:
                collect_json_usage(value, child, names, content, mentions, False)
    elif isinstance(node, list):
        for index, value in enumerate(node):
            child = parts + [index]
            if isinstance(value, str) and exact_image_ref(value, names):
                content.append({"path": json_path(child), "parts": child, "kind": "item", "value": value})
            elif isinstance(value, str) and mentions_image(value, names):
                mentions.append({"path": json_path(child), "value": value[:160]})
            else:
                collect_json_usage(value, child, names, content, mentions, True)


def component_usage(names: set[str]) -> list[dict]:
    hits = []
    src = ROOT / "src"
    if not src.is_dir():
        return hits
    for path in sorted(src.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in COMPONENT_SUFFIXES:
            continue
        if path.parts[-2:] == ("src", "data") or "data" in path.relative_to(src).parts and path.parent.name == "data":
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        rel = str(path.relative_to(ROOT))
        for number, line in enumerate(lines, 1):
            if any(filename_in_text(line, name) for name in names):
                hits.append({"file": rel, "line": number, "text": line.strip()[:180]})
    return hits


def merge_content(en_hits: list[dict], ko_hits: list[dict]) -> list[dict]:
    merged: dict[str, dict] = {}
    for lang, hits in (("en", en_hits), ("ko", ko_hits)):
        for hit in hits:
            row = merged.setdefault(hit["path"], {
                "path": hit["path"],
                "parts": hit["parts"],
                "kind": hit["kind"],
                "value": hit["value"],
                "langs": [],
            })
            if lang not in row["langs"]:
                row["langs"].append(lang)
            if lang == "ko" and hit["value"] != row["value"]:
                row["valueKo"] = hit["value"]
    return list(merged.values())


def image_usage(stem: str) -> dict:
    group = group_by_id(stem)
    if group is None:
        return {"ok": False, "error": msg("Unknown image.", "알 수 없는 사진입니다.")}
    names = set(group["files"])
    en, ko = load_pair()
    en_hits: list[dict] = []
    ko_hits: list[dict] = []
    en_mentions: list[dict] = []
    ko_mentions: list[dict] = []
    collect_json_usage(en, [], names, en_hits, en_mentions)
    collect_json_usage(ko, [], names, ko_hits, ko_mentions)
    hardcoded = component_usage(names)
    content = merge_content(en_hits, ko_hits)
    mentions = []
    for lang, rows in (("en", en_mentions), ("ko", ko_mentions)):
        for row in rows:
            mentions.append({**row, "lang": lang})
    return {
        "ok": True,
        "id": stem,
        "files": group["files"],
        "label": group["label"],
        "blocked": False,
        "hardcoded": hardcoded,
        "content": [{key: value for key, value in row.items() if key != "parts"} | {"parts": row["parts"]} for row in content],
        "mentions": mentions,
    }


def drop_path(node: object, parts: list) -> None:
    if not parts:
        return
    parent: object = node
    for part in parts[:-1]:
        if isinstance(part, int):
            if not isinstance(parent, list) or part >= len(parent):
                return
            parent = parent[part]
        else:
            if not isinstance(parent, dict) or part not in parent:
                return
            parent = parent[part]
    last = parts[-1]
    if isinstance(last, int):
        if isinstance(parent, list) and last < len(parent):
            parent.pop(last)
    elif isinstance(parent, dict):
        parent.pop(last, None)


def apply_reference_removals(en: dict, ko: dict, content: list[dict]) -> None:
    field_paths = [row["parts"] for row in content if row["kind"] == "field"]
    index_groups: dict[tuple, set[int]] = {}
    for row in content:
        if row["kind"] != "item":
            continue
        parent = tuple(row["parts"][:-1])
        index_groups.setdefault(parent, set()).add(row["parts"][-1])
    for tree in (en, ko):
        for parts in field_paths:
            drop_path(tree, parts)
        for parent, indexes in index_groups.items():
            for index in sorted(indexes, reverse=True):
                drop_path(tree, list(parent) + [index])


def get_path(node: object, parts: list) -> object:
    current = node
    for part in parts:
        if isinstance(part, int):
            if not isinstance(current, list) or not 0 <= part < len(current):
                return None
            current = current[part]
        else:
            if not isinstance(current, dict) or part not in current:
                return None
            current = current[part]
    return current


def snapshot_removals(en: dict, ko: dict, content: list[dict]) -> list[dict]:
    rows = []
    for row in content:
        parts = row["parts"]
        rows.append({
            "parts": parts,
            "kind": row["kind"],
            "en": copy.deepcopy(get_path(en, parts)),
            "ko": copy.deepcopy(get_path(ko, parts)),
        })
    return rows


def put_back(tree: dict, parts: list, value: object) -> bool:
    if value is None or not parts:
        return False
    parent: object = tree
    for part in parts[:-1]:
        if isinstance(part, int):
            if not isinstance(parent, list) or not 0 <= part < len(parent):
                return False
            parent = parent[part]
        else:
            if not isinstance(parent, dict):
                return False
            if part not in parent or not isinstance(parent[part], (dict, list)):
                parent[part] = {}
            parent = parent[part]
    last = parts[-1]
    if isinstance(last, int):
        if not isinstance(parent, list):
            return False
        if any(item == value for item in parent):
            return False
        parent.insert(min(last, len(parent)), copy.deepcopy(value))
        return True
    if isinstance(parent, dict) and last not in parent:
        parent[last] = copy.deepcopy(value)
        return True
    return False


def apply_restores(en: dict, ko: dict, removals: list) -> bool:
    changed = False
    fields = [row for row in removals if isinstance(row, dict) and row.get("kind") != "item"]
    items = [row for row in removals if isinstance(row, dict) and row.get("kind") == "item"]
    items.sort(key=lambda row: row["parts"][-1] if isinstance(row.get("parts"), list) and isinstance(row["parts"][-1], int) else 0)
    for row in fields + items:
        parts = row.get("parts")
        if not isinstance(parts, list) or not parts:
            continue
        changed = put_back(en, parts, row.get("en")) or changed
        changed = put_back(ko, parts, row.get("ko")) or changed
    return changed


def delete_image(stem: str, remove_references: bool = True) -> dict:
    usage = image_usage(stem)
    if not usage.get("ok"):
        return usage
    en = ko = None
    removals: list[dict] = []
    # Confirm always clears JSON references. The page hides a frame whose file or entry is gone.
    if usage["content"]:
        en, ko = load_pair()
        removals = snapshot_removals(en, ko, usage["content"])
        apply_reference_removals(en, ko, usage["content"])
        problems = validate(en, ko)
        if problems:
            return {"ok": False, "errors": problems}
    group = group_by_id(stem)
    assert group is not None
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    dest = DELETED_DIR / stamp
    dest.mkdir(parents=True, exist_ok=True)
    moved = []
    for name in group["files"]:
        source = IMAGE_DIR / name
        if source.is_file():
            shutil.move(str(source), dest / name)
            moved.append(name)
    (dest / "meta.json").write_text(json.dumps({
        "id": stem,
        "files": moved,
        "label": group["label"],
        "removals": removals,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if en is not None and ko is not None:
        try:
            save_pair(en, ko)
        except Exception:
            for name in moved:
                shutil.move(str(dest / name), IMAGE_DIR / name)
            shutil.rmtree(dest, ignore_errors=True)
            raise
    return {
        "ok": True,
        "backup": str(dest.relative_to(ROOT)),
        "files": moved,
        "contentChanged": en is not None,
        "hardcoded": usage["hardcoded"],
    }


def list_deleted() -> list[dict]:
    if not DELETED_DIR.is_dir():
        return []
    rows = []
    folders = [path for path in DELETED_DIR.iterdir() if path.is_dir()]
    for folder in sorted(folders, key=lambda path: path.name, reverse=True):
        meta: dict = {}
        meta_path = folder / "meta.json"
        if meta_path.is_file():
            try:
                loaded = json.loads(meta_path.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    meta = loaded
            except json.JSONDecodeError:
                meta = {}
        files = [
            path.name for path in sorted(folder.iterdir())
            if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
        ]
        if not files:
            continue
        thumb = next((name for name in files if name.lower().endswith((".jpg", ".jpeg"))), files[0])
        label = meta.get("label") if isinstance(meta.get("label"), dict) else {"en": meta.get("id") or folder.name, "ko": meta.get("id") or folder.name}
        rows.append({
            "stamp": folder.name,
            "id": meta.get("id") or Path(files[0]).stem,
            "files": files,
            "thumb": thumb,
            "label": label,
        })
    return rows[:40]


def restore_deleted(stamp: str) -> dict:
    if not re.fullmatch(r"\d{8}-\d{6}-\d{6}", stamp):
        return {"ok": False, "error": msg("Unknown deleted photo.", "알 수 없는 삭제 사진입니다.")}
    folder = (DELETED_DIR / stamp).resolve()
    if folder.parent != DELETED_DIR.resolve() or not folder.is_dir():
        return {"ok": False, "error": msg("Unknown deleted photo.", "알 수 없는 삭제 사진입니다.")}
    files = [path for path in folder.iterdir() if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES]
    if not files:
        return {"ok": False, "error": msg("That backup has no image file.", "그 백업에는 사진 파일이 없습니다.")}
    conflicts = [path.name for path in files if (IMAGE_DIR / path.name).exists()]
    if conflicts:
        return {"ok": False, "error": msg(
            "A photo with that name is already on the site: " + ", ".join(conflicts),
            "같은 이름의 사진이 이미 있습니다: " + ", ".join(conflicts),
        )}
    meta: dict = {}
    meta_path = folder / "meta.json"
    if meta_path.is_file():
        try:
            loaded = json.loads(meta_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                meta = loaded
        except json.JSONDecodeError:
            meta = {}
    removals = meta.get("removals") if isinstance(meta.get("removals"), list) else []
    en = ko = None
    if removals:
        loaded_en, loaded_ko = load_pair()
        if apply_restores(loaded_en, loaded_ko, removals) and not validate(loaded_en, loaded_ko):
            en, ko = loaded_en, loaded_ko
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    names = [path.name for path in files]
    for path in files:
        shutil.move(str(path), IMAGE_DIR / path.name)
    if en is not None and ko is not None:
        try:
            save_pair(en, ko)
        except Exception:
            for name in names:
                shutil.move(str(IMAGE_DIR / name), folder / name)
            raise
    shutil.rmtree(folder, ignore_errors=True)
    return {"ok": True, "files": names, "contentChanged": en is not None}


def slug_stem(original: str) -> str:
    stem = Path(original or "photo").stem.lower()
    stem = re.sub(r"[^a-z0-9]+", "-", stem).strip("-")[:40] or "photo"
    return stem


def unique_stem(stem: str) -> str:
    taken = {item["id"] for item in image_groups()}
    taken.update(path.stem for path in image_paths())
    if stem not in taken:
        return stem
    number = 2
    while f"{stem}-{number}" in taken:
        number += 1
    return f"{stem}-{number}"


def add_image(original_name: str, data: bytes) -> dict:
    if len(data) < 32:
        return {"ok": False, "error": msg("That file is empty.", "파일이 비어 있습니다.")}
    stem = unique_stem(slug_stem(original_name))
    dest = IMAGE_DIR / f"{stem}.jpg"
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    try:
        if Image is None:
            if not data.startswith(b"\xff\xd8"):
                return {"ok": False, "error": pillow_hint()}
            dest.write_bytes(data)
        else:
            image = open_image(data)
            image.save(dest, format="JPEG", quality=88, optimize=True)
    except Exception as exc:
        return {"ok": False, "error": msg(f"Could not read that image. {exc}", f"이미지를 읽지 못했습니다. {exc}")}
    return {"ok": True, "id": stem, "file": dest.name}


def jpeg_size(data: bytes) -> tuple[int, int] | None:
    if len(data) < 4 or data[:2] != b"\xff\xd8":
        return None
    index = 2
    while index + 9 < len(data):
        if data[index] != 0xFF:
            index += 1
            continue
        marker = data[index + 1]
        if marker in (0xC0, 0xC1, 0xC2):
            height = int.from_bytes(data[index + 5 : index + 7], "big")
            width = int.from_bytes(data[index + 7 : index + 9], "big")
            if width and height:
                return width, height
            return None
        if marker in (0xD8, 0xD9):
            index += 2
            continue
        if index + 4 > len(data):
            break
        length = int.from_bytes(data[index + 2 : index + 4], "big")
        if length < 2:
            break
        index += 2 + length
    return None


def open_image(data: bytes):
    if Image is None or ImageOps is None:
        raise RuntimeError("Pillow is not installed")
    image = ImageOps.exif_transpose(Image.open(BytesIO(data)))
    if image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info):
        rgba = image.convert("RGBA")
        background = Image.new("RGB", rgba.size, (255, 255, 255))
        background.paste(rgba, mask=rgba.getchannel("A"))
        image = background
    else:
        image = image.convert("RGB")
    width, height = image.size
    long_edge = max(width, height)
    if long_edge > MAX_EDGE:
        scale = MAX_EDGE / long_edge
        resample = getattr(getattr(Image, "Resampling", Image), "LANCZOS")
        image = image.resize((max(1, round(width * scale)), max(1, round(height * scale))), resample)
    return image


def write_layout_image(stem: str, width: int | None, height: int | None, extras: dict[str, str]) -> bool:
    field = LAYOUT_FIELDS.get(stem)
    if not field:
        return False
    en, ko = load_pair()
    src = f"/images/{stem}.jpg"
    for tree in (en, ko):
        media = tree.setdefault("media", {})
        if not isinstance(media, dict):
            return False
        current = media.get(field)
        slot = dict(current) if isinstance(current, dict) else {}
        slot["src"] = src
        if width and height:
            slot["width"] = width
            slot["height"] = height
        for key in ("webp", "avif"):
            if key in extras:
                slot[key] = extras[key]
            else:
                slot.pop(key, None)
        media[field] = slot
    save_pair(en, ko)
    return True


def pillow_hint() -> dict[str, str]:
    return msg(
        "Install Pillow once so replacements are converted and resized: pip install pillow",
        "교체한 사진을 변환하고 크기를 맞추려면 한 번만 설치하세요: pip install pillow",
    )


def replace_image(stem: str, data: bytes) -> dict:
    if not re.fullmatch(r"[A-Za-z0-9_-]+", stem):
        return {"ok": False, "error": msg("Unknown image.", "알 수 없는 사진입니다.")}
    groups = {item["id"]: item for item in image_groups()}
    if stem not in groups:
        return {"ok": False, "error": msg("Unknown image.", "알 수 없는 사진입니다.")}
    if len(data) < 32:
        return {"ok": False, "error": msg("That file is empty.", "파일이 비어 있습니다.")}
    group = groups[stem]
    paths = [IMAGE_DIR / name for name in group["files"]]
    paths.extend([EN_PATH, KO_PATH])
    backup(paths)
    notes: list[dict[str, str]] = []
    try:
        if group["hero"]:
            notes.extend(write_hero(data))
        else:
            notes.extend(write_simple_image(group, data))
    except Exception as exc:  # Pillow or a bad file.
        return {"ok": False, "error": msg(f"Could not read that image. {exc}", f"이미지를 읽지 못했습니다. {exc}")}
    return {"ok": True, "notes": notes}


def write_hero(data: bytes) -> list[dict[str, str]]:
    notes: list[dict[str, str]] = []
    if Image is None:
        if not data.startswith(b"\xff\xd8"):
            raise RuntimeError("Pillow is not installed, so only a JPEG can replace the portrait.")
        (IMAGE_DIR / "portrait.jpg").write_bytes(data)
        for name in ("portrait.webp", "portrait.avif"):
            (IMAGE_DIR / name).unlink(missing_ok=True)
        size = jpeg_size(data)
        extras: dict[str, str] = {}
        notes.append(msg(
            "Saved the JPEG. WebP and AVIF were removed so the previous portrait is not shown.",
            "JPEG만 저장했습니다. 이전 사진이 남지 않도록 WebP와 AVIF는 지웠습니다.",
        ))
        notes.append(pillow_hint())
    else:
        image = open_image(data)
        image.save(IMAGE_DIR / "portrait.jpg", format="JPEG", quality=88, optimize=True)
        image.save(IMAGE_DIR / "portrait.webp", format="WEBP", quality=82, method=6)
        extras = {"webp": "/images/portrait.webp"}
        try:
            image.save(IMAGE_DIR / "portrait.avif", format="AVIF", quality=50)
            extras["avif"] = "/images/portrait.avif"
        except Exception:
            (IMAGE_DIR / "portrait.avif").unlink(missing_ok=True)
            notes.append(msg(
                "Saved JPEG and WebP. This Pillow build cannot write AVIF, so that copy was removed.",
                "JPEG와 WebP는 저장했습니다. 이 Pillow는 AVIF를 만들지 못해 그 파일은 지웠습니다.",
            ))
        size = image.size
        notes.append(msg(
            "Regenerated the portrait files the site serves (JPEG, WebP, and AVIF when possible).",
            "사이트가 사용하는 프로필 사진(JPEG, WebP, 가능하면 AVIF)을 다시 만들었습니다.",
        ))
    width, height = size if size else (None, None)
    write_layout_image("portrait", width, height, extras)
    return notes


def write_simple_image(group: dict, data: bytes) -> list[dict[str, str]]:
    notes: list[dict[str, str]] = []
    filename = group["files"][0]
    dest = IMAGE_DIR / filename
    if Image is None:
        if not data.startswith(b"\xff\xd8"):
            raise RuntimeError("Pillow is not installed, so only a JPEG can replace this photo.")
        dest.write_bytes(data)
        size = jpeg_size(data)
    else:
        image = open_image(data)
        image.save(dest, format="JPEG", quality=88, optimize=True)
        size = image.size
    if size and group["id"] in LAYOUT_FIELDS:
        write_layout_image(group["id"], size[0], size[1], {})
    return notes


def cv_entries() -> list[dict]:
    entries = []
    for kind, name in CV_FILES.items():
        path = CV_DIR / name
        entries.append({
            "kind": kind,
            "name": name,
            "bytes": path.stat().st_size if path.is_file() else 0,
            "mtime": int(path.stat().st_mtime) if path.is_file() else 0,
        })
    return entries


def replace_cv(kind: str, data: bytes) -> dict:
    if kind not in CV_FILES:
        return {"ok": False, "error": msg("Choose the PDF or the Word file.", "PDF 또는 Word 파일을 고르세요.")}
    if kind == "pdf" and not data.startswith(b"%PDF"):
        return {"ok": False, "error": msg("That is not a PDF.", "PDF 파일이 아닙니다.")}
    if kind == "docx" and not data.startswith(b"PK\x03\x04"):
        return {"ok": False, "error": msg("That is not a Word .docx file.", "Word .docx 파일이 아닙니다.")}
    if len(data) < 32:
        return {"ok": False, "error": msg("That file is empty.", "파일이 비어 있습니다.")}
    path = CV_DIR / CV_FILES[kind]
    path.parent.mkdir(parents=True, exist_ok=True)
    backup([path])
    path.write_bytes(data)
    return {"ok": True}


def safe_child(folder: Path, name: str) -> Path | None:
    if not name or "/" in name or "\\" in name or name.startswith("."):
        return None
    path = (folder / name).resolve()
    if path.parent != folder.resolve() or not path.is_file():
        return None
    return path


def tool_path(name: str) -> str | None:
    return shutil.which(name)


def run_command(command: list[str], timeout: int = 60) -> subprocess.CompletedProcess | None:
    try:
        return subprocess.run(
            command,
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None


def git_ok() -> dict | None:
    if tool_path("git") is None:
        return {"ok": False, "error": msg(
            "Git is not installed. Install it from https://git-scm.com/download/win and then open the editor again.",
            "Git이 설치되어 있지 않습니다. https://git-scm.com/download/win 에서 설치한 뒤 편집기를 다시 여세요.",
        )}
    probe = run_command(["git", "rev-parse", "--is-inside-work-tree"])
    if probe is None or probe.returncode != 0 or probe.stdout.strip() != "true":
        return {"ok": False, "error": msg(
            "This folder is not a git clone. Clone the site, then run the editor inside that folder: git clone https://github.com/dukyong414/dukyong414.github.io.git",
            "이 폴더는 git 복제본이 아닙니다. 사이트를 복제한 폴더에서 편집기를 실행하세요: git clone https://github.com/dukyong414/dukyong414.github.io.git",
        )}
    return None


def current_branch() -> str:
    result = run_command(["git", "branch", "--show-current"])
    if result is None:
        return ""
    return result.stdout.strip()


def change_lines() -> list[str]:
    result = run_command(["git", "status", "--porcelain"])
    if result is None:
        return []
    return [line for line in result.stdout.splitlines() if line.strip()]


def publish(message: str) -> dict:
    blocked = git_ok()
    if blocked:
        return blocked
    branch = current_branch()
    if branch != "main":
        return {"ok": False, "error": msg(
            f"This folder is on branch {branch or '(none)'}, not main. In a terminal here, run: git checkout main",
            f"이 폴더는 main이 아닌 {branch or '(없음)'} 브랜치입니다. 여기서 터미널을 열고 git checkout main 을 실행하세요.",
        )}
    remote = run_command(["git", "remote", "get-url", "origin"])
    if remote is None or remote.returncode != 0:
        return {"ok": False, "error": msg(
            "This clone has no GitHub remote named origin.",
            "이 복제본에는 origin 이라는 GitHub 원격 저장소가 없습니다.",
        )}
    text = " ".join(message.split()).strip()
    if not text:
        text = "Update site content"
    if text.startswith("-") or len(text) > 200:
        return {"ok": False, "error": msg("Use a short commit message.", "짧은 커밋 메시지를 쓰세요.")}
    # -A records deletions under public/images, not only new or edited files.
    added = run_command(["git", "add", "-A", "--", *PUBLISH_PATHS])
    if added is None or added.returncode != 0:
        detail = "" if added is None else (added.stderr or added.stdout)
        return {"ok": False, "error": msg(f"Could not stage files. {detail}", f"파일을 올리지 못했습니다. {detail}")}
    staged = run_command(["git", "diff", "--cached", "--name-only"])
    if staged is None or not staged.stdout.strip():
        return {"ok": False, "error": msg(
            "Nothing to publish. Save a change first.",
            "게시할 변경이 없습니다. 먼저 저장하세요.",
        )}
    committed = run_command(["git", "commit", "-m", text])
    if committed is None or committed.returncode != 0:
        detail = "" if committed is None else (committed.stderr or committed.stdout)
        if "user.email" in detail or "user.name" in detail or "who you are" in detail.lower():
            return {"ok": False, "error": msg(
                'Git needs your name once. In a terminal: git config --global user.name "Dukyong Kim" and git config --global user.email "you@example.com"',
                'Git에 이름을 한 번 알려 주세요. 터미널에서 git config --global user.name "Dukyong Kim" 그리고 git config --global user.email "you@example.com"',
            )}
        return {"ok": False, "error": msg(f"Commit failed. {detail}", f"커밋에 실패했습니다. {detail}")}
    pushed = run_command(["git", "push", "origin", "main"], timeout=120)
    if pushed is None:
        return {"ok": False, "error": msg(
            "The push took too long or Git is unavailable. If a GitHub sign-in window is open, finish it and press Publish again.",
            "푸시가 너무 오래 걸렸거나 Git을 쓸 수 없습니다. GitHub 로그인 창이 있으면 로그인한 뒤 게시를 다시 누르세요.",
        )}
    if pushed.returncode != 0:
        detail = (pushed.stderr or pushed.stdout).strip()
        return {"ok": False, "error": msg(
            f"The commit was saved locally, but the push to GitHub failed. {detail}",
            f"커밋은 이 컴퓨터에 저장됐지만 GitHub로 올리지 못했습니다. {detail}",
        )}
    return {"ok": True, "files": staged.stdout.split(), "message": text}


def port_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.3)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def start_preview() -> dict:
    global PREVIEW_PROCESS
    if tool_path("node") is None or tool_path("npm") is None:
        return {"ok": False, "code": "no-node", "error": msg(
            "Node.js is not installed, so this computer cannot build a local preview. Save, then Publish. The live site updates a minute or two after the push to GitHub.",
            "이 컴퓨터에는 Node.js가 없어서 미리보기를 만들 수 없습니다. 저장한 뒤 게시를 누르면, GitHub에 올라간 다음 1–2분 뒤 실제 사이트가 바뀝니다.",
        )}
    url = f"http://127.0.0.1:{PREVIEW_PORT}/"
    if port_open(PREVIEW_PORT):
        return {"ok": True, "url": url, "already": True}
    if not (ROOT / "node_modules").is_dir():
        npm = tool_path("npm")
        installed = run_command([npm or "npm", "install"], timeout=300)
        if installed is None or installed.returncode != 0:
            detail = "" if installed is None else (installed.stderr or installed.stdout)[-500:]
            return {"ok": False, "error": msg(
                f"npm install failed, so the preview could not start. {detail}",
                f"npm install 이 실패해서 미리보기를 시작하지 못했습니다. {detail}",
            )}
    if PREVIEW_PROCESS is not None and PREVIEW_PROCESS.poll() is None:
        return {"ok": True, "url": url, "already": True}
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    log_path = BACKUP_DIR / "preview.log"
    log_file = log_path.open("w", encoding="utf-8")
    npm = tool_path("npm") or "npm"
    kwargs = {}
    if sys.platform == "win32":
        kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    PREVIEW_PROCESS = subprocess.Popen(
        [npm, "run", "dev"],
        cwd=ROOT,
        stdout=log_file,
        stderr=subprocess.STDOUT,
        **kwargs,
    )
    for _ in range(80):
        if port_open(PREVIEW_PORT):
            return {"ok": True, "url": url}
        if PREVIEW_PROCESS.poll() is not None:
            break
        threading.Event().wait(0.5)
    tail = ""
    try:
        tail = log_path.read_text(encoding="utf-8", errors="replace")[-800:]
    except OSError:
        tail = ""
    return {"ok": False, "error": msg(
        f"The preview server did not start. {tail}",
        f"미리보기 서버가 시작되지 않았습니다. {tail}",
    )}


def status() -> dict:
    return {
        "python": platform_version(),
        "pillow": Image is not None,
        "node": tool_path("node") is not None,
        "npm": tool_path("npm") is not None,
        "git": tool_path("git") is not None,
        "branch": current_branch() if tool_path("git") else "",
        "previewUrl": f"http://127.0.0.1:{PREVIEW_PORT}/",
        "pillowHint": pillow_hint(),
    }


def platform_version() -> str:
    return sys.version.split()[0]


class EditorServer(ThreadingHTTPServer):
    allow_reuse_address = True
    daemon_threads = True


class EditorHandler(BaseHTTPRequestHandler):
    server_version = "SiteEditor/1.0"

    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def do_GET(self) -> None:  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)
        if path in ("/", "/index.html"):
            self.send_file(EDITOR_DIR / "index.html", "text/html; charset=utf-8")
        elif path == "/editor.css":
            self.send_file(EDITOR_DIR / "editor.css", "text/css; charset=utf-8")
        elif path == "/editor.js":
            self.send_file(EDITOR_DIR / "editor.js", "text/javascript; charset=utf-8")
        elif path == "/favicon.svg":
            self.send_file(ROOT / "public" / "favicon.svg", "image/svg+xml")
        elif path.startswith("/fonts/"):
            self.serve_named(ROOT / "public" / "fonts", path[len("/fonts/"):], "font/woff2")
        elif path.startswith("/media/images/"):
            self.serve_named(IMAGE_DIR, path[len("/media/images/"):], None)
        elif path.startswith("/media/cv/"):
            self.serve_named(CV_DIR, path[len("/media/cv/"):], None)
        elif path.startswith("/media/deleted/"):
            self.serve_deleted(path[len("/media/deleted/"):])
        elif path == "/api/content":
            en, ko = load_pair()
            self.send_json(200, {"en": en, "ko": ko, "syncKeys": sorted(SYNC_KEYS)})
        elif path == "/api/status":
            self.send_json(200, status())
        elif path == "/api/files":
            self.send_json(200, {
                "images": image_groups(),
                "cvs": cv_entries(),
                "deleted": list_deleted(),
                "pillow": Image is not None,
            })
        elif path == "/api/image-usage":
            self.send_json(200, image_usage(query.get("id", [""])[0]))
        elif path == "/api/changes":
            blocked = git_ok()
            if blocked:
                self.send_json(200, blocked)
                return
            branch = current_branch()
            self.send_json(200, {
                "ok": True,
                "branch": branch,
                "onMain": branch == "main",
                "files": change_lines(),
                "error": None if branch == "main" else msg(
                    f"This folder is on branch {branch or '(none)'}, not main. Publish only works on main.",
                    f"이 폴더는 main이 아닌 {branch or '(없음)'} 브랜치입니다. 게시는 main에서만 됩니다.",
                ),
            })
        elif path == "/api/youtube":
            video_id = extract_youtube_id(query.get("u", [""])[0])
            self.send_json(200, {"id": video_id})
        else:
            self.send_error(404)

    def do_POST(self) -> None:  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length < 0 or length > MAX_UPLOAD:
            self.send_json(413, {"ok": False, "error": msg("That file is too large (limit 20 MB).", "파일이 너무 큽니다 (최대 20 MB).")})
            return
        body = self.rfile.read(length) if length else b""
        query = urllib.parse.parse_qs(parsed.query)
        try:
            if parsed.path == "/api/save":
                self.handle_save(body)
            elif parsed.path == "/api/replace-image":
                stem = query.get("id", [""])[0]
                with LOCK:
                    self.send_json(200, replace_image(stem, body))
            elif parsed.path == "/api/replace-cv":
                kind = query.get("kind", [""])[0]
                with LOCK:
                    self.send_json(200, replace_cv(kind, body))
            elif parsed.path == "/api/add-image":
                with LOCK:
                    self.send_json(200, add_image(query.get("name", ["photo.jpg"])[0], body))
            elif parsed.path == "/api/delete-image":
                self.handle_delete_image(body)
            elif parsed.path == "/api/restore-image":
                self.handle_restore_image(body)
            elif parsed.path == "/api/preview":
                self.send_json(200, start_preview())
            elif parsed.path == "/api/publish":
                self.handle_publish(body)
            else:
                self.send_error(404)
        except Exception as exc:
            self.send_json(500, {"ok": False, "error": msg(str(exc), str(exc))})

    def handle_save(self, body: bytes) -> None:
        try:
            payload = json.loads(body.decode("utf-8"))
            en = payload["en"]
            ko = payload["ko"]
        except Exception:
            self.send_json(400, {"ok": False, "error": msg("The editor sent invalid JSON.", "편집기가 잘못된 JSON을 보냈습니다.")})
            return
        if isinstance(en, dict):
            en["lang"] = "en"
            en["home"] = "/"
        if isinstance(ko, dict):
            ko["lang"] = "ko"
            ko["home"] = "/ko/"
        normalize(en) if isinstance(en, dict) else None
        normalize(ko) if isinstance(ko, dict) else None
        problems = validate(en, ko)
        if problems:
            self.send_json(400, {"ok": False, "errors": problems})
            return
        with LOCK:
            try:
                dest = save_pair(en, ko)
            except ValueError as exc:
                detail = exc.args[0] if exc.args else []
                self.send_json(400, {"ok": False, "errors": detail})
                return
        self.send_json(200, {"ok": True, "backup": str(dest.relative_to(ROOT))})

    def handle_delete_image(self, body: bytes) -> None:
        try:
            payload = json.loads(body.decode("utf-8") or "{}")
        except Exception:
            self.send_json(400, {"ok": False, "error": msg("Invalid request.", "잘못된 요청입니다.")})
            return
        with LOCK:
            try:
                result = delete_image(str(payload.get("id") or ""), bool(payload.get("removeReferences")))
            except Exception as exc:
                self.send_json(500, {"ok": False, "error": msg(str(exc), str(exc))})
                return
        if result.get("contentChanged"):
            en, ko = load_pair()
            result["en"] = en
            result["ko"] = ko
        self.send_json(200 if result.get("ok") else 400, result)

    def handle_restore_image(self, body: bytes) -> None:
        try:
            payload = json.loads(body.decode("utf-8") or "{}")
        except Exception:
            self.send_json(400, {"ok": False, "error": msg("Invalid request.", "잘못된 요청입니다.")})
            return
        with LOCK:
            result = restore_deleted(str(payload.get("stamp") or ""))
        if result.get("contentChanged"):
            en, ko = load_pair()
            result["en"] = en
            result["ko"] = ko
        self.send_json(200 if result.get("ok") else 400, result)

    def handle_publish(self, body: bytes) -> None:
        try:
            payload = json.loads(body.decode("utf-8") or "{}")
        except Exception:
            self.send_json(400, {"ok": False, "error": msg("Invalid request.", "잘못된 요청입니다.")})
            return
        if payload.get("confirm") is not True:
            self.send_json(400, {"ok": False, "error": msg(
                "Publish was not confirmed.",
                "게시가 확인되지 않았습니다.",
            )})
            return
        with LOCK:
            result = publish(str(payload.get("message") or ""))
        self.send_json(200 if result.get("ok") else 400, result)

    def serve_deleted(self, spec: str) -> None:
        parts = [part for part in spec.split("/") if part]
        if len(parts) != 2:
            self.send_error(404)
            return
        stamp, name = parts
        if not re.fullmatch(r"\d{8}-\d{6}-\d{6}", stamp):
            self.send_error(404)
            return
        folder = (DELETED_DIR / stamp).resolve()
        if folder.parent != DELETED_DIR.resolve():
            self.send_error(404)
            return
        path = safe_child(folder, urllib.parse.unquote(name))
        if path is None:
            self.send_error(404)
            return
        self.send_file(path, guess_type(path))

    def serve_named(self, folder: Path, name: str, content_type: str | None) -> None:
        path = safe_child(folder, urllib.parse.unquote(name))
        if path is None:
            self.send_error(404)
            return
        self.send_file(path, content_type or guess_type(path))

    def send_file(self, path: Path, content_type: str) -> None:
        if not path.is_file():
            self.send_error(404)
            return
        data = path.read_bytes()
        self.send_bytes(200, data, content_type)

    def send_json(self, code: int, payload: object) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_bytes(code, data, "application/json; charset=utf-8")

    def send_bytes(self, code: int, data: bytes, content_type: str) -> None:
        try:
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError):
            pass


def guess_type(path: Path) -> str:
    suffix = path.suffix.lower()
    return {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
        ".avif": "image/avif",
        ".gif": "image/gif",
        ".svg": "image/svg+xml",
        ".pdf": "application/pdf",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".woff2": "font/woff2",
    }.get(suffix, "application/octet-stream")


def pick_port(preferred: int) -> int:
    if preferred:
        return preferred
    for port in range(8765, 8785):
        if not port_open(port):
            return port
    return 8765


def main() -> None:
    parser = argparse.ArgumentParser(description="Edit the Dukyong Kim site in a browser.")
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    os.chdir(ROOT)
    if not EN_PATH.is_file() or not KO_PATH.is_file():
        raise SystemExit("Run editor.py from the site repository. src/data/en.json was not found.")
    port = pick_port(args.port)
    server = EditorServer(("127.0.0.1", port), EditorHandler)
    url = f"http://127.0.0.1:{port}/"
    print(f"Site editor: {url}")
    print("Press Ctrl+C to stop.")
    if not args.no_browser:
        threading.Timer(0.4, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        server.server_close()
        if PREVIEW_PROCESS is not None and PREVIEW_PROCESS.poll() is None:
            PREVIEW_PROCESS.terminate()


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as exc:
        print(f"Editor failed: {exc}", file=sys.stderr)
        if sys.platform == "win32":
            try:
                input("\nPress Enter to close...")
            except EOFError:
                pass
        raise
