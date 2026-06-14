from __future__ import annotations

import argparse

from tcv.commands import (
    dashboard,
    emoji_cmd,
    heatmap,
    links,
    network,
    sentiment,
    stats,
    timeline,
    wordcloud_cmd,
)


def main() -> None:
    p = argparse.ArgumentParser(
        prog='tcv',
        description='Telegram chat visualiser — analyse and visualise your chat exports',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            'commands:\n'
            '  wordcloud   word cloud from all messages\n'
            '  heatmap     activity by day of week and hour\n'
            '  timeline    message volume over time\n'
            '  stats       per-person statistics table\n'
            '  network     reply network graph\n'
            '  emoji       emoji frequency chart\n'
            '  links       most shared link domains\n'
            '  sentiment   sentiment score over time\n'
            '  dashboard   self-contained HTML analytics report\n'
        ),
    )

    sub = p.add_subparsers(dest='command', metavar='command')
    sub.required = True

    wordcloud_cmd.register(sub)
    heatmap.register(sub)
    timeline.register(sub)
    stats.register(sub)
    network.register(sub)
    emoji_cmd.register(sub)
    links.register(sub)
    sentiment.register(sub)
    dashboard.register(sub)

    args = p.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()
