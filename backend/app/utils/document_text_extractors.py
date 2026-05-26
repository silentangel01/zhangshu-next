"""Document text extractors for knowledge base import.

Provides PDF text extraction using pypdf and .doc (legacy Word binary)
text extraction using olefile. Scanned PDFs (image-only) will produce
empty or minimal text; OCR is not supported in this phase.
"""

from __future__ import annotations

import logging
import struct

logger = logging.getLogger(__name__)


def extract_pdf_text(content: bytes, filename: str, failed_files: list[str]) -> str | None:
    """Extract text from a PDF file.

    Args:
        content: Raw bytes of the PDF file.
        filename: Original filename for error reporting.
        failed_files: List to append filename to on failure.

    Returns:
        Extracted text, or None if extraction failed.
    """
    try:
        from pypdf import PdfReader
    except ImportError:
        failed_files.append(filename)
        logger.warning("pypdf 未安装，无法提取 PDF 文本：%s", filename)
        return None

    import io

    try:
        reader = PdfReader(io.BytesIO(content))
    except Exception:
        failed_files.append(filename)
        logger.warning("PDF 文件无法读取（可能已损坏或加密）：%s", filename)
        return None

    if reader.is_encrypted:
        failed_files.append(filename)
        logger.warning("PDF 文件已加密，无法提取文本：%s", filename)
        return None

    paragraphs: list[str] = []
    try:
        for page in reader.pages:
            text = page.extract_text()
            if text:
                paragraphs.append(text)
    except Exception:
        failed_files.append(filename)
        logger.warning("PDF 文本提取过程中出错：%s", filename)
        return None

    result = "\n\n".join(paragraphs)
    if not result.strip():
        failed_files.append(filename)
        logger.warning(
            "PDF 文本提取为空，可能是扫描版或加密文件：%s", filename
        )
        return None

    return result


def extract_doc_text(content: bytes, filename: str, failed_files: list[str]) -> str | None:
    """Extract text from a legacy .doc (Word Binary) file.

    Uses the olefile library to read the OLE2 compound document structure,
    then parses the Word binary format (FIB + piece table) to extract text.

    Args:
        content: Raw bytes of the .doc file.
        filename: Original filename for error reporting.
        failed_files: List to append filename to on failure.

    Returns:
        Extracted text, or None if extraction failed.
    """
    try:
        import olefile
    except ImportError:
        failed_files.append(filename)
        logger.warning("olefile 未安装，无法提取 .doc 文本：%s", filename)
        return None

    import io

    # Validate OLE2 signature
    if len(content) < 512 or content[:8] != b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1":
        failed_files.append(filename)
        logger.warning("不是有效的 .doc 文件（缺少 OLE2 签名）：%s", filename)
        return None

    try:
        ole = olefile.OleFileIO(io.BytesIO(content))
    except Exception:
        failed_files.append(filename)
        logger.warning(".doc 文件无法读取（可能已损坏）：%s", filename)
        return None

    try:
        return _extract_doc_text_from_ole(ole, filename, failed_files)
    finally:
        ole.close()


def _extract_doc_text_from_ole(
    ole, filename: str, failed_files: list[str]
) -> str | None:
    """Extract text from an opened OLE2 container."""
    if not ole.exists("WordDocument"):
        failed_files.append(filename)
        logger.warning(".doc 文件缺少 WordDocument 流：%s", filename)
        return None

    word_stream = ole.openstream("WordDocument").read()
    if len(word_stream) < 32:
        failed_files.append(filename)
        return None

    # --- Parse FIB (File Information Block) ---
    try:
        w_ident = struct.unpack_from("<H", word_stream, 0)[0]
        if w_ident != 0xA5EC:
            failed_files.append(filename)
            logger.warning(".doc FIB 标识无效：%s", filename)
            return None

        flags = struct.unpack_from("<H", word_stream, 0x000A)[0]
        f_complex = (flags >> 2) & 1
        which_table = "1Table" if (flags & 0x0200) else "0Table"

        # ccpText at offset 0x004C
        ccp_text = struct.unpack_from("<i", word_stream, 0x004C)[0]

        if ccp_text <= 0:
            failed_files.append(filename)
            logger.warning(".doc 文件文本长度为 0：%s", filename)
            return None

        # fcClx and lcbClx — offset depends on FIB version
        n_fib = struct.unpack_from("<H", word_stream, 2)[0]

        if n_fib >= 0x0101:
            # Word 2003+ (FibRgFcLcb2003)
            fc_clx_offset = 0x01A2
            lcb_clx_offset = 0x01A6
        else:
            # Word 97 (FibRgFcLcb97)
            fc_clx_offset = 0x01A2
            lcb_clx_offset = 0x01A6

        fc_clx = struct.unpack_from("<I", word_stream, fc_clx_offset)[0]
        lcb_clx = struct.unpack_from("<I", word_stream, lcb_clx_offset)[0]
    except struct.error:
        failed_files.append(filename)
        logger.warning(".doc FIB 解析失败：%s", filename)
        return None

    # --- Read table stream and find piece table ---
    if not ole.exists(which_table):
        # Fallback: try scanning WordDocument for text
        return _scan_doc_stream_for_text(word_stream, ccp_text, filename, failed_files)

    try:
        table_stream = ole.openstream(which_table).read()
    except Exception:
        return _scan_doc_stream_for_text(word_stream, ccp_text, filename, failed_files)

    if fc_clx + lcb_clx > len(table_stream) or lcb_clx < 4:
        return _scan_doc_stream_for_text(word_stream, ccp_text, filename, failed_files)

    # Parse CLX to find piece table (type 0x02)
    piece_table_data = _find_piece_table(table_stream[fc_clx : fc_clx + lcb_clx])
    if piece_table_data is None:
        return _scan_doc_stream_for_text(word_stream, ccp_text, filename, failed_files)

    # --- Extract text from piece table ---
    text = _extract_text_from_piece_table(
        piece_table_data, word_stream, ccp_text
    )

    if text and text.strip():
        return _clean_doc_text(text)

    # Fallback to stream scanning
    return _scan_doc_stream_for_text(word_stream, ccp_text, filename, failed_files)


def _find_piece_table(clx_data: bytes) -> bytes | None:
    """Find the piece table (type 0x02) within CLX data."""
    pos = 0
    while pos < len(clx_data):
        if pos >= len(clx_data):
            break
        entry_type = clx_data[pos]
        if entry_type == 0x01:
            # ClxRgPrc — skip: 1 byte type + 2 bytes cb + cb bytes
            if pos + 3 > len(clx_data):
                break
            cb = struct.unpack_from("<H", clx_data, pos + 1)[0]
            pos += 3 + cb
        elif entry_type == 0x02:
            # Piece table
            if pos + 5 > len(clx_data):
                return None
            lcb = struct.unpack_from("<I", clx_data, pos + 1)[0]
            return clx_data[pos + 5 : pos + 5 + lcb]
        else:
            break
    return None


def _extract_text_from_piece_table(
    piece_data: bytes,
    word_stream: bytes,
    ccp_text: int,
) -> str | None:
    """Extract text using the piece table.

    Piece table structure:
    - (n+1) CPs as uint32: CP[0]..CP[n]
    - n PCD entries (8 bytes each)
    """
    if len(piece_data) < 12:
        return None

    # Determine n: piece_data has (n+1) uint32 CPs + n * 8-byte PCDs
    # Total = 4*(n+1) + 8*n = 12n + 4
    # So n = (len(piece_data) - 4) / 12
    n = (len(piece_data) - 4) // 12
    if n <= 0:
        return None

    # Read CPs
    cps = []
    for i in range(n + 1):
        cp = struct.unpack_from("<I", piece_data, i * 4)[0]
        cps.append(cp)

    # Read PCDs and extract text
    pcd_offset = (n + 1) * 4
    result_chars: list[str] = []
    chars_remaining = ccp_text

    for i in range(n):
        if chars_remaining <= 0:
            break
        if pcd_offset + (i + 1) * 8 > len(piece_data):
            break

        pcd_start = pcd_offset + i * 8
        # PCD structure: 2 bytes flags, 4 bytes fc, 2 bytes prm
        fc_compressed = struct.unpack_from("<I", piece_data, pcd_start + 2)[0]

        cp_start = cps[i]
        cp_end = cps[i + 1]
        char_count = cp_end - cp_start
        if char_count <= 0:
            continue

        is_compressed = bool(fc_compressed & 0x40000000)
        fc = fc_compressed & 0x3FFFFFFF

        if is_compressed:
            # CP1252 (single-byte), fc is divided by 2
            byte_offset = fc // 2
            byte_count = min(char_count, chars_remaining)
            if byte_offset + byte_count > len(word_stream):
                break
            raw = word_stream[byte_offset : byte_offset + byte_count]
            try:
                text = raw.decode("cp1252", errors="replace")
            except Exception:
                text = raw.decode("latin-1", errors="replace")
        else:
            # UTF-16LE (double-byte)
            byte_offset = fc
            byte_count = min(char_count, chars_remaining) * 2
            if byte_offset + byte_count > len(word_stream):
                break
            raw = word_stream[byte_offset : byte_offset + byte_count]
            try:
                text = raw.decode("utf-16-le", errors="replace")
            except Exception:
                text = ""

        result_chars.append(text)
        chars_remaining -= len(text)

    if not result_chars:
        return None

    return "".join(result_chars)


def _scan_doc_stream_for_text(
    word_stream: bytes,
    ccp_text: int,
    filename: str,
    failed_files: list[str],
) -> str | None:
    """Fallback: scan WordDocument stream for readable text sequences.

    Used when the FIB or piece table cannot be parsed.
    Tries UTF-16LE first, then CP1252.
    """
    # Try UTF-16LE decoding of the text region
    # Typical text starts at a sector boundary after the FIB
    for start_offset in range(0x0400, min(len(word_stream), 0x10000), 0x0200):
        remaining = word_stream[start_offset:]
        byte_count = min(ccp_text * 2, len(remaining))
        if byte_count < 20:
            continue
        try:
            text = remaining[:byte_count].decode("utf-16-le", errors="replace")
            # Check if it contains enough readable characters
            readable = sum(1 for c in text if c.isprintable() or c in "\n\r\t")
            if readable > len(text) * 0.5 and len(text.strip()) > 10:
                return _clean_doc_text(text[:ccp_text])
        except Exception:
            continue

    # Last resort: try CP1252
    for start_offset in range(0x0400, min(len(word_stream), 0x10000), 0x0200):
        remaining = word_stream[start_offset:]
        byte_count = min(ccp_text, len(remaining))
        if byte_count < 20:
            continue
        try:
            text = remaining[:byte_count].decode("cp1252", errors="replace")
            readable = sum(1 for c in text if c.isprintable() or c in "\n\r\t")
            if readable > len(text) * 0.6 and len(text.strip()) > 10:
                return _clean_doc_text(text[:ccp_text])
        except Exception:
            continue

    failed_files.append(filename)
    logger.warning(".doc 文本提取失败（无法解析文档结构）：%s", filename)
    return None


def _clean_doc_text(text: str) -> str:
    """Clean extracted .doc text: normalise whitespace and control chars."""
    # Replace Word-specific control characters
    text = text.replace("\x07", "")   # Cell/row marks in tables
    text = text.replace("\x0b", "\n")  # Vertical tab → newline
    text = text.replace("\x0c", "\n")  # Form feed / page break
    text = text.replace("\x01", "")    # Field begin
    text = text.replace("\x13", "")    # Field begin
    text = text.replace("\x14", "")    # Field separator
    text = text.replace("\x15", "")    # Field end
    text = text.replace("\r", "\n")    # Normalise CR

    # Collapse multiple newlines
    import re
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Strip lines
    lines = [line.strip() for line in text.split("\n")]
    return "\n".join(lines).strip()
