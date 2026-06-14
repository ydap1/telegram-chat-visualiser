
# Telegram Chat WordCloud Generator

A simple tool to visualise the most used words in a Telegram conversation using a word cloud.
Currently supports English and Russian.

## Chat export:
![](https://github.com/YungDrizzyAP/telegram-chat-visualiser/blob/main/demo.gif)![](https://github.com/YungDrizzyAP/telegram-chat-visualiser/blob/main/example.png)

## Installation

```bash
cd telegram-chat-visualiser
pip3 install -r requirements.txt
```

## Usage

Export your Telegram chat as JSON (**Settings → Export Telegram data → select the chat → JSON format**), then run:

```bash
python3 script.py result.json
```

By default this produces a `wordcloud.png` with the 150 most common words at 1280×720.

### Options

| Flag | Long form | Default | Description |
|------|-----------|---------|-------------|
| `-n` | `--num-words` | `150` | Number of words to display |
| `-W` | `--width` | `1280` | Image width in pixels |
| `-H` | `--height` | `720` | Image height in pixels |
| `-o` | `--output` | `wordcloud.png` | Output PNG path |

### Example

```bash
python3 script.py result.json -n 200 -W 1920 -H 1080 -o chat.png
```

## Contributions are welcome.

YDAP 2022.
