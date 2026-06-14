from __future__ import annotations

import sys
from collections import defaultdict
from datetime import date, timedelta

import matplotlib.pyplot as plt
import matplotlib.dates as mdates

from tcv import style
from tcv.parser import Message


def _rolling_avg(series: list[tuple[date, float]], window: int) -> list[tuple[date, float]]:
    if not series:
        return []
    dates = [d for d, _ in series]
    vals = [v for _, v in series]
    result = []
    for i in range(len(vals)):
        lo = max(0, i - window + 1)
        result.append((dates[i], sum(vals[lo:i + 1]) / (i - lo + 1)))
    return result


def make_figure(messages: list[Message], window: int = 7) -> plt.Figure:
    try:
        from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    except ImportError:
        sys.exit('error: vaderSentiment is required — pip install vaderSentiment')

    style.apply()

    analyzer = SentimentIntensityAnalyzer()
    daily: dict[date, list[float]] = defaultdict(list)

    for m in messages:
        if m.type != 'message' or not m.text.strip():
            continue
        score = analyzer.polarity_scores(m.text)['compound']
        daily[m.date.date()].append(score)

    if not daily:
        fig, ax = plt.subplots()
        ax.text(0.5, 0.5, 'no messages to analyse', ha='center', va='center', transform=ax.transAxes)
        return fig

    raw = sorted((d, sum(v) / len(v)) for d, v in daily.items())
    smoothed = _rolling_avg(raw, window)

    dates_raw = [d for d, _ in raw]
    vals_raw = [v for _, v in raw]
    dates_sm = [d for d, _ in smoothed]
    vals_sm = [v for _, v in smoothed]

    fig, ax = plt.subplots(figsize=(14, 5))

    ax.scatter(dates_raw, vals_raw, s=6, alpha=0.25, color=style.PALETTE[0], zorder=1)
    ax.plot(dates_sm, vals_sm, color=style.PALETTE[0], linewidth=2, zorder=2, label=f'{window}-day avg')
    ax.axhline(0, color=style.BORDER, linewidth=1, linestyle='--')

    ax.fill_between(dates_sm, vals_sm, 0,
                    where=[v >= 0 for v in vals_sm], alpha=0.15, color=style.PALETTE[1])
    ax.fill_between(dates_sm, vals_sm, 0,
                    where=[v < 0 for v in vals_sm], alpha=0.15, color=style.PALETTE[3])

    ax.set_ylabel('sentiment (−1 negative → +1 positive)')
    ax.set_ylim(-1, 1)
    ax.set_title('Chat sentiment over time')
    ax.legend()
    ax.grid(axis='y', alpha=0.4)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
    fig.autofmt_xdate(rotation=30)
    fig.tight_layout()
    return fig


def register(sub) -> None:
    p = sub.add_parser('sentiment', help='sentiment analysis over time (requires vaderSentiment)')
    p.add_argument('input_file', help='Telegram JSON export')
    p.add_argument('--window', type=int, default=7,
                   help='rolling average window in days (default: 7)')
    p.add_argument('-o', '--output', default='sentiment.png',
                   help='output PNG path (default: sentiment.png)')
    p.set_defaults(func=run)


def run(args) -> None:
    from tcv.parser import load
    messages, _ = load(args.input_file)
    fig = make_figure(messages, window=args.window)
    fig.savefig(args.output)
    plt.close(fig)
    print(f'saved to {args.output}')
