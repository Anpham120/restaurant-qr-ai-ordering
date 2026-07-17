from __future__ import annotations

import codecs
import re


_CONTENT_PATTERN = re.compile(r'"content"\s*:\s*"((?:[^"\\]|\\.)*)', re.DOTALL)


def extract_streaming_content(accumulated: str) -> str:
    match = _CONTENT_PATTERN.search(accumulated)
    if not match:
        return ""
    return _decode_json_string(match.group(1))


def _decode_json_string(value: str) -> str:
    try:
        return codecs.decode(f'"{value}"', "unicode_escape")
    except (UnicodeDecodeError, ValueError):
        return value.replace("\\n", "\n").replace('\\"', '"').replace("\\\\", "\\")
