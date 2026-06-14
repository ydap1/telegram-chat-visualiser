from __future__ import annotations

import matplotlib as mpl
import matplotlib.pyplot as plt

BG = '#0f0f1a'
SURFACE = '#1a1a2e'
BORDER = '#2a2a4a'
TEXT = '#e0e0e0'
MUTED = '#8888aa'

PALETTE = [
    '#4FC3F7',  # light blue
    '#81C784',  # green
    '#FFB74D',  # amber
    '#E57373',  # red
    '#CE93D8',  # purple
    '#4DD0E1',  # cyan
    '#FFF176',  # yellow
    '#F48FB1',  # pink
    '#80CBC4',  # teal
    '#FFCC02',  # gold
]


def apply() -> None:
    mpl.rcParams.update({
        'figure.facecolor': BG,
        'axes.facecolor': SURFACE,
        'axes.edgecolor': BORDER,
        'axes.labelcolor': TEXT,
        'axes.prop_cycle': mpl.cycler(color=PALETTE),
        'text.color': TEXT,
        'xtick.color': TEXT,
        'ytick.color': TEXT,
        'xtick.labelsize': 9,
        'ytick.labelsize': 9,
        'axes.titlesize': 13,
        'axes.labelsize': 10,
        'grid.color': BORDER,
        'grid.alpha': 0.6,
        'legend.facecolor': SURFACE,
        'legend.edgecolor': BORDER,
        'legend.fontsize': 9,
        'figure.dpi': 150,
        'savefig.dpi': 150,
        'savefig.bbox': 'tight',
        'savefig.facecolor': BG,
    })
    plt.style.use('dark_background')
