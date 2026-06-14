
# Telegram Chat Visualiser

Analyse and visualise your Telegram chat exports. Generates word clouds, activity heatmaps,
message timelines, reply networks, sentiment trends, and a full self-contained HTML dashboard.
Supports English and Russian.

![demo](https://github.com/YungDrizzyAP/telegram-chat-visualiser/blob/main/demo.gif)
![example](https://github.com/YungDrizzyAP/telegram-chat-visualiser/blob/main/example.png)

## Export your chat

Open Telegram → **Settings → Export Telegram data** → select the chat → choose **JSON** format.

## Installation

```bash
git clone https://github.com/YungDrizzyAP/telegram-chat-visualiser
cd telegram-chat-visualiser
pip install -e .
```

This installs the `tcv` command globally.

## Usage

```
tcv <command> <file.json> [options]
```

### Commands

| Command | Description |
|---------|-------------|
| `wordcloud` | Word cloud from all messages |
| `heatmap` | Message count by day of week × hour of day |
| `timeline` | Message volume over time |
| `stats` | Per-person statistics table |
| `network` | Reply network graph — who responds to whom |
| `emoji` | Emoji frequency chart |
| `links` | Most shared link domains |
| `sentiment` | Sentiment score over time |
| `dashboard` | Self-contained HTML report with all analyses |

Run `tcv <command> --help` for per-command options.

---

### `wordcloud`

```bash
tcv wordcloud result.json
tcv wordcloud result.json -n 200 -W 1920 -H 1080 -o cloud.png
tcv wordcloud result.json --by-person     # one image per sender
```

| Flag | Default | Description |
|------|---------|-------------|
| `-n, --num-words` | `150` | Number of words |
| `-W, --width` | `1280` | Image width (px) |
| `-H, --height` | `720` | Image height (px) |
| `-o, --output` | `wordcloud.png` | Output path |
| `--by-person` | off | One cloud per sender |

---

### `heatmap`

```bash
tcv heatmap result.json
tcv heatmap result.json -o activity.png
```

Shows a 7×24 grid of message volume (day of week vs hour of day).

---

### `timeline`

```bash
tcv timeline result.json
tcv timeline result.json --period month --by-person
```

| Flag | Default | Description |
|------|---------|-------------|
| `--period` | `week` | `day`, `week`, or `month` |
| `--by-person` | off | One line per sender |
| `-o, --output` | `timeline.png` | Output path |

---

### `stats`

```bash
tcv stats result.json
tcv stats result.json --csv stats.csv
```

Prints a table with messages, words, avg length, vocabulary size, media,
voice messages, replies, peak hour, and most used word per person.

---

### `network`

```bash
tcv network result.json
tcv network result.json --top 15 -o replies.png
```

Directed graph — arrow from A to B means A replied to B.
Node size = total messages sent.

| Flag | Default | Description |
|------|---------|-------------|
| `--top` | `20` | Limit to N most active senders |
| `-o, --output` | `network.png` | Output path |

---

### `emoji`

```bash
tcv emoji result.json -n 40
```

---

### `links`

```bash
tcv links result.json -n 20
```

---

### `sentiment`

Requires `vaderSentiment` (included in `requirements.txt`).
Shows compound sentiment score on a rolling average, coloured green for positive
and red for negative periods.

```bash
tcv sentiment result.json --window 14
```

---

### `dashboard`

Generates a single self-contained HTML file with all charts embedded as images.
Open it in any browser — no internet required.

```bash
tcv dashboard result.json
tcv dashboard result.json -o my_chat_report.html
```

---

## Running without installing

```bash
python -m tcv wordcloud result.json
python -m tcv dashboard result.json
```

---

YDAP 2022–2025.
