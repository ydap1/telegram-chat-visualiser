from __future__ import annotations

import base64
import io
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import date, timedelta
from typing import Optional

from tcv import nlp, style
from tcv.parser import Message

# ── emoji regex ──────────────────────────────────────────────────────────────
_EMOJI_RE = re.compile(
    r'[\U0001F300-\U0001F9FF\U0001FA00-\U0001FAFF\U00002600-\U000027BF\U00002300-\U000023FF]',
    flags=re.UNICODE,
)
_URL_RE = re.compile(r'https?://[^\s<>"{}|\\^`\[\]]+')


# ── analytics ────────────────────────────────────────────────────────────────

def _text_msgs(messages: list[Message]) -> list[Message]:
    return [m for m in messages if m.type == 'message']


def _valid_dates(msgs: list[Message]) -> list:
    return [m.date for m in msgs if m.date.year > 2001]


def _heatmap_data(msgs: list[Message]) -> list[list[int]]:
    grid = [[0] * 24 for _ in range(7)]
    for m in msgs:
        if m.date.year > 2001:
            grid[m.date.weekday()][m.date.hour] += 1
    return grid


def _timeline_data(msgs: list[Message]) -> list[tuple[str, int]]:
    counts: dict[date, int] = defaultdict(int)
    for m in msgs:
        if m.date.year > 2001:
            d = m.date.date()
            week_start = d - timedelta(days=d.weekday())
            counts[week_start] += 1
    return [(str(d), c) for d, c in sorted(counts.items())]


def _per_person(msgs: list[Message]) -> list[dict]:
    nlp.ensure_nltk_data()
    stop = nlp.extended_stopword_set()
    senders = sorted({m.sender for m in msgs})
    rows = []
    for sender in senders:
        sm = [m for m in msgs if m.sender == sender]
        voice = [m for m in sm if m.media_type == 'voice_message']
        media = [m for m in sm if m.media_type and m.media_type != 'voice_message']
        replies = [m for m in sm if m.reply_to_id]

        raw_words: list[str] = []
        filtered: list[str] = []
        for m in sm:
            toks = m.text.split()
            raw_words.extend(toks)
            filtered.extend(nlp.tokenize_and_filter(nlp.clean(m.text), stop))

        freq = Counter(filtered)
        top = freq.most_common(1)
        hour_counts = Counter(m.date.hour for m in sm if m.date.year > 2001)
        peak = f'{hour_counts.most_common(1)[0][0]:02d}:00' if hour_counts else '—'
        total_words = len(raw_words)

        rows.append({
            'sender': sender,
            'messages': len(sm),
            'words': total_words,
            'avg': round(total_words / len(sm), 1) if sm else 0,
            'vocab': len(freq),
            'media': len(media),
            'voice': len(voice),
            'voice_min': round(sum(m.duration_seconds or 0 for m in voice) / 60, 1),
            'replies': len(replies),
            'peak': peak,
            'top_word': top[0][0] if top else '—',
        })
    rows.sort(key=lambda r: r['messages'], reverse=True)
    return rows


def _word_freq(msgs: list[Message], stop: set[str]) -> list[tuple[str, int]]:
    combined = ' '.join(nlp.clean(m.text) for m in msgs if m.text)
    freq = Counter(nlp.tokenize_and_filter(combined, stop))
    return freq.most_common(500)


def _emoji_freq(msgs: list[Message]) -> list[tuple[str, int]]:
    counts: Counter[str] = Counter()
    for m in msgs:
        counts.update(_EMOJI_RE.findall(m.text))
    return counts.most_common(50)


def _reaction_freq(msgs: list[Message]) -> list[tuple[str, int]]:
    counts: Counter[str] = Counter()
    for m in msgs:
        for r in m.reactions:
            counts[r['emoji']] += r.get('count', 1)
    return counts.most_common(30)


def _link_freq(msgs: list[Message]) -> list[tuple[str, int]]:
    from urllib.parse import urlparse
    counts: Counter[str] = Counter()
    for m in msgs:
        for url in _URL_RE.findall(m.text):
            try:
                d = urlparse(url).netloc.lower().lstrip('www.')
                if d:
                    counts[d] += 1
            except ValueError:
                pass
    return counts.most_common(20)


# ── matplotlib charts → base64 ───────────────────────────────────────────────

def _fig_to_b64(fig) -> str:
    import matplotlib.pyplot as plt
    buf = io.BytesIO()
    fig.savefig(buf, format='png', facecolor=fig.get_facecolor(), bbox_inches='tight', dpi=150)
    buf.seek(0)
    b64 = base64.b64encode(buf.read()).decode()
    plt.close(fig)
    return b64


def _wordcloud_b64(freq: list[tuple[str, int]], num_words: int) -> Optional[str]:
    if not freq:
        return None
    try:
        from wordcloud import WordCloud
        wc = WordCloud(
            width=1200, height=600,
            background_color='#0f0f1a',
            colormap='cool',
            max_words=num_words,
        ).generate_from_frequencies(dict(freq[:num_words]))
        img = wc.to_image()
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        return base64.b64encode(buf.getvalue()).decode()
    except Exception:
        return None


def _timeline_b64(timeline: list[tuple[str, int]]) -> Optional[str]:
    if not timeline:
        return None
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from datetime import datetime as dt
    style.apply()
    dates = [dt.strptime(d, '%Y-%m-%d') for d, _ in timeline]
    vals = [c for _, c in timeline]
    fig, ax = plt.subplots(figsize=(14, 4))
    ax.fill_between(dates, vals, alpha=0.25, color=style.PALETTE[0])
    ax.plot(dates, vals, color=style.PALETTE[0], linewidth=1.8)
    ax.set_ylabel('messages / week')
    ax.grid(axis='y', alpha=0.4)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
    fig.autofmt_xdate(rotation=30)
    fig.tight_layout()
    return _fig_to_b64(fig)


def _sentiment_b64(msgs: list[Message]) -> Optional[str]:
    try:
        from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    except ImportError:
        return None
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from datetime import datetime as dt

    style.apply()
    analyzer = SentimentIntensityAnalyzer()
    daily: dict[date, list[float]] = defaultdict(list)
    for m in msgs:
        if m.text.strip() and m.date.year > 2001:
            daily[m.date.date()].append(analyzer.polarity_scores(m.text)['compound'])

    if not daily:
        return None

    raw = sorted((d, sum(v) / len(v)) for d, v in daily.items())
    # 7-day rolling average
    vals_raw = [v for _, v in raw]
    smoothed = []
    W = 7
    for i in range(len(vals_raw)):
        lo = max(0, i - W + 1)
        smoothed.append(sum(vals_raw[lo:i + 1]) / (i - lo + 1))

    dates_p = [dt.combine(d, dt.min.time()) for d, _ in raw]

    fig, ax = plt.subplots(figsize=(14, 4))
    ax.scatter(dates_p, vals_raw, s=5, alpha=0.2, color=style.PALETTE[0])
    ax.plot(dates_p, smoothed, color=style.PALETTE[0], linewidth=2)
    ax.fill_between(dates_p, smoothed, 0,
                    where=[v >= 0 for v in smoothed], alpha=0.15, color=style.PALETTE[1])
    ax.fill_between(dates_p, smoothed, 0,
                    where=[v < 0 for v in smoothed], alpha=0.15, color=style.PALETTE[3])
    ax.axhline(0, color=style.BORDER, linewidth=1, linestyle='--')
    ax.set_ylim(-1, 1)
    ax.set_ylabel('sentiment')
    ax.grid(axis='y', alpha=0.4)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
    fig.autofmt_xdate(rotation=30)
    fig.tight_layout()
    return _fig_to_b64(fig)


# ── static CSS ───────────────────────────────────────────────────────────────

_CSS = r"""
*{box-sizing:border-box;margin:0;padding:0}
html{scroll-behavior:smooth}
body{background:#0f0f1a;color:#e0e0e0;font-family:system-ui,-apple-system,sans-serif;font-size:14px}

/* ── nav ── */
nav{position:sticky;top:0;z-index:100;background:#0f0f1aee;backdrop-filter:blur(8px);
    border-bottom:1px solid #2a2a4a;display:flex;align-items:center;gap:4px;
    padding:8px 20px;flex-wrap:wrap}
nav a{color:#8888aa;text-decoration:none;padding:4px 10px;border-radius:6px;font-size:12px;
      white-space:nowrap;transition:color .15s,background .15s}
nav a:hover{color:#e0e0e0;background:#1a1a2e}
.lang-wrap{margin-left:auto;display:flex;gap:4px}
.lang-btn{background:none;border:1px solid #2a2a4a;color:#8888aa;padding:3px 10px;
          border-radius:6px;cursor:pointer;font-size:11px;transition:all .15s}
.lang-btn.active{background:#4FC3F7;border-color:#4FC3F7;color:#0f0f1a;font-weight:700}

/* ── header ── */
header{padding:36px 28px 20px;border-bottom:1px solid #1a1a2e}
header h1{font-size:1.9rem;font-weight:800;letter-spacing:-.02em}
header .sub{color:#8888aa;margin-top:6px;font-size:.85rem}

/* ── sections ── */
section{padding:28px;border-bottom:1px solid #1a1a2e}
section h2{font-size:1rem;font-weight:700;text-transform:uppercase;letter-spacing:.07em;
           color:#8888aa;margin-bottom:18px}

/* ── overview cards ── */
.cards{display:flex;flex-wrap:wrap;gap:14px}
.card{background:#1a1a2e;border:1px solid #2a2a4a;border-radius:10px;
      padding:16px 22px;min-width:130px;display:flex;flex-direction:column;align-items:center;gap:4px}
.card .val{font-size:1.7rem;font-weight:800;color:#4FC3F7}
.card .lbl{font-size:.72rem;color:#8888aa;text-transform:uppercase;letter-spacing:.05em}

/* ── chart images ── */
.chart-img{width:100%;border-radius:8px;display:block}

/* ── side-by-side ── */
.two-col{display:grid;grid-template-columns:1fr 1fr;gap:24px}
@media(max-width:800px){.two-col{grid-template-columns:1fr}}
.three-col{display:grid;grid-template-columns:1fr 1fr 1fr;gap:24px}
@media(max-width:1000px){.three-col{grid-template-columns:1fr 1fr}}
@media(max-width:600px){.three-col{grid-template-columns:1fr}}

/* ── heatmap ── */
.heatmap-wrap{overflow-x:auto}
.hm-table{border-collapse:collapse;min-width:600px}
.hm-table th,.hm-table td{padding:0}
.hm-table .day-lbl{font-size:11px;color:#8888aa;padding-right:8px;white-space:nowrap;text-align:right}
.hm-table .hour-lbl{font-size:10px;color:#555;text-align:center;padding-bottom:4px;width:28px}
.hm-cell{width:28px;height:22px;border-radius:3px;cursor:default;position:relative}
.hm-cell:hover::after{content:attr(title);position:absolute;bottom:110%;left:50%;
                       transform:translateX(-50%);background:#2a2a4a;color:#e0e0e0;
                       padding:4px 8px;border-radius:4px;font-size:11px;white-space:nowrap;
                       z-index:10;pointer-events:none}

/* ── top words ── */
.words-controls{display:flex;align-items:center;gap:10px;margin-bottom:16px;flex-wrap:wrap}
.words-controls input[type=range]{flex:1;min-width:120px;accent-color:#4FC3F7}
.words-controls input[type=number]{width:64px;background:#1a1a2e;border:1px solid #2a2a4a;
                                    color:#e0e0e0;border-radius:6px;padding:4px 8px;font-size:13px}
#words-n-val{font-weight:700;color:#4FC3F7;min-width:24px}
.mode-wrap{margin-left:auto;display:flex;gap:4px}
.bar-row{display:flex;align-items:center;gap:8px;margin-bottom:6px}
.bar-lbl{width:130px;text-align:right;font-size:12px;color:#c0c0d8;overflow:hidden;
         text-overflow:ellipsis;white-space:nowrap;flex-shrink:0}
.bar-track{flex:1;height:14px;background:#1a1a2e;border-radius:4px;overflow:hidden}
.bar-fill{height:100%;background:#4FC3F7;border-radius:4px;transition:width .3s}
.bar-cnt{font-size:11px;color:#8888aa;min-width:36px}

/* ── stats table ── */
.tbl-wrap{overflow-x:auto}
table{width:100%;border-collapse:collapse;font-size:12px}
thead th{background:#1a1a2e;color:#8888aa;font-size:11px;text-transform:uppercase;
         letter-spacing:.05em;padding:10px 12px;text-align:left;white-space:nowrap;
         border-bottom:1px solid #2a2a4a}
tbody tr:nth-child(even){background:#0d0d18}
tbody td{padding:9px 12px;border-bottom:1px solid #1a1a2e;vertical-align:middle}
tbody tr:hover{background:#1a1a2e}
.sender-cell{font-weight:600;color:#4FC3F7}

/* ── emoji grid ── */
.emoji-grid{display:flex;flex-wrap:wrap;gap:10px}
.emoji-item{background:#1a1a2e;border:1px solid #2a2a4a;border-radius:8px;
            padding:10px 14px;display:flex;flex-direction:column;align-items:center;
            gap:4px;min-width:70px;cursor:default}
.emoji-char{font-size:2rem;line-height:1}
.emoji-count{font-size:11px;color:#8888aa}

/* ── links chart ── */
.link-row{display:flex;align-items:center;gap:8px;margin-bottom:8px}
.link-domain{width:160px;font-size:12px;color:#c0c0d8;text-align:right;flex-shrink:0;
             overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.link-track{flex:1;height:14px;background:#1a1a2e;border-radius:4px;overflow:hidden}
.link-fill{height:100%;border-radius:4px;transition:width .3s}
.link-cnt{font-size:11px;color:#8888aa;min-width:32px}
"""

# ── static JS (no f-string interpolation — use raw string) ──────────────────

_JS_STATIC = r"""
const DAYS_EN = ['Mon','Tue','Wed','Thu','Fri','Sat','Sun'];
const DAYS_RU = ['Пн','Вт','Ср','Чт','Пт','Сб','Вс'];

const I18N = {
  en: {
    'nav.overview':   'Overview',
    'nav.timeline':   'Timeline',
    'nav.heatmap':    'Heatmap',
    'nav.wordcloud':  'Word Cloud',
    'nav.topwords':   'Top Words',
    'nav.stats':      'Statistics',
    'nav.emoji':      'Emoji',
    'nav.links':      'Links',
    'nav.sentiment':  'Sentiment',
    'sec.overview':   'Overview',
    'sec.timeline':   'Message timeline — weekly',
    'sec.heatmap':    'Activity heatmap',
    'sec.wordcloud':  'Word cloud',
    'sec.topwords':   'Most common words',
    'sec.stats':      'Statistics per person',
    'sec.emoji':      'Emoji usage',
    'sec.reactions':  'Message reactions',
    'sec.links':      'Most shared domains',
    'sec.sentiment':  'Sentiment over time',
    'lbl.messages':   'messages',
    'lbl.people':     'participants',
    'lbl.days':       'days active',
    'lbl.media':      'media files',
    'lbl.voice':      'voice minutes',
    'lbl.vocab':      'unique words',
    'lbl.forwarded':  'forwarded',
    'lbl.replies':    'replies',
    'ctrl.showing':   'Top',
    'ctrl.words':     'words',
    'ctrl.mode_smart':'Meaningful',
    'ctrl.mode_all':  'All words',
    'th.sender':      'Sender',
    'th.messages':    'Msgs',
    'th.words':       'Words',
    'th.avg':         'Avg',
    'th.vocab':       'Vocab',
    'th.media':       'Media',
    'th.voice':       'Voice',
    'th.voicemin':    'Voice min',
    'th.replies':     'Replies',
    'th.peak':        'Peak hour',
    'th.topword':     'Top word',
  },
  ru: {
    'nav.overview':   'Обзор',
    'nav.timeline':   'График',
    'nav.heatmap':    'Активность',
    'nav.wordcloud':  'Облако слов',
    'nav.topwords':   'Топ слов',
    'nav.stats':      'Статистика',
    'nav.emoji':      'Emoji',
    'nav.links':      'Ссылки',
    'nav.sentiment':  'Настроение',
    'sec.overview':   'Обзор',
    'sec.timeline':   'График сообщений — по неделям',
    'sec.heatmap':    'Тепловая карта активности',
    'sec.wordcloud':  'Облако слов',
    'sec.topwords':   'Самые частые слова',
    'sec.stats':      'Статистика по участникам',
    'sec.emoji':      'Использование emoji',
    'sec.reactions':  'Реакции на сообщения',
    'sec.links':      'Топ сайтов',
    'sec.sentiment':  'Настроение чата',
    'lbl.messages':   'сообщений',
    'lbl.people':     'участников',
    'lbl.days':       'дней активности',
    'lbl.media':      'медиафайлов',
    'lbl.voice':      'мин. голос.',
    'lbl.vocab':      'уникальных слов',
    'lbl.forwarded':  'пересланных',
    'lbl.replies':    'ответов',
    'ctrl.showing':   'Топ',
    'ctrl.words':     'слов',
    'ctrl.mode_smart':'Смысловые',
    'ctrl.mode_all':  'Все слова',
    'th.sender':      'Участник',
    'th.messages':    'Сообщ.',
    'th.words':       'Слов',
    'th.avg':         'Сред.',
    'th.vocab':       'Словарь',
    'th.media':       'Медиа',
    'th.voice':       'Голос',
    'th.voicemin':    'Мин. гол.',
    'th.replies':     'Ответов',
    'th.peak':        'Пик',
    'th.topword':     'Топ слово',
  }
};

let currentLang = 'ru';
let wordMode = 'smart';

function setWordMode(m) {
  wordMode = m;
  document.getElementById('btn-smart').classList.toggle('active', m === 'smart');
  document.getElementById('btn-all').classList.toggle('active', m === 'all');
  const wcs = document.getElementById('wc-smart');
  const wca = document.getElementById('wc-all');
  if (wcs) wcs.style.display = m === 'smart' ? '' : 'none';
  if (wca) wca.style.display = m === 'all' ? '' : 'none';
  renderWords(+document.getElementById('words-slider').value);
}

function setLang(l) {
  currentLang = l;
  document.getElementById('btn-en').classList.toggle('active', l === 'en');
  document.getElementById('btn-ru').classList.toggle('active', l === 'ru');
  const dict = I18N[l];
  document.querySelectorAll('[data-key]').forEach(el => {
    const k = el.dataset.key;
    if (dict[k] !== undefined) el.textContent = dict[k];
  });
  renderHeatmap();
}

function renderHeatmap() {
  const days = currentLang === 'ru' ? DAYS_RU : DAYS_EN;
  const max = Math.max(...HM_DATA.flat(), 1);
  let html = '<table class="hm-table"><tr><td></td>';
  for (let h = 0; h < 24; h++) {
    html += `<th class="hour-lbl">${String(h).padStart(2,'0')}</th>`;
  }
  html += '</tr>';
  for (let d = 0; d < 7; d++) {
    html += `<tr><td class="day-lbl">${days[d]}</td>`;
    for (let h = 0; h < 24; h++) {
      const v = HM_DATA[d][h];
      const a = (v / max).toFixed(3);
      const tip = `${days[d]} ${String(h).padStart(2,'0')}:00 — ${v}`;
      html += `<td class="hm-cell" style="background:rgba(79,195,247,${a})" title="${tip}"></td>`;
    }
    html += '</tr>';
  }
  html += '</table>';
  document.getElementById('hm-container').innerHTML = html;
}

function renderWords(n) {
  const WORD_FREQ = wordMode === 'smart' ? WORD_FREQ_SMART : WORD_FREQ_ALL;
  n = Math.max(1, Math.min(n, WORD_FREQ.length));
  document.getElementById('words-n-val').textContent = n;
  document.getElementById('words-slider').value = n;
  document.getElementById('words-num').value = n;
  const data = WORD_FREQ.slice(0, n);
  const max = data.length ? data[0][1] : 1;
  const html = data.map(([w, c]) =>
    `<div class="bar-row">
       <span class="bar-lbl">${w}</span>
       <div class="bar-track"><div class="bar-fill" style="width:${(c/max*100).toFixed(1)}%"></div></div>
       <span class="bar-cnt">${c}</span>
     </div>`
  ).join('');
  document.getElementById('words-chart').innerHTML = html;
}

document.addEventListener('DOMContentLoaded', () => {
  renderHeatmap();
  renderWords(20);
  setLang('ru');

  document.getElementById('words-slider').addEventListener('input', e => renderWords(+e.target.value));
  document.getElementById('words-num').addEventListener('input', e => renderWords(+e.target.value));
});
"""


# ── HTML assembly ─────────────────────────────────────────────────────────────

def _card(key: str, val: str) -> str:
    return f'<div class="card"><span class="val">{val}</span><span class="lbl" data-key="{key}"></span></div>'


def _section(sid: str, title_key: str, inner: str) -> str:
    return f'''<section id="{sid}">
  <h2 data-key="{title_key}"></h2>
  {inner}
</section>'''


def _stats_rows(rows: list[dict]) -> str:
    html = ''
    for r in rows:
        html += f'''<tr>
  <td class="sender-cell">{r['sender']}</td>
  <td>{r['messages']:,}</td>
  <td>{r['words']:,}</td>
  <td>{r['avg']}</td>
  <td>{r['vocab']:,}</td>
  <td>{r['media']}</td>
  <td>{r['voice']}</td>
  <td>{r['voice_min']}</td>
  <td>{r['replies']}</td>
  <td>{r['peak']}</td>
  <td>{r['top_word']}</td>
</tr>'''
    return html


def _emoji_html(emoji_freq: list[tuple[str, int]]) -> str:
    if not emoji_freq:
        return '<p style="color:#8888aa">No emoji found.</p>'
    items = ''.join(
        f'<div class="emoji-item" title="{count}"><span class="emoji-char">{e}</span>'
        f'<span class="emoji-count">{count}</span></div>'
        for e, count in emoji_freq
    )
    return f'<div class="emoji-grid">{items}</div>'


def _links_html(link_freq: list[tuple[str, int]]) -> str:
    if not link_freq:
        return '<p style="color:#8888aa">No links found.</p>'
    max_c = link_freq[0][1]
    palette = ['#4FC3F7', '#81C784', '#FFB74D', '#E57373', '#CE93D8',
               '#4DD0E1', '#FFF176', '#F48FB1', '#80CBC4', '#FFCC02']
    rows = ''
    for i, (domain, count) in enumerate(link_freq):
        pct = count / max_c * 100
        color = palette[i % len(palette)]
        rows += (f'<div class="link-row">'
                 f'<span class="link-domain">{domain}</span>'
                 f'<div class="link-track"><div class="link-fill" style="width:{pct:.1f}%;background:{color}"></div></div>'
                 f'<span class="link-cnt">{count}</span>'
                 f'</div>')
    return rows


# ── main generate ─────────────────────────────────────────────────────────────

def generate(messages: list[Message], chat_name: str, num_words: int = 150,
             pdf_path: Optional[str] = None) -> str:
    import matplotlib
    matplotlib.use('Agg')

    style.apply()
    nlp.ensure_nltk_data()

    text_msgs = _text_msgs(messages)
    valid = _valid_dates(text_msgs)

    if not valid:
        sys.exit('error: no messages with valid dates found')

    first_date = min(valid).date()
    last_date  = max(valid).date()
    span_days  = (last_date - first_date).days + 1
    n_senders  = len({m.sender for m in text_msgs})
    n_media    = sum(1 for m in text_msgs if m.media_type)
    n_fwd      = sum(1 for m in text_msgs if m.forwarded_from)
    n_replies  = sum(1 for m in text_msgs if m.reply_to_id)
    voice_min  = sum(m.duration_seconds or 0 for m in text_msgs
                     if m.media_type == 'voice_message') // 60

    print('  Computing word frequencies ...')
    stop_basic = nlp.stopword_set()
    stop_smart = nlp.extended_stopword_set()
    word_freq_all   = _word_freq(text_msgs, stop_basic)
    word_freq_smart = _word_freq(text_msgs, stop_smart)

    all_words = []
    for m in text_msgs:
        all_words.extend(nlp.tokenize_and_filter(nlp.clean(m.text), stop_basic))
    vocab_size = len(set(all_words))

    print('  Computing per-person stats ...')
    person_stats = _per_person(text_msgs)

    hm_data       = _heatmap_data(text_msgs)
    timeline      = _timeline_data(text_msgs)
    emoji_freq    = _emoji_freq(text_msgs)
    reaction_freq = _reaction_freq(text_msgs)
    link_freq     = _link_freq(text_msgs)

    print('  Generating charts ...')
    b64_wc_smart = _wordcloud_b64(word_freq_smart, num_words)
    b64_wc_all   = _wordcloud_b64(word_freq_all, num_words)
    b64_timeline = _timeline_b64(timeline)
    b64_sent     = _sentiment_b64(text_msgs)

    # ── inject data as JS ──
    data_js = (
        f'const HM_DATA = {json.dumps(hm_data)};\n'
        f'const WORD_FREQ_SMART = {json.dumps(word_freq_smart)};\n'
        f'const WORD_FREQ_ALL = {json.dumps(word_freq_all)};\n'
    )

    # ── sections ──
    def _wc_img(img_id: str, b64: Optional[str], hidden: bool = False) -> str:
        if not b64:
            return '' if hidden else '<p style="color:#8888aa">Word cloud could not be generated.</p>'
        disp = ' style="display:none"' if hidden else ''
        return f'<img id="{img_id}" class="chart-img" src="data:image/png;base64,{b64}" alt="word cloud"{disp}>'

    wc_html = _wc_img('wc-smart', b64_wc_smart) + _wc_img('wc-all', b64_wc_all, hidden=True)
    timeline_html = (
        f'<img class="chart-img" src="data:image/png;base64,{b64_timeline}" alt="timeline">'
        if b64_timeline else ''
    )
    sentiment_section = ''
    if b64_sent:
        sentiment_section = _section(
            'sentiment', 'sec.sentiment',
            f'<img class="chart-img" src="data:image/png;base64,{b64_sent}" alt="sentiment">'
        )

    th = lambda k: f'<th data-key="{k}"></th>'
    stats_table = f'''<div class="tbl-wrap"><table>
  <thead><tr>
    {th("th.sender")}{th("th.messages")}{th("th.words")}{th("th.avg")}
    {th("th.vocab")}{th("th.media")}{th("th.voice")}{th("th.voicemin")}
    {th("th.replies")}{th("th.peak")}{th("th.topword")}
  </tr></thead>
  <tbody>{_stats_rows(person_stats)}</tbody>
</table></div>'''

    max_slider = min(max(len(word_freq_smart), len(word_freq_all)), 200)

    # ── optional PDF ──
    if pdf_path:
        print('  Generating PDF ...')
        from tcv.pdf_export import generate_pdf
        overview_cards = [
            ('Messages',     f'{len(text_msgs):,}'),
            ('Participants', str(n_senders)),
            ('Days active',  f'{span_days:,}'),
            ('Media files',  f'{n_media:,}'),
            ('Voice min',    str(voice_min)),
            ('Unique words', f'{vocab_size:,}'),
            ('Forwarded',    f'{n_fwd:,}'),
            ('Replies',      f'{n_replies:,}'),
        ]
        generate_pdf(
            path=pdf_path,
            chat_name=chat_name,
            first_date=first_date,
            last_date=last_date,
            overview_cards=overview_cards,
            word_freq_smart=word_freq_smart,
            hm_data=hm_data,
            person_stats=person_stats,
            emoji_freq=emoji_freq,
            reaction_freq=reaction_freq,
            link_freq=link_freq,
            b64_wc=b64_wc_smart,
            b64_timeline=b64_timeline,
            b64_sent=b64_sent,
        )
        print(f'  Saved → {pdf_path}')

    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>{chat_name} — Analytics</title>
  <style>{_CSS}</style>
</head>
<body>

<nav>
  <a href="#overview"  data-key="nav.overview"></a>
  <a href="#timeline"  data-key="nav.timeline"></a>
  <a href="#heatmap"   data-key="nav.heatmap"></a>
  <a href="#wordcloud" data-key="nav.wordcloud"></a>
  <a href="#topwords"  data-key="nav.topwords"></a>
  <a href="#stats"     data-key="nav.stats"></a>
  <a href="#emoji"     data-key="nav.emoji"></a>
  <a href="#links"     data-key="nav.links"></a>
  {'<a href="#sentiment" data-key="nav.sentiment"></a>' if b64_sent else ''}
  <div class="lang-wrap">
    <button class="lang-btn" id="btn-en" onclick="setLang('en')">EN</button>
    <button class="lang-btn active" id="btn-ru" onclick="setLang('ru')">RU</button>
  </div>
</nav>

<header>
  <h1>{chat_name}</h1>
  <p class="sub">{first_date} → {last_date} &nbsp;·&nbsp; {len(text_msgs):,} messages &nbsp;·&nbsp; {n_senders} participants</p>
</header>

{_section('overview', 'sec.overview', f'''<div class="cards">
  {_card("lbl.messages",  f"{len(text_msgs):,}")}
  {_card("lbl.people",    str(n_senders))}
  {_card("lbl.days",      f"{span_days:,}")}
  {_card("lbl.media",     f"{n_media:,}")}
  {_card("lbl.voice",     str(voice_min))}
  {_card("lbl.vocab",     f"{vocab_size:,}")}
  {_card("lbl.forwarded", f"{n_fwd:,}")}
  {_card("lbl.replies",   f"{n_replies:,}")}
</div>''')}

{_section('timeline', 'sec.timeline', timeline_html)}

{_section('heatmap', 'sec.heatmap', '<div class="heatmap-wrap"><div id="hm-container"></div></div>')}

<section>
  <div class="two-col">
    <div>
      <h2 data-key="sec.wordcloud"></h2>
      {wc_html}
    </div>
    <div>
      <h2 data-key="sec.topwords"></h2>
      <div class="words-controls">
        <span data-key="ctrl.showing"></span>
        <input type="number" id="words-num" min="5" max="{max_slider}" value="20">
        <input type="range"  id="words-slider" min="5" max="{max_slider}" value="20">
        <span id="words-n-val" style="color:#4FC3F7;font-weight:700">20</span>
        <span data-key="ctrl.words"></span>
        <div class="mode-wrap">
          <button class="lang-btn active" id="btn-smart" onclick="setWordMode('smart')" data-key="ctrl.mode_smart"></button>
          <button class="lang-btn" id="btn-all" onclick="setWordMode('all')" data-key="ctrl.mode_all"></button>
        </div>
      </div>
      <div id="words-chart"></div>
    </div>
  </div>
</section>

{_section('stats', 'sec.stats', stats_table)}

<section>
  <div class="{'three-col' if reaction_freq else 'two-col'}">
    <div>
      <h2 data-key="sec.emoji"></h2>
      {_emoji_html(emoji_freq)}
    </div>
    {'<div><h2 data-key="sec.reactions"></h2>' + _emoji_html(reaction_freq) + '</div>' if reaction_freq else ''}
    <div>
      <h2 data-key="sec.links"></h2>
      {_links_html(link_freq)}
    </div>
  </div>
</section>

{sentiment_section}

<script>
{data_js}
</script>
<script>
{_JS_STATIC}
</script>
</body>
</html>"""
