from __future__ import annotations

import re
import sys
from collections import Counter
from urllib.parse import urlparse

import matplotlib.pyplot as plt

from tcv import style
from tcv.parser import Message

_URL_RE = re.compile(r'https?://[^\s<>"{}|\\^`\[\]]+')


def extract(messages: list[Message]) -> Counter:
    counts: Counter[str] = Counter()
    for m in messages:
        if m.type != 'message':
            continue
        for url in _URL_RE.findall(m.text):
            try:
                domain = urlparse(url).netloc.lower().lstrip('www.')
                if domain:
                    counts[domain] += 1
            except ValueError:
                pass
    return counts


def make_figure(counts: Counter, n: int = 20) -> plt.Figure:
    style.apply()

    top = counts.most_common(n)
    if not top:
        fig, ax = plt.subplots()
        ax.text(0.5, 0.5, 'no links found', ha='center', va='center', transform=ax.transAxes)
        return fig

    domains = [d for d, _ in reversed(top)]
    vals = [c for _, c in reversed(top)]

    fig, ax = plt.subplots(figsize=(9, max(4, len(domains) * 0.35)))
    colors = [style.PALETTE[i % len(style.PALETTE)] for i in range(len(domains))]
    bars = ax.barh(domains, vals, color=colors, alpha=0.85)

    for bar, val in zip(bars, vals):
        ax.text(val + max(vals) * 0.01, bar.get_y() + bar.get_height() / 2,
                str(val), va='center', fontsize=8, color=style.MUTED)

    ax.set_xlabel('links shared')
    ax.set_title(f'Top {n} shared domains')
    ax.grid(axis='x', alpha=0.4)
    fig.tight_layout()
    return fig


def register(sub) -> None:
    p = sub.add_parser('links', help='most shared link domains')
    p.add_argument('input_file', help='Telegram JSON export')
    p.add_argument('-n', '--top', type=int, default=20,
                   help='number of top domains to show (default: 20)')
    p.add_argument('-o', '--output', default='links.png',
                   help='output PNG path (default: links.png)')
    p.set_defaults(func=run)


def run(args) -> None:
    from tcv.parser import load
    messages, _ = load(args.input_file)
    counts = extract(messages)

    if not counts:
        sys.exit('error: no URLs found in messages')

    print(f'Found {sum(counts.values())} links from {len(counts)} unique domains')
    for domain, count in counts.most_common(10):
        print(f'  {domain}  {count}')

    fig = make_figure(counts, n=args.top)
    fig.savefig(args.output)
    plt.close(fig)
    print(f'saved to {args.output}')
