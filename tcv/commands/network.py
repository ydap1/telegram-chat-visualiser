from __future__ import annotations

import sys
from collections import defaultdict, Counter

import matplotlib.pyplot as plt

from tcv import style
from tcv.parser import Message


def make_figure(messages: list[Message], top: int = 20) -> plt.Figure:
    try:
        import networkx as nx
    except ImportError:
        sys.exit('error: networkx is required — pip install networkx')

    style.apply()

    id_to_sender = {m.id: m.sender for m in messages if m.type == 'message'}
    msg_counts: Counter[str] = Counter(
        m.sender for m in messages if m.type == 'message'
    )
    top_senders = {s for s, _ in msg_counts.most_common(top)}

    edge_weights: dict[tuple[str, str], int] = defaultdict(int)
    for m in messages:
        if m.type != 'message' or m.reply_to_id is None:
            continue
        replier = m.sender
        target = id_to_sender.get(m.reply_to_id)
        if target and replier != target and replier in top_senders and target in top_senders:
            edge_weights[(replier, target)] += 1

    if not edge_weights:
        fig, ax = plt.subplots(figsize=(8, 8))
        ax.text(0.5, 0.5, 'no reply data found\n(export may not include reply_to_message_id)',
                ha='center', va='center', transform=ax.transAxes, color=style.MUTED, fontsize=11)
        ax.set_title('Reply network')
        return fig

    G = nx.DiGraph()
    for (src, dst), w in edge_weights.items():
        G.add_edge(src, dst, weight=w)

    node_sizes = [msg_counts.get(n, 1) * 5 for n in G.nodes()]
    edge_widths = [G[u][v]['weight'] ** 0.6 for u, v in G.edges()]

    try:
        pos = nx.kamada_kawai_layout(G)
    except Exception:
        pos = nx.spring_layout(G, k=2, seed=42)

    fig, ax = plt.subplots(figsize=(11, 11))

    node_colors = [style.PALETTE[i % len(style.PALETTE)] for i, _ in enumerate(G.nodes())]
    nx.draw_networkx_nodes(G, pos, node_size=node_sizes, node_color=node_colors,
                           alpha=0.85, ax=ax)
    nx.draw_networkx_labels(G, pos, font_size=8, font_color=style.TEXT, ax=ax)
    nx.draw_networkx_edges(G, pos, width=edge_widths, alpha=0.5,
                           edge_color=style.PALETTE[0],
                           arrows=True, arrowsize=15,
                           connectionstyle='arc3,rad=0.1', ax=ax)

    ax.set_title(f'Reply network (top {top} senders)', pad=15)
    ax.axis('off')
    fig.tight_layout()
    return fig


def register(sub) -> None:
    p = sub.add_parser('network', help='reply network graph — who responds to whom')
    p.add_argument('input_file', help='Telegram JSON export')
    p.add_argument('--top', type=int, default=20,
                   help='limit to N most active senders (default: 20)')
    p.add_argument('-o', '--output', default='network.png',
                   help='output PNG path (default: network.png)')
    p.set_defaults(func=run)


def run(args) -> None:
    from tcv.parser import load
    messages, _ = load(args.input_file)
    fig = make_figure(messages, top=args.top)
    fig.savefig(args.output)
    plt.close(fig)
    print(f'saved to {args.output}')
