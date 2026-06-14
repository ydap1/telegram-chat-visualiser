"""Generate a multi-page PDF analytics report using matplotlib."""
from __future__ import annotations

import base64
import io
import warnings
from typing import Optional

# matplotlib's default font can't render emoji glyphs; suppress the noise
warnings.filterwarnings('ignore', message='Glyph .* missing from font')

import numpy as np

from tcv import style

_BG     = '#0f0f1a'
_SURF   = '#1a1a2e'
_BORDER = '#2a2a4a'
_FG     = '#e0e0e0'
_DIM    = '#8888aa'
_ACCENT = '#4FC3F7'
_PAGE_W = 11.69   # A4 landscape width (inches)
_PAGE_H = 8.27    # A4 landscape height (inches)


def _dark_fig(w=_PAGE_W, h=_PAGE_H):
    import matplotlib.pyplot as plt
    fig = plt.figure(figsize=(w, h), facecolor=_BG)
    return fig


def _b64_to_array(b64: str):
    from PIL import Image
    data = base64.b64decode(b64)
    return np.array(Image.open(io.BytesIO(data)))


def _page_overview(pdf, chat_name: str, first_date, last_date, cards: list[tuple[str, str]]):
    import matplotlib.pyplot as plt
    fig = _dark_fig()
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_facecolor(_BG)
    ax.axis('off')

    ax.text(0.5, 0.95, chat_name, transform=ax.transAxes,
            ha='center', va='top', fontsize=26, fontweight='bold', color=_FG)
    ax.text(0.5, 0.87, f'{first_date}  →  {last_date}', transform=ax.transAxes,
            ha='center', va='top', fontsize=13, color=_DIM)

    cols = 4
    cw, ch = 0.2, 0.22
    xs = 0.05 + np.arange(cols) * (cw + 0.03)
    ys = [0.68, 0.38]

    for i, (label, value) in enumerate(cards):
        x = xs[i % cols]
        y = ys[i // cols]
        rect = plt.Rectangle((x, y - ch), cw, ch,
                              transform=ax.transAxes,
                              facecolor=_SURF, edgecolor=_BORDER, linewidth=1, zorder=2)
        ax.add_patch(rect)
        ax.text(x + cw / 2, y - ch * 0.38, str(value),
                transform=ax.transAxes, ha='center', va='center',
                fontsize=19, fontweight='bold', color=_ACCENT, zorder=3)
        ax.text(x + cw / 2, y - ch * 0.76, label,
                transform=ax.transAxes, ha='center', va='center',
                fontsize=9, color=_DIM, zorder=3)

    pdf.savefig(fig, bbox_inches='tight')
    plt.close(fig)


def _page_image(pdf, b64: str, title: str):
    import matplotlib.pyplot as plt
    fig = _dark_fig()
    ax = fig.add_subplot(111)
    ax.set_facecolor(_BG)
    ax.imshow(_b64_to_array(b64))
    ax.axis('off')
    ax.set_title(title, color=_FG, fontsize=13, pad=8)
    pdf.savefig(fig, bbox_inches='tight', facecolor=_BG)
    plt.close(fig)


def _page_heatmap(pdf, hm_data: list[list[int]]):
    import matplotlib.pyplot as plt
    style.apply()
    days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    data = np.array(hm_data, dtype=float)

    fig, ax = plt.subplots(figsize=(_PAGE_W, _PAGE_H))
    im = ax.imshow(data, aspect='auto', cmap='Blues', interpolation='nearest')
    ax.set_xticks(range(24))
    ax.set_xticklabels([f'{h:02d}' for h in range(24)], fontsize=8)
    ax.set_yticks(range(7))
    ax.set_yticklabels(days)
    ax.set_title('Activity Heatmap — hour × day of week', pad=8)
    plt.colorbar(im, ax=ax, label='messages')
    fig.tight_layout()
    pdf.savefig(fig, facecolor=fig.get_facecolor())
    plt.close(fig)


def _page_top_words(pdf, word_freq: list[tuple[str, int]], n: int = 20):
    import matplotlib.pyplot as plt
    style.apply()
    data = word_freq[:n]
    if not data:
        return
    words  = [w for w, _ in data]
    counts = [c for _, c in data]
    max_c  = counts[0] if counts else 1

    fig, ax = plt.subplots(figsize=(_PAGE_W, _PAGE_H))
    bars = ax.barh(range(len(words)), counts, color=_ACCENT)
    ax.set_yticks(range(len(words)))
    ax.set_yticklabels(words, fontsize=11)
    ax.invert_yaxis()
    ax.set_title(f'Top {n} Words (meaningful)', pad=8)
    ax.set_xlabel('occurrences')
    for bar, c in zip(bars, counts):
        ax.text(bar.get_width() + max_c * 0.01,
                bar.get_y() + bar.get_height() / 2,
                str(c), va='center', fontsize=9, color=_FG)
    fig.tight_layout()
    pdf.savefig(fig, facecolor=fig.get_facecolor())
    plt.close(fig)


def _page_stats_table(pdf, rows: list[dict]):
    import matplotlib.pyplot as plt
    style.apply()
    if not rows:
        return

    col_labels = ['Sender', 'Msgs', 'Words', 'Avg', 'Media', 'Voice min', 'Peak', 'Top word']
    cell_data = [
        [r['sender'], f"{r['messages']:,}", f"{r['words']:,}",
         str(r['avg']), str(r['media']), str(r['voice_min']), r['peak'], r['top_word']]
        for r in rows[:25]
    ]

    row_h  = 0.36
    fig_h  = max(4.0, len(cell_data) * row_h + 1.5)
    fig, ax = plt.subplots(figsize=(_PAGE_W, fig_h))
    ax.axis('off')
    ax.set_title('Statistics per Person', pad=8)

    tbl = ax.table(cellText=cell_data, colLabels=col_labels,
                   cellLoc='center', loc='center')
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(9)
    tbl.auto_set_column_width(range(len(col_labels)))

    for (r, c), cell in tbl.get_celld().items():
        if r == 0:
            cell.set_facecolor(_BORDER)
            cell.set_text_props(color=_FG, weight='bold')
        elif r % 2 == 0:
            cell.set_facecolor('#0d0d18')
            cell.set_text_props(color=_FG)
        else:
            cell.set_facecolor(_SURF)
            cell.set_text_props(color=_FG)
        cell.set_edgecolor(_BORDER)

    fig.tight_layout()
    pdf.savefig(fig, facecolor=fig.get_facecolor())
    plt.close(fig)


def _page_emoji_links(pdf, emoji_freq, link_freq, reaction_freq=None):
    import matplotlib.pyplot as plt
    style.apply()

    panels = [('Emoji Usage', emoji_freq)]
    if reaction_freq:
        panels.append(('Message Reactions', reaction_freq))
    panels.append(('Top Shared Domains', link_freq))

    fig, axes = plt.subplots(1, len(panels), figsize=(_PAGE_W, _PAGE_H))
    if len(panels) == 1:
        axes = [axes]

    for ax, (title, data) in zip(axes, panels):
        ax.set_title(title, pad=8)
        if title == 'Top Shared Domains':
            if data:
                domains = [d for d, _ in data[:15]]
                counts  = [c for _, c in data[:15]]
                ax.barh(range(len(domains)), counts, color=style.PALETTE[2])
                ax.set_yticks(range(len(domains)))
                ax.set_yticklabels(domains, fontsize=9)
                ax.invert_yaxis()
            else:
                ax.axis('off')
                ax.text(0.5, 0.5, 'No links found', transform=ax.transAxes,
                        ha='center', va='center', color=_DIM)
        else:
            # Emoji grid as text
            ax.axis('off')
            y = 0.95
            for emoji, count in (data or [])[:18]:
                ax.text(0.15, y, emoji, transform=ax.transAxes, fontsize=16, va='top')
                ax.text(0.42, y + 0.01, str(count), transform=ax.transAxes,
                        va='top', fontsize=10, color=_FG)
                y -= 0.054
                if y < 0.05:
                    break

    fig.tight_layout()
    pdf.savefig(fig, facecolor=fig.get_facecolor())
    plt.close(fig)


def generate_pdf(
    path: str,
    chat_name: str,
    first_date,
    last_date,
    overview_cards: list[tuple[str, str]],
    word_freq_smart: list[tuple[str, int]],
    hm_data: list[list[int]],
    person_stats: list[dict],
    emoji_freq: list[tuple[str, int]],
    reaction_freq: list[tuple[str, int]],
    link_freq: list[tuple[str, int]],
    b64_wc: Optional[str] = None,
    b64_timeline: Optional[str] = None,
    b64_sent: Optional[str] = None,
) -> None:
    import matplotlib
    matplotlib.use('Agg')
    from matplotlib.backends.backend_pdf import PdfPages

    with PdfPages(path) as pdf:
        _page_overview(pdf, chat_name, first_date, last_date, overview_cards)

        if b64_timeline:
            _page_image(pdf, b64_timeline, 'Message Timeline — weekly')

        _page_heatmap(pdf, hm_data)

        if b64_wc:
            _page_image(pdf, b64_wc, 'Word Cloud — meaningful words')

        _page_top_words(pdf, word_freq_smart, n=20)
        _page_stats_table(pdf, person_stats)
        _page_emoji_links(pdf, emoji_freq, link_freq, reaction_freq or None)

        if b64_sent:
            _page_image(pdf, b64_sent, 'Sentiment Over Time')

        d = pdf.infodict()
        d['Title'] = f'{chat_name} — Analytics'
        d['Author'] = 'tcv'
