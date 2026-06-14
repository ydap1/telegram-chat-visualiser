from __future__ import annotations

import glob
import os
import re
import sys
from datetime import datetime
from typing import Optional

from tcv.parser import Message

_DATE_RE = re.compile(r'(\d{2})\.(\d{2})\.(\d{4}) (\d{2}):(\d{2}):(\d{2})')
_REPLY_RE = re.compile(r'go_to_message-(\d+)')


def _bs4():
    try:
        from bs4 import BeautifulSoup
        return BeautifulSoup
    except ImportError:
        sys.exit('error: beautifulsoup4 is required for HTML exports — pip install beautifulsoup4')


def _parse_dt(title: str) -> Optional[datetime]:
    m = _DATE_RE.search(title)
    if not m:
        return None
    d, mo, y, h, mi, s = m.groups()
    try:
        return datetime(int(y), int(mo), int(d), int(h), int(mi), int(s))
    except ValueError:
        return None


def _text_of(tag) -> str:
    """Get the text of a navigable string node, excluding child tag contents cleanly."""
    return ' '.join(tag.get_text(separator=' ').split())


def parse_file(path: str, state: dict) -> tuple[list[Message], str]:
    """
    Parse a single Telegram HTML export file.

    `state` is a shared dict that persists across files:
      - 'sender': last known sender name (needed for "joined" messages)
      - 'chat_name': filled on first parse
    """
    BS = _bs4()
    with open(path, encoding='utf-8') as f:
        soup = BS(f, 'html.parser')

    header = soup.find('div', class_='text bold')
    if header and not state.get('chat_name'):
        state['chat_name'] = header.get_text(strip=True)

    messages: list[Message] = []

    # AyuGram uses "message-NNN" (with hyphen) in older exports and
    # "messageNNN" (no hyphen) in newer ones — accept both.
    for div in soup.find_all('div', id=re.compile(r'^message-?\d+$')):
        classes = div.get('class', [])
        try:
            msg_id = int(re.sub(r'^message-?', '', div['id']))
        except (KeyError, ValueError):
            continue

        # Service message (date separators, join/leave events)
        if 'service' in classes:
            body = div.find('div', class_='body')
            text = body.get_text(strip=True) if body else ''
            # Skip pure date separators (they contain only a date string)
            if not re.match(r'^\d{1,2} \w+ \d{4}$', text):
                messages.append(Message(
                    id=msg_id, type='service', date=datetime(2000, 1, 1),
                    sender='', sender_id='', text=text,
                    reply_to_id=None, media_type=None,
                    duration_seconds=None, forwarded_from=None,
                ))
            state['sender'] = None
            continue

        # Regular message
        body = div.find('div', class_='body', recursive=False)
        if not body:
            continue

        # Timestamp
        date_div = body.find('div', class_='date')
        dt = _parse_dt(date_div.get('title', '')) if date_div else None
        if dt is None:
            dt = datetime(2000, 1, 1)

        # Sender — absent on "joined" follow-up messages from the same person
        from_div = body.find('div', class_='from_name', recursive=False)
        if from_div:
            sender = from_div.get_text(strip=True)
            state['sender'] = sender
        else:
            sender = state.get('sender') or 'Unknown'

        # Reply-to message ID
        reply_div = body.find('div', class_='reply_to')
        reply_to_id: Optional[int] = None
        if reply_div:
            a = reply_div.find('a')
            if a:
                m = _REPLY_RE.search(a.get('href', ''))
                reply_to_id = int(m.group(1)) if m else None

        # Forwarded-from name (first text node of the inner from_name, strips the date span)
        # CSS selector needed: class_=['a','b'] in BS4 is OR, not AND
        fwd_results = body.select('div.forwarded.body')
        fwd_body = fwd_results[0] if fwd_results else None
        forwarded_from: Optional[str] = None
        if fwd_body:
            fwd_name_div = fwd_body.find('div', class_='from_name')
            if fwd_name_div:
                # First NavigableString child only — ignores the <span> date
                from bs4 import NavigableString
                first = next(
                    (c for c in fwd_name_div.children if isinstance(c, NavigableString)),
                    None,
                )
                forwarded_from = first.strip() if first else None

        # Message text — prefer direct child .text over forwarded .text
        text_div = body.find('div', class_='text', recursive=False)
        if text_div:
            text = _text_of(text_div)
        elif fwd_body:
            fwd_text = fwd_body.find('div', class_='text')
            text = _text_of(fwd_text) if fwd_text else ''
        else:
            text = ''

        # Media type from the CSS class on the media div
        media_type: Optional[str] = None
        media_wrap = body.find('div', class_='media_wrap')
        if media_wrap:
            media_div = media_wrap.find('div', class_=re.compile(r'^media '))
            if media_div:
                for cls in media_div.get('class', []):
                    if cls.startswith('media_') and cls != 'media_wrap':
                        media_type = cls[len('media_'):]
                        break

        # Duration for audio/voice (format "0:30" or "1:23" in the status div)
        duration_seconds: Optional[int] = None
        if media_type in ('audio', 'voice', 'video_file'):
            status = body.find('div', class_='status')
            if status:
                dm = re.search(r'(\d+):(\d{2})', status.get_text())
                if dm:
                    duration_seconds = int(dm.group(1)) * 60 + int(dm.group(2))

        messages.append(Message(
            id=msg_id,
            type='message',
            date=dt,
            sender=sender,
            sender_id='',
            text=text,
            reply_to_id=reply_to_id,
            media_type=media_type,
            duration_seconds=duration_seconds,
            forwarded_from=forwarded_from,
        ))

    return messages, state.get('chat_name', 'Unknown Chat')


def load_directory(path: str) -> tuple[list[Message], str]:
    files = glob.glob(os.path.join(path, 'messages*.html'))

    def _sort_key(f: str) -> int:
        m = re.search(r'messages(\d*)\.html$', os.path.basename(f))
        return int(m.group(1)) if m and m.group(1) else 0

    files = sorted(files, key=_sort_key)

    if not files:
        sys.exit(f'error: no messages*.html files found in {path}')

    state: dict = {}
    all_messages: list[Message] = []
    for f in files:
        msgs, _ = parse_file(f, state)
        all_messages.extend(msgs)

    return all_messages, state.get('chat_name', 'Unknown Chat')
