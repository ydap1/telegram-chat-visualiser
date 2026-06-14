from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta

import matplotlib.pyplot as plt
import matplotlib.dates as mdates

from tcv import style
from tcv.parser import Message


def _period_key(dt, period: str) -> date:
    d = dt.date()
    if period == 'day':
        return d
    if period == 'week':
        return d - timedelta(days=d.weekday())
    # month
    return date(d.year, d.month, 1)


def make_figure(messages: list[Message], period: str = 'week', by_person: bool = False) -> plt.Figure:
    style.apply()

    text_msgs = [m for m in messages if m.type == 'message']
    if not text_msgs:
        fig, ax = plt.subplots()
        ax.text(0.5, 0.5, 'no messages', ha='center', va='center', transform=ax.transAxes)
        return fig

    if by_person:
        senders = sorted({m.sender for m in text_msgs})
        counts: dict[str, dict[date, int]] = {s: defaultdict(int) for s in senders}
        for m in text_msgs:
            counts[m.sender][_period_key(m.date, period)] += 1

        all_dates = sorted({_period_key(m.date, period) for m in text_msgs})
        fig, ax = plt.subplots(figsize=(14, 6))
        for i, sender in enumerate(senders):
            vals = [counts[sender].get(d, 0) for d in all_dates]
            ax.plot(all_dates, vals, label=sender,
                    color=style.PALETTE[i % len(style.PALETTE)], linewidth=1.5, alpha=0.9)
        ax.legend(loc='upper left', ncol=2)
    else:
        daily: dict[date, int] = defaultdict(int)
        for m in text_msgs:
            daily[_period_key(m.date, period)] += 1
        all_dates = sorted(daily)
        vals = [daily[d] for d in all_dates]

        fig, ax = plt.subplots(figsize=(14, 5))
        ax.fill_between(all_dates, vals, alpha=0.3, color=style.PALETTE[0])
        ax.plot(all_dates, vals, color=style.PALETTE[0], linewidth=1.5)

    period_label = {'day': 'Daily', 'week': 'Weekly', 'month': 'Monthly'}[period]
    ax.set_title(f'{period_label} message volume')
    ax.set_ylabel('messages')
    ax.set_xlabel('')
    ax.grid(axis='y')
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
    fig.autofmt_xdate(rotation=30)
    fig.tight_layout()
    return fig


def register(sub) -> None:
    p = sub.add_parser('timeline', help='message volume over time')
    p.add_argument('input_file', help='Telegram JSON export')
    p.add_argument('--period', choices=['day', 'week', 'month'], default='week',
                   help='grouping period (default: week)')
    p.add_argument('--by-person', action='store_true', dest='by_person',
                   help='show a separate line per sender')
    p.add_argument('-o', '--output', default='timeline.png', help='output PNG path (default: timeline.png)')
    p.set_defaults(func=run)


def run(args) -> None:
    from tcv.parser import load
    messages, _ = load(args.input_file)
    fig = make_figure(messages, period=args.period, by_person=args.by_person)
    fig.savefig(args.output)
    plt.close(fig)
    print(f'saved to {args.output}')
