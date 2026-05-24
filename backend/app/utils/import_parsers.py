from __future__ import annotations

import json
import re
import uuid
import zipfile
from pathlib import PurePosixPath
from typing import Any
from xml.etree import ElementTree


SUPPORTED_TEXT_SUFFIXES = {".txt", ".md", ".docx"}
IGNORED_NAMES = {".ds_store", "thumbs.db"}
UNSUPPORTED_LEGACY_NOTE = "暂未导入：人物、关系图、时间线、知识库等复杂资料将在后续版本支持。"


def calculate_word_count(content: str) -> int:
    return sum(1 for character in content if not character.isspace())


def parse_legacy_json_bytes(content: bytes, source_filename: str) -> dict[str, Any]:
    warnings: list[str] = []
    unsupported_items: list[str] = []
    failed_files: list[str] = []

    text = decode_text(content, source_filename, failed_files)
    if text is None:
        return empty_preview_payload(
            import_type="legacy_json",
            source_filename=source_filename,
            warnings=["无法识别 JSON 文件编码。"],
            failed_files=failed_files,
        )

    try:
        raw_data = json.loads(text)
    except json.JSONDecodeError as exc:
        return empty_preview_payload(
            import_type="legacy_json",
            source_filename=source_filename,
            warnings=[f"JSON 解析失败：{exc.msg}"],
            failed_files=[source_filename],
        )

    if not isinstance(raw_data, dict):
        return empty_preview_payload(
            import_type="legacy_json",
            source_filename=source_filename,
            warnings=["旧版 JSON 顶层结构不是对象，暂无法导入。"],
        )

    project_data = raw_data.get("project") if isinstance(raw_data.get("project"), dict) else raw_data
    title = pick_string(project_data, ["title", "name", "project_title"]) or strip_extension(source_filename)
    summary = pick_string(project_data, ["summary", "description", "desc", "note"]) or None

    volumes: list[dict[str, Any]] = []
    volume_lookup: dict[str, dict[str, Any]] = {}
    unassigned_chapters: list[dict[str, Any]] = []

    raw_volumes = raw_data.get("volumes")
    if isinstance(raw_volumes, list):
        for index, raw_volume in enumerate(raw_volumes):
            if not isinstance(raw_volume, dict):
                warnings.append(f"第 {index + 1} 个分卷结构无法识别，已跳过。")
                continue

            volume = create_volume_payload(
                title=pick_string(raw_volume, ["title", "name", "volume_title"]) or f"分卷 {index + 1}",
                order_index=parse_order(raw_volume, index),
            )
            volumes.append(volume)
            register_volume_aliases(volume_lookup, volume, raw_volume)

            raw_chapters = raw_volume.get("chapters")
            if isinstance(raw_chapters, list):
                for chapter_index, raw_chapter in enumerate(raw_chapters):
                    chapter = parse_legacy_chapter(raw_chapter, chapter_index, warnings)
                    if chapter is not None:
                        volume["chapters"].append(chapter)

    raw_chapters = raw_data.get("chapters")
    if isinstance(raw_chapters, list):
        for index, raw_chapter in enumerate(raw_chapters):
            chapter = parse_legacy_chapter(raw_chapter, index, warnings)
            if chapter is None:
                continue

            volume_key = pick_string(raw_chapter, ["volume", "volume_title", "volume_id"]) if isinstance(raw_chapter, dict) else None
            if volume_key:
                volume = volume_lookup.get(volume_key)
                if volume is None:
                    volume = create_volume_payload(title=volume_key, order_index=len(volumes))
                    volumes.append(volume)
                    volume_lookup[volume_key] = volume
                volume["chapters"].append(chapter)
            else:
                unassigned_chapters.append(chapter)

    for key in ["notes", "characters", "graph", "timeline", "knowledge_base"]:
        if key in raw_data:
            unsupported_items.append(key)

    if unsupported_items:
        warnings.append(UNSUPPORTED_LEGACY_NOTE)

    return build_preview_payload(
        import_type="legacy_json",
        source_filename=source_filename,
        detected_project_title=title,
        summary=summary,
        volumes=volumes,
        unassigned_chapters=unassigned_chapters,
        warnings=warnings,
        unsupported_items=unsupported_items,
        failed_files=failed_files,
    )


def parse_folder_zip_bytes(content: bytes, source_filename: str) -> dict[str, Any]:
    warnings: list[str] = []
    unsupported_items: list[str] = []
    failed_files: list[str] = []
    empty_files: list[str] = []
    text_entries: list[tuple[PurePosixPath, str]] = []

    try:
        with zipfile.ZipFile(io_bytes(content)) as archive:
            for info in archive.infolist():
                path = PurePosixPath(info.filename)
                if should_ignore_zip_path(path) or info.is_dir():
                    continue

                if path.suffix.lower() not in SUPPORTED_TEXT_SUFFIXES:
                    unsupported_items.append(info.filename)
                    continue

                if any(part == ".." for part in path.parts) or path.is_absolute():
                    failed_files.append(info.filename)
                    continue

                file_content = archive.read(info)
                text = parse_supported_file(file_content, info.filename, failed_files)
                if text is not None:
                    if not text.strip():
                        empty_files.append(info.filename)
                        continue
                    text_entries.append((path, text))
    except zipfile.BadZipFile:
        return empty_preview_payload(
            import_type="folder_zip",
            source_filename=source_filename,
            warnings=["ZIP 文件无法读取。"],
            failed_files=[source_filename],
        )

    if not text_entries:
        return empty_preview_payload(
            import_type="folder_zip",
            source_filename=source_filename,
            warnings=["未找到可导入的 .txt 或 .md 文件。"],
            unsupported_items=unsupported_items,
            failed_files=failed_files,
        )

    root_prefix = detect_common_root([path for path, _text in text_entries])
    project_title = root_prefix or strip_extension(source_filename)
    volumes, unassigned_chapters = build_structure_from_text_entries(text_entries, root_prefix)

    return build_preview_payload(
        import_type="folder_zip",
        source_filename=source_filename,
        detected_project_title=project_title,
        summary=None,
        volumes=volumes,
        unassigned_chapters=unassigned_chapters,
        warnings=warnings,
        unsupported_items=unsupported_items,
        failed_files=failed_files,
        empty_files=empty_files,
    )


def parse_external_files(file_entries: list[tuple[str, bytes]], source_filename: str) -> dict[str, Any]:
    warnings: list[str] = []
    unsupported_items: list[str] = []
    failed_files: list[str] = []
    empty_files: list[str] = []
    text_entries: list[tuple[PurePosixPath, str]] = []

    for filename, content in file_entries:
        path = PurePosixPath(filename)
        if should_ignore_zip_path(path) or not path.name:
            continue
        if path.suffix.lower() not in SUPPORTED_TEXT_SUFFIXES:
            unsupported_items.append(filename)
            continue
        text = parse_supported_file(content, filename, failed_files)
        if text is not None:
            if not text.strip():
                empty_files.append(filename)
                continue
            text_entries.append((path, text))

    if not text_entries:
        return empty_preview_payload(
            import_type="external_files",
            source_filename=source_filename,
            warnings=["未找到可导入的 .txt、.md 或 .docx 文件。"],
            unsupported_items=unsupported_items,
            failed_files=failed_files,
            empty_files=empty_files,
        )

    root_prefix = detect_common_root([path for path, _text in text_entries])
    volumes, unassigned_chapters = build_structure_from_text_entries(text_entries, root_prefix)

    return build_preview_payload(
        import_type="external_files",
        source_filename=root_prefix or source_filename,
        detected_project_title=root_prefix or strip_extension(source_filename),
        summary=None,
        volumes=volumes,
        unassigned_chapters=unassigned_chapters,
        warnings=warnings,
        unsupported_items=unsupported_items,
        failed_files=failed_files,
        empty_files=empty_files,
    )


def decode_text(content: bytes, filename: str, failed_files: list[str]) -> str | None:
    for encoding in ["utf-8", "utf-8-sig", "gbk"]:
        try:
            text = content.decode(encoding)
            if encoding == "utf-8" and text.startswith("\ufeff"):
                continue
            return text
        except UnicodeDecodeError:
            continue

    failed_files.append(filename)
    return None


def parse_supported_file(content: bytes, filename: str, failed_files: list[str]) -> str | None:
    if PurePosixPath(filename).suffix.lower() == ".docx":
        return parse_docx_text(content, filename, failed_files)
    return decode_text(content, filename, failed_files)


def parse_docx_text(content: bytes, filename: str, failed_files: list[str]) -> str | None:
    try:
        with zipfile.ZipFile(io_bytes(content)) as archive:
            xml_content = archive.read("word/document.xml")
    except (KeyError, zipfile.BadZipFile):
        failed_files.append(filename)
        return None

    try:
        root = ElementTree.fromstring(xml_content)
    except ElementTree.ParseError:
        failed_files.append(filename)
        return None

    namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    paragraphs: list[str] = []
    for paragraph in root.findall(".//w:body/w:p", namespace):
        text = "".join(node.text or "" for node in paragraph.findall(".//w:t", namespace)).strip()
        if text:
            paragraphs.append(text)
    return "\n\n".join(paragraphs)


def build_preview_payload(
    *,
    import_type: str,
    source_filename: str,
    detected_project_title: str,
    summary: str | None,
    volumes: list[dict[str, Any]],
    unassigned_chapters: list[dict[str, Any]],
    warnings: list[str],
    unsupported_items: list[str],
    failed_files: list[str],
    empty_files: list[str] | None = None,
) -> dict[str, Any]:
    total_word_count = sum(
        chapter["word_count"]
        for chapter in unassigned_chapters
        for _ in [None]
    ) + sum(
        chapter["word_count"]
        for volume in volumes
        for chapter in volume["chapters"]
    )
    chapter_count = len(unassigned_chapters) + sum(len(volume["chapters"]) for volume in volumes)
    files_detected = [
        chapter.get("source_path", chapter["title"])
        for chapter in unassigned_chapters
    ] + [
        chapter.get("source_path", chapter["title"])
        for volume in volumes
        for chapter in volume["chapters"]
    ]
    detected_empty_files = [
        chapter.get("source_path", chapter["title"])
        for chapter in unassigned_chapters
        if not chapter.get("content", "").strip()
    ] + [
        chapter.get("source_path", chapter["title"])
        for volume in volumes
        for chapter in volume["chapters"]
        if not chapter.get("content", "").strip()
    ]
    empty_files = sorted(set((empty_files or []) + detected_empty_files))
    duplicate_titles = find_duplicate_titles(volumes, unassigned_chapters)
    if empty_files:
        warnings.append(f"发现 {len(empty_files)} 个空文件。")
    if duplicate_titles:
        warnings.append(f"发现重复章节标题：{', '.join(duplicate_titles)}")

    return {
        "import_id": "",
        "import_type": import_type,
        "source_filename": source_filename,
        "detected_project_title": detected_project_title,
        "summary": summary,
        "volumes": volumes,
        "unassigned_chapters": unassigned_chapters,
        "volume_count": len(volumes),
        "chapter_count": chapter_count,
        "total_word_count": total_word_count,
        "unassigned_chapter_count": len(unassigned_chapters),
        "warnings": warnings,
        "unsupported_items": sorted(set(unsupported_items)),
        "failed_files": failed_files,
        "report": {
            "files_detected": files_detected,
            "files_skipped": sorted(set(unsupported_items + failed_files + empty_files)),
            "encoding_issues": failed_files,
            "empty_files": empty_files,
            "duplicate_titles": duplicate_titles,
            "unsupported_files": sorted(set(unsupported_items)),
        },
        "can_import": chapter_count > 0,
    }


def empty_preview_payload(
    *,
    import_type: str,
    source_filename: str,
    warnings: list[str],
    unsupported_items: list[str] | None = None,
    failed_files: list[str] | None = None,
    empty_files: list[str] | None = None,
) -> dict[str, Any]:
    return build_preview_payload(
        import_type=import_type,
        source_filename=source_filename,
        detected_project_title=strip_extension(source_filename),
        summary=None,
        volumes=[],
        unassigned_chapters=[],
        warnings=warnings,
        unsupported_items=unsupported_items or [],
        failed_files=failed_files or [],
        empty_files=empty_files or [],
    )


def parse_legacy_chapter(raw_chapter: Any, index: int, warnings: list[str]) -> dict[str, Any] | None:
    if isinstance(raw_chapter, str):
        return create_chapter_payload(f"章节 {index + 1}", raw_chapter, index)

    if not isinstance(raw_chapter, dict):
        warnings.append(f"第 {index + 1} 个章节结构无法识别，已跳过。")
        return None

    title = pick_string(raw_chapter, ["title", "name", "chapter_title"]) or f"章节 {index + 1}"
    content = pick_string(raw_chapter, ["content", "text", "body"]) or ""
    order_index = parse_order(raw_chapter, index)
    return create_chapter_payload(title, content, order_index)


def create_volume_payload(title: str, order_index: int) -> dict[str, Any]:
    return {
        "temp_id": str(uuid.uuid4()),
        "title": clean_title(title),
        "order_index": order_index,
        "chapters": [],
    }


def create_chapter_payload(filename_or_title: str, content: str, order_index: int) -> dict[str, Any]:
    return {
        "temp_id": str(uuid.uuid4()),
        "title": clean_title(strip_extension(filename_or_title)),
        "content": content,
        "order_index": order_index,
        "word_count": calculate_word_count(content),
        "source_path": filename_or_title,
    }


def build_structure_from_text_entries(
    text_entries: list[tuple[PurePosixPath, str]],
    root_prefix: str | None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    volumes: list[dict[str, Any]] = []
    volume_lookup: dict[str, dict[str, Any]] = {}
    unassigned_chapters: list[dict[str, Any]] = []

    for order_index, (path, text) in enumerate(sorted(text_entries, key=lambda item: natural_sort_key(str(item[0])))):
        relative_path = remove_root_prefix(path, root_prefix)
        if len(relative_path.parts) >= 2:
            volume_title = relative_path.parts[0]
            chapter_name = relative_path.name
            volume = volume_lookup.get(volume_title)
            if volume is None:
                volume = create_volume_payload(title=volume_title, order_index=len(volumes))
                volume_lookup[volume_title] = volume
                volumes.append(volume)
            volume["chapters"].append(create_chapter_payload(chapter_name, text, len(volume["chapters"])))
        else:
            unassigned_chapters.append(create_chapter_payload(relative_path.name, text, order_index))

    return volumes, unassigned_chapters


def find_duplicate_titles(
    volumes: list[dict[str, Any]],
    unassigned_chapters: list[dict[str, Any]],
) -> list[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for chapter in list(unassigned_chapters) + [
        chapter for volume in volumes for chapter in volume["chapters"]
    ]:
        title = chapter["title"]
        if title in seen:
            duplicates.add(title)
        seen.add(title)
    return sorted(duplicates)


def pick_string(data: Any, keys: list[str]) -> str | None:
    if not isinstance(data, dict):
        return None

    for key in keys:
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
        if isinstance(value, (int, float)):
            return str(value)
    return None


def parse_order(data: dict[str, Any], fallback: int) -> int:
    for key in ["order_index", "order", "index", "sort"]:
        value = data.get(key)
        if isinstance(value, int) and value >= 0:
            return value
        if isinstance(value, str) and value.isdigit():
            return int(value)
    return fallback


def register_volume_aliases(
    volume_lookup: dict[str, dict[str, Any]],
    volume: dict[str, Any],
    raw_volume: dict[str, Any],
) -> None:
    aliases = [volume["title"]]
    for key in ["id", "volume_id", "name", "title", "volume_title"]:
        value = raw_volume.get(key)
        if isinstance(value, (str, int, float)):
            aliases.append(str(value))
    for alias in aliases:
        volume_lookup[alias] = volume


def clean_title(title: str) -> str:
    return title.strip() or "未命名"


def strip_extension(filename: str) -> str:
    return PurePosixPath(filename).stem or filename


def natural_sort_key(value: str) -> list[Any]:
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", value)]


def should_ignore_zip_path(path: PurePosixPath) -> bool:
    normalized_parts = [part.lower() for part in path.parts]
    return (
        "__macosx" in normalized_parts
        or any(part.startswith(".") for part in normalized_parts)
        or path.name.lower() in IGNORED_NAMES
    )


def detect_common_root(paths: list[PurePosixPath]) -> str | None:
    first_parts = [path.parts[0] for path in paths if len(path.parts) > 1]
    if not first_parts:
        return None
    first = first_parts[0]
    if all(part == first for part in first_parts) and len(first_parts) == len(paths):
        return first
    return None


def remove_root_prefix(path: PurePosixPath, root_prefix: str | None) -> PurePosixPath:
    if root_prefix and path.parts and path.parts[0] == root_prefix:
        return PurePosixPath(*path.parts[1:])
    return path


def io_bytes(content: bytes):
    import io

    return io.BytesIO(content)


# ---------------------------------------------------------------------------
# Knowledge Base Import Helpers
# ---------------------------------------------------------------------------

# Knowledge import supports a broader set of formats than work import.
KNOWLEDGE_SUPPORTED_SUFFIXES = {".txt", ".md", ".docx", ".pdf", ".doc"}
# .zip is also recognized and expanded before per-file parsing.
KNOWLEDGE_RECOGNIZED_SUFFIXES = KNOWLEDGE_SUPPORTED_SUFFIXES | {".zip"}

# Upload limits for knowledge import
KNOWLEDGE_MAX_FILE_SIZE = 25 * 1024 * 1024  # 25 MB per file
KNOWLEDGE_MAX_TOTAL_SIZE = 200 * 1024 * 1024  # 200 MB total
KNOWLEDGE_MAX_FILE_COUNT = 200  # 200 files per import


def _extract_zip_entries(
    content: bytes, filename: str, failed_files: list[str]
) -> list[tuple[str, bytes]] | None:
    """Extract entries from a zip archive, returning (relative_path, bytes) pairs.

    Returns None if the zip is unreadable.
    """
    import io

    entries: list[tuple[str, bytes]] = []
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            for info in archive.infolist():
                if info.is_dir():
                    continue
                path = PurePosixPath(info.filename)
                # Prevent path traversal (check before ignore-filter)
                if any(part == ".." for part in path.parts) or path.is_absolute():
                    failed_files.append(info.filename)
                    continue
                # Skip system / hidden files
                if should_ignore_zip_path(path) or not path.name:
                    continue
                data = archive.read(info)
                entries.append((info.filename, data))
    except zipfile.BadZipFile:
        failed_files.append(filename)
        return None
    return entries


def _parse_single_knowledge_file(
    filename: str,
    content: bytes,
    *,
    documents: list[dict[str, Any]],
    warnings: list[str],
    failed_files: list[str],
    empty_files: list[str],
    unsupported_files: list[str],
) -> None:
    """Process a single file for knowledge import."""
    path = PurePosixPath(filename)
    suffix = path.suffix.lower()

    if should_ignore_zip_path(path) or not path.name:
        return

    if suffix not in KNOWLEDGE_SUPPORTED_SUFFIXES:
        unsupported_files.append(filename)
        return

    # Parse based on file type
    text: str | None = None
    if suffix == ".pdf":
        from app.utils.document_text_extractors import extract_pdf_text

        text = extract_pdf_text(content, filename, failed_files)
        if text is None:
            warnings.append(
                f"PDF 文本提取失败，可能是扫描版或加密文件：{filename}"
            )
            return
    elif suffix == ".doc":
        from app.utils.document_text_extractors import extract_doc_text

        text = extract_doc_text(content, filename, failed_files)
        if text is None:
            warnings.append(
                f".doc 文本提取失败，文件可能已损坏或格式异常：{filename}"
            )
            return
    elif suffix == ".docx":
        text = parse_docx_text(content, filename, failed_files)
        if text is None:
            return
    else:
        # .txt, .md
        text = decode_text(content, filename, failed_files)
        if text is None:
            return

    if not text.strip():
        empty_files.append(filename)
        return

    source_type = _suffix_to_source_type(suffix)
    documents.append({
        "title": strip_extension(path.name),
        "content": text,
        "source_type": source_type,
        "source_uri": filename,
        "filename": path.name,
        "relative_path": filename,
        "extension": suffix,
        "word_count": calculate_word_count(text),
        "size": len(content),
    })


def parse_knowledge_files(
    file_entries: list[tuple[str, bytes]],
) -> dict[str, Any]:
    """Parse uploaded files into knowledge source entries.

    Supports .txt, .md, .docx, .pdf, and .zip (containing supported formats).
    .doc files are recognized but reported as unsupported.

    Returns a preview dict with:
    - documents: list of parsed document dicts
    - document_count, supported_count, unsupported_count
    - total_word_count, total_size
    - warnings, failed_files, empty_files, unsupported_files
    - can_import
    """
    warnings: list[str] = []
    failed_files: list[str] = []
    empty_files: list[str] = []
    unsupported_files: list[str] = []
    documents: list[dict[str, Any]] = []

    # Expand zip entries first
    expanded_entries: list[tuple[str, bytes]] = []
    for filename, content in file_entries:
        path = PurePosixPath(filename)
        suffix = path.suffix.lower()
        if suffix == ".zip":
            entries = _extract_zip_entries(content, filename, failed_files)
            if entries is not None:
                if not entries:
                    warnings.append(f"ZIP 文件中未找到可导入的文件：{filename}")
                else:
                    # Prefix zip internal paths with the zip name for context
                    for inner_name, inner_content in entries:
                        expanded_entries.append((inner_name, inner_content))
        else:
            expanded_entries.append((filename, content))

    for filename, content in expanded_entries:
        _parse_single_knowledge_file(
            filename,
            content,
            documents=documents,
            warnings=warnings,
            failed_files=failed_files,
            empty_files=empty_files,
            unsupported_files=unsupported_files,
        )

    # Deduplicate warnings (same message may appear multiple times)
    seen_warnings: set[str] = set()
    unique_warnings: list[str] = []
    for warning in warnings:
        if warning not in seen_warnings:
            seen_warnings.add(warning)
            unique_warnings.append(warning)

    if not documents and not failed_files and not unsupported_files:
        unique_warnings.append("未找到可导入的文件。支持 .txt、.md、.docx、.doc、.pdf 格式。")

    if empty_files:
        unique_warnings.append(f"发现 {len(empty_files)} 个空文件，已跳过。")

    total_size = sum(doc["size"] for doc in documents)

    return {
        "documents": documents,
        "document_count": len(documents),
        "supported_count": len(documents),
        "unsupported_count": len(unsupported_files),
        "total_word_count": sum(doc["word_count"] for doc in documents),
        "total_size": total_size,
        "warnings": unique_warnings,
        "failed_files": failed_files,
        "empty_files": empty_files,
        "unsupported_files": unsupported_files,
        "can_import": len(documents) > 0,
    }


def _suffix_to_source_type(suffix: str) -> str:
    mapping = {
        ".txt": "file",
        ".md": "file",
        ".docx": "file",
        ".pdf": "file",
        ".doc": "file",
    }
    return mapping.get(suffix, "file")
