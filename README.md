
# Telegram Chat Visualiser

Generates a self-contained HTML analytics dashboard from a Telegram chat export.
Supports both JSON and HTML export formats. English and Russian UI.

![demo](https://github.com/YungDrizzyAP/telegram-chat-visualiser/blob/main/demo.gif)

## Export your chat

Open Telegram → **Settings → Export Telegram data** → select the chat.
Works with both **HTML** and **JSON** export formats.

## Installation

```bash
git clone https://github.com/ydap1/telegram-chat-visualiser
cd telegram-chat-visualiser
python3 -m venv .venv && .venv/bin/pip install -e .
```

## Usage

```bash
# HTML export (pass the exported folder)
tcv "/path/to/ChatExport_2026-06-14"

# JSON export
tcv result.json

# Custom output path and word cloud size
tcv result.json -o report.html -n 200
```

Opens `dashboard.html` in any browser — no internet required.

### Options

| Flag | Default | Description |
|------|---------|-------------|
| `-o, --output` | `dashboard.html` | Output HTML file |
| `-n, --num-words` | `150` | Words in the word cloud image |

## Dashboard sections

| Section | Description |
|---------|-------------|
| Overview | Message count, participants, days active, media, voice minutes, vocabulary size |
| Timeline | Weekly message volume chart |
| Activity heatmap | Interactive hour × day-of-week grid with hover counts |
| Word cloud | Top-N word cloud image |
| Top words | Interactive bar chart with slider (default top 20, adjustable) |
| Statistics | Per-person table: messages, words, avg length, vocab, media, voice, replies, peak hour |
| Emoji usage | Top emoji rendered natively by the browser |
| Shared domains | Most linked websites |
| Sentiment | Mood over time (requires `vaderSentiment`) |

The page has an **EN / RU** toggle in the navigation bar.

## Running without installing

```bash
python3 -m venv .venv && .venv/bin/pip install -e .
.venv/bin/python -m tcv "/path/to/export"
```

---

YDAP 2022–2026.
