from __future__ import annotations

from collections import defaultdict

import matplotlib.pyplot as plt
import numpy as np

from tcv import style
from tcv.parser import Message

_DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']


def make_figure(messages: list[Message]) -> plt.Figure:
    style.apply()

    grid = np.zeros((7, 24), dtype=int)
    for m in messages:
        if m.type == 'message':
            grid[m.date.weekday(), m.date.hour] += 1

    fig, ax = plt.subplots(figsize=(14, 5))
    im = ax.imshow(grid, aspect='auto', cmap='YlOrRd', interpolation='nearest')
    plt.colorbar(im, ax=ax, label='messages')

    ax.set_xticks(range(24))
    ax.set_xticklabels([f'{h:02d}' for h in range(24)], fontsize=8)
    ax.set_yticks(range(7))
    ax.set_yticklabels(_DAYS)
    ax.set_xlabel('hour of day')
    ax.set_title('Activity heatmap — messages by day and hour')

    # annotate cells with counts, skip zeros
    vmax = grid.max()
    for row in range(7):
        for col in range(24):
            val = grid[row, col]
            if val == 0:
                continue
            color = 'black' if val > vmax * 0.6 else style.TEXT
            ax.text(col, row, str(val), ha='center', va='center', fontsize=6, color=color)

    fig.tight_layout()
    return fig


def register(sub) -> None:
    p = sub.add_parser('heatmap', help='activity heatmap — messages by day of week and hour')
    p.add_argument('input_file', help='Telegram JSON export')
    p.add_argument('-o', '--output', default='heatmap.png', help='output PNG path (default: heatmap.png)')
    p.set_defaults(func=run)


def run(args) -> None:
    from tcv.parser import load
    messages, _ = load(args.input_file)
    fig = make_figure(messages)
    fig.savefig(args.output)
    plt.close(fig)
    print(f'saved to {args.output}')
