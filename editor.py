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
PAGE_PATH = ROOT / "src" / "components" / "Page.astro"
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


def image_groups() -> list[dict]:
    groups: dict[str, list[Path]] = {}
    if IMAGE_DIR.is_dir():
        for path in sorted(IMAGE_DIR.iterdir()):
            if path.is_file() and not path.name.startswith("."):
                groups.setdefault(path.stem, []).append(path)
    items = []
    for stem, paths in groups.items():
        names = [path.name for path in paths]
        hero = stem == "portrait" or any(path.suffix.lower() in {".webp", ".avif"} for path in paths)
        label_en, label_ko = IMAGE_LABELS.get(stem, (stem.replace("-", " "), stem))
        thumb = next((name for name in names if name.lower().endswith(".jpg")), names[0])
        items.append({
            "id": stem,
            "label": {"en": label_en, "ko": label_ko},
            "hero": hero,
            "files": names,
            "thumb": thumb,
            "mtime": max(int(path.stat().st_mtime) for path in paths),
        })
    items.sort(key=lambda item: IMAGE_ORDER.index(item["id"]) if item["id"] in IMAGE_ORDER else 100)
    return items


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


def portrait_markup(width: int, height: int) -> str:
    lines = ["            <picture>"]
    if (IMAGE_DIR / "portrait.avif").is_file():
        lines.append('              <source srcset="/images/portrait.avif" type="image/avif" />')
    if (IMAGE_DIR / "portrait.webp").is_file():
        lines.append('              <source srcset="/images/portrait.webp" type="image/webp" />')
    lines.extend([
        "              <img",
        '                src="/images/portrait.jpg"',
        f'                width="{width}"',
        f'                height="{height}"',
        "                alt={c.media.portraitAlt}",
        "              />",
        "            </picture>",
    ])
    return "\n".join(lines)


def write_portrait_markup(width: int, height: int) -> bool:
    text = PAGE_PATH.read_text(encoding="utf-8")
    block = portrait_markup(width, height)
    new, count = re.subn(r"[ ]*<picture>[\s\S]*?</picture>", block, text, count=1)
    if count != 1:
        return False
    if new != text:
        PAGE_PATH.write_text(new, encoding="utf-8", newline="\n")
    return True


def update_img_size(filename: str, width: int, height: int) -> bool:
    text = PAGE_PATH.read_text(encoding="utf-8")
    pattern = re.compile(rf'(src="/images/{re.escape(filename)}"\s+width=")\d+("\s+height=")\d+(")')
    new, count = pattern.subn(lambda match: f"{match.group(1)}{width}{match.group(2)}{height}{match.group(3)}", text, count=1)
    if count != 1:
        return False
    if new != text:
        PAGE_PATH.write_text(new, encoding="utf-8", newline="\n")
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
    paths.append(PAGE_PATH)
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
        notes.append(msg(
            "Saved the JPEG. WebP and AVIF were removed so the previous portrait is not shown.",
            "JPEG만 저장했습니다. 이전 사진이 남지 않도록 WebP와 AVIF는 지웠습니다.",
        ))
        notes.append(pillow_hint())
    else:
        image = open_image(data)
        image.save(IMAGE_DIR / "portrait.jpg", format="JPEG", quality=88, optimize=True)
        image.save(IMAGE_DIR / "portrait.webp", format="WEBP", quality=82, method=6)
        try:
            image.save(IMAGE_DIR / "portrait.avif", format="AVIF", quality=50)
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
    if size:
        write_portrait_markup(*size)
    else:
        notes.append(msg(
            "Could not read the pixel size, so the page template was left unchanged.",
            "픽셀 크기를 읽지 못해 페이지 템플릿은 그대로 두었습니다.",
        ))
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
    if size and filename.lower().endswith(".jpg"):
        if not update_img_size(filename, *size):
            notes.append(msg(
                "The photo was saved. Its width and height in the page template were not found to update.",
                "사진은 저장했습니다. 페이지 템플릿의 가로·세로 숫자는 찾지 못했습니다.",
            ))
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
    added = run_command(["git", "add", "--", *PUBLISH_PATHS])
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
        elif path == "/api/content":
            en, ko = load_pair()
            self.send_json(200, {"en": en, "ko": ko, "syncKeys": sorted(SYNC_KEYS)})
        elif path == "/api/status":
            self.send_json(200, status())
        elif path == "/api/files":
            self.send_json(200, {"images": image_groups(), "cvs": cv_entries(), "pillow": Image is not None})
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
