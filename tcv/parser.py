from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Message:
    id: int
    type: str
    date: datetime
    sender: str
    sender_id: str
    text: str
    reply_to_id: Optional[int]
    media_type: Optional[str]
    duration_seconds: Optional[int]
    forwarded_from: Optional[str]
    reactions: list = field(default_factory=list)  # [{"emoji": "👍", "count": 3}]


def _extract_text(field) -> str:
    if isinstance(field, str):
        return field
    if isinstance(field, list):
        parts = []
        hrefs = []
        for part in field:
            if isinstance(part, str):
                parts.append(part)
            elif isinstance(part, dict):
                parts.append(part.get('text', ''))
                # Collect hrefs so _link_freq can find them;
                # nlp.clean() strips URLs before word analysis
                if part.get('href'):
                    hrefs.append(part['href'])
        text = ''.join(parts)
        if hrefs:
            text += ' ' + ' '.join(hrefs)
        return text
    return ''


def _load_json(path: str) -> tuple[list[Message], str]:
    try:
        with open(path, encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        sys.exit(f'error: file not found: {path}')
    except json.JSONDecodeError as e:
        sys.exit(f'error: invalid JSON: {e}')

    chat_name = data.get('name', 'Unknown Chat')
    messages: list[Message] = []

    for raw in data.get('messages', []):
        try:
            date = datetime.fromisoformat(raw.get('date', ''))
        except (ValueError, TypeError):
            continue

        raw_rx = raw.get('reactions') or []
        reactions = [
            {'emoji': r['emoji'], 'count': r.get('count', 1)}
            for r in raw_rx
            if r.get('type') == 'emoji' and r.get('emoji')
        ]

        messages.append(Message(
            id=raw.get('id', 0),
            type=raw.get('type', ''),
            date=date,
            sender=raw.get('from') or 'Unknown',
            sender_id=str(raw.get('from_id', '')),
            text=_extract_text(raw.get('text', '')),
            reply_to_id=raw.get('reply_to_message_id'),
            media_type=raw.get('media_type'),
            duration_seconds=raw.get('duration_seconds'),
            forwarded_from=raw.get('forwarded_from'),
            reactions=reactions,
        ))

    return messages, chat_name


def load(path: str) -> tuple[list[Message], str]:
    """Load a Telegram export. Accepts:
    - a directory (HTML export with messages*.html, or JSON export with result.json)
    - a single .html file
    - a .json file
    """
    if os.path.isdir(path):
        json_path = os.path.join(path, 'result.json')
        if os.path.isfile(json_path):
            return _load_json(json_path)
        from tcv.html_parser import load_directory
        return load_directory(path)

    if path.lower().endswith('.html'):
        from tcv.html_parser import parse_file
        return parse_file(path, {})

    return _load_json(path)
