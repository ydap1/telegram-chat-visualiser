from __future__ import annotations

import base64
import io
import sys
from collections import Counter
from datetime import date

import matplotlib.pyplot as plt

from tcv import nlp, style
from tcv.parser import Message


def _fig_to_b64(fig: plt.Figure) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format='png', facecolor=fig.get_facecolor())
    buf.seek(0)
    b64 = base64.b64encode(buf.read()).decode()
    plt.close(fig)
    return b64


def _chart_section(title: str, b64: str, wide: bool = False) -> str:
    width = '100%' if wide else '48%'
    return f'''
    <div class="chart" style="width:{width}">
      <h3>{title}</h3>
      <img src="data:image/png;base64,{b64}" alt="{title}">
    </div>'''


def _overview_card(value: str, label: str) -> str:
    return f'<div class="card"><span class="val">{value}</span><span class="lbl">{label}</span></div>'


def generate(messages: list[Message], chat_name: str) -> str:
    from tcv.commands import heatmap, timeline, emoji_cmd, links

    style.apply()
    nlp.ensure_nltk_data()

    text_msgs = [m for m in messages if m.type == 'message']
    if not text_msgs:
        sys.exit('error: no messages found')

    dates = [m.date for m in text_msgs]
    first, last = min(dates).date(), max(dates).date()
    span = (last - first).days + 1
    senders = sorted({m.sender for m in text_msgs})

    # --- word frequencies for top words chart ---
    stop = nlp.stopword_set()
    all_words = nlp.tokenize_and_filter(
        ' '.join(nlp.clean(m.text) for m in text_msgs), stop
    )
    word_freq = Counter(all_words)
    top_words = word_freq.most_common(20)

    # --- per-person message counts ---
    sender_counts = Counter(m.sender for m in text_msgs)

    # ----- generate charts -----
    fig_timeline = timeline.make_figure(messages, period='week')
    b64_timeline = _fig_to_b64(fig_timeline)

    fig_heatmap = heatmap.make_figure(messages)
    b64_heatmap = _fig_to_b64(fig_heatmap)

    # top words bar
    fig_words, ax = plt.subplots(figsize=(10, 5))
    words_list = [w for w, _ in reversed(top_words)]
    words_vals = [c for _, c in reversed(top_words)]
    colors_w = [style.PALETTE[i % len(style.PALETTE)] for i in range(len(words_list))]
    ax.barh(words_list, words_vals, color=colors_w, alpha=0.85)
    ax.set_xlabel('occurrences')
    ax.set_title('Top 20 words')
    ax.grid(axis='x', alpha=0.4)
    fig_words.tight_layout()
    b64_words = _fig_to_b64(fig_words)

    # per-person message count bar
    top_senders = sender_counts.most_common(15)
    fig_people, ax = plt.subplots(figsize=(10, max(4, len(top_senders) * 0.4)))
    pnames = [s for s, _ in reversed(top_senders)]
    pvals = [c for _, c in reversed(top_senders)]
    pcolors = [style.PALETTE[i % len(style.PALETTE)] for i in range(len(pnames))]
    ax.barh(pnames, pvals, color=pcolors, alpha=0.85)
    ax.set_xlabel('messages')
    ax.set_title('Messages per person')
    ax.grid(axis='x', alpha=0.4)
    fig_people.tight_layout()
    b64_people = _fig_to_b64(fig_people)

    # emoji chart
    emoji_counts = emoji_cmd.extract(messages)
    fig_emoji = emoji_cmd.make_figure(emoji_counts, n=20)
    b64_emoji = _fig_to_b64(fig_emoji)

    # links chart
    link_counts = links.extract(messages)
    fig_links = links.make_figure(link_counts, n=15)
    b64_links = _fig_to_b64(fig_links)

    # optional sentiment
    b64_sentiment = None
    try:
        from tcv.commands import sentiment as sent_mod
        fig_sent = sent_mod.make_figure(messages, window=7)
        b64_sentiment = _fig_to_b64(fig_sent)
    except SystemExit:
        pass  # vaderSentiment not installed

    # ----- assemble HTML -----
    total_media = sum(1 for m in messages if m.type == 'message' and m.media_type)
    total_voice_min = sum(
        (m.duration_seconds or 0) for m in messages
        if m.type == 'message' and m.media_type == 'voice_message'
    ) // 60

    cards_html = ''.join([
        _overview_card(f'{len(text_msgs):,}', 'messages'),
        _overview_card(str(len(senders)), 'participants'),
        _overview_card(f'{span:,}', 'days active'),
        _overview_card(f'{total_media:,}', 'media files'),
        _overview_card(f'{total_voice_min:,}', 'voice minutes'),
        _overview_card(f'{len(word_freq):,}', 'unique words'),
    ])

    charts_html = (
        _chart_section('Weekly message volume', b64_timeline, wide=True)
        + _chart_section('Activity heatmap', b64_heatmap, wide=True)
        + _chart_section('Messages per person', b64_people)
        + _chart_section('Top words', b64_words)
        + _chart_section('Emoji usage', b64_emoji)
        + _chart_section('Most shared domains', b64_links)
    )
    if b64_sentiment:
        charts_html += _chart_section('Sentiment over time', b64_sentiment, wide=True)

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>{chat_name} — Chat Analysis</title>
  <style>
    *{{box-sizing:border-box;margin:0;padding:0}}
    body{{background:#0f0f1a;color:#e0e0e0;font-family:system-ui,-apple-system,sans-serif;padding:24px}}
    h1{{font-size:1.8rem;font-weight:700;margin-bottom:4px}}
    .sub{{color:#8888aa;font-size:.9rem;margin-bottom:28px}}
    .cards{{display:flex;flex-wrap:wrap;gap:16px;margin-bottom:32px}}
    .card{{background:#1a1a2e;border:1px solid #2a2a4a;border-radius:10px;
           padding:16px 22px;min-width:130px;display:flex;flex-direction:column;align-items:center}}
    .val{{font-size:1.6rem;font-weight:700;color:#4FC3F7}}
    .lbl{{font-size:.75rem;color:#8888aa;margin-top:4px;text-transform:uppercase;letter-spacing:.05em}}
    .charts{{display:flex;flex-wrap:wrap;gap:24px}}
    .chart{{background:#1a1a2e;border:1px solid #2a2a4a;border-radius:10px;padding:18px}}
    .chart h3{{font-size:.95rem;font-weight:600;color:#c0c0d8;margin-bottom:12px}}
    .chart img{{width:100%;height:auto;display:block;border-radius:6px}}
    h2{{font-size:1.1rem;color:#8888aa;font-weight:500;margin:24px 0 12px;
        text-transform:uppercase;letter-spacing:.08em;font-size:.8rem}}
  </style>
</head>
<body>
  <h1>{chat_name}</h1>
  <p class="sub">{first} → {last} &nbsp;·&nbsp; exported by telegram-chat-visualiser</p>

  <h2>Overview</h2>
  <div class="cards">{cards_html}</div>

  <h2>Charts</h2>
  <div class="charts">{charts_html}</div>
</body>
</html>'''

    return html


def register(sub) -> None:
    p = sub.add_parser('dashboard', help='generate a self-contained HTML analytics report')
    p.add_argument('input_file', help='Telegram JSON export')
    p.add_argument('-o', '--output', default='dashboard.html',
                   help='output HTML path (default: dashboard.html)')
    p.set_defaults(func=run)


def run(args) -> None:
    from tcv.parser import load
    messages, chat_name = load(args.input_file)
    html = generate(messages, chat_name)
    with open(args.output, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'saved to {args.output}')
