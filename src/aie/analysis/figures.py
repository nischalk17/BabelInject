"""Figures from the summary tables (matplotlib, static PNG, light surface).

Design rules applied: one hue (blue) for magnitude, a gray baseline for emphasis, a hairline
solid grid, a fixed 0-100% scale across panels, thin marks, direct labels, and a CSV "table
view" for every figure (see ``tables.py``). No dual axes. Text is never set in a series color.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")  # headless: write files, never open a window
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap

from aie.analysis.tables import CHANNELS, LANGUAGES, AsrRow, EffectRow
from aie.eval.metrics import wilson

SURFACE, INK, INK2, MUTED = "#fcfcfb", "#0b0b0b", "#52514e", "#898781"
GRID, AXIS = "#e1e0d9", "#c3c2b7"
BLUE = "#2a78d6"  # categorical slot 1, the single accent
GRAY = "#b3b2ab"  # de-emphasis (baseline)
BLUE_RAMP = ["#cde2fb", "#9ec5f4", "#5598e7", "#256abf", "#184f95", "#0d366b"]  # sequential

LANG_NAMES = {
    "en": "English",
    "ne": "Nepali",
    "ne_rom": "Romanized Nepali",
    "hi": "Hindi",
    "mix": "Code-mixed",
}
CHANNEL_NAMES = {
    "email": "Email",
    "file": "File",
    "doc": "Web\npage",
    "tool_output": "Tool\noutput",
}
ATTACK_NAMES = {
    "ALL": "All attacks",
    "inject_override": "Blunt override",
    "inject_owner_note": "Owner note",
    "inject_cc_request": "Casual request",
}
DEFENSE_ORDER = ("none", "spotlight", "sandwich", "tool_policy", "detector")
DEFENSE_NAMES = {
    "none": "none",
    "spotlight": "spotlight",
    "sandwich": "sandwich",
    "tool_policy": "tool policy",
    "detector": "detector",
}


def _style() -> None:
    plt.rcParams.update(
        {
            "figure.facecolor": SURFACE,
            "axes.facecolor": SURFACE,
            "savefig.facecolor": SURFACE,
            "axes.edgecolor": AXIS,
            "axes.labelcolor": INK2,
            "axes.titlecolor": INK,
            "text.color": INK,
            "xtick.color": MUTED,
            "ytick.color": MUTED,
            "grid.color": GRID,
            "grid.linewidth": 0.8,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "font.family": "sans-serif",
            "font.sans-serif": ["Segoe UI", "Helvetica", "Arial", "DejaVu Sans"],
            "font.size": 10,
        }
    )


def _slug(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_")


def fig_asr_heatmap(rows: Sequence[AsrRow], out_dir: Path) -> list[Path]:
    """Heatmap of ASR by language (rows) and channel (columns): one panel per attack + pool."""
    _style()
    out_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    cmap = LinearSegmentedColormap.from_list("blue", BLUE_RAMP).with_extremes(bad="#efeee9")
    for tag in sorted({r.model_tag for r in rows}):
        mine = [r for r in rows if r.model_tag == tag]
        langs = [x for x in LANGUAGES if any(r.language == x for r in mine)]
        chans = [c for c in CHANNELS if any(r.channel == c for r in mine)]
        attacks = ["ALL"] + [
            a for a in ATTACK_NAMES if a != "ALL" and any(r.attack == a for r in mine)
        ]
        fig, axes = plt.subplots(
            1,
            len(attacks),
            figsize=(3.3 * len(attacks) + 1.4, 0.62 * len(langs) + 2.5),
            squeeze=False,
            sharey=True,
        )
        mesh: Any = None
        for ax, attack in zip(axes[0], attacks, strict=True):
            grid = np.full((len(langs), len(chans)), np.nan)
            cell = {(r.language, r.channel): r for r in mine if r.attack == attack}
            for i, lang in enumerate(langs):
                for j, ch in enumerate(chans):
                    if (lang, ch) in cell:
                        grid[i, j] = cell[(lang, ch)].rate
            mesh = ax.pcolormesh(
                np.ma.masked_invalid(grid),
                cmap=cmap,
                vmin=0,
                vmax=1,
                edgecolors=SURFACE,
                linewidth=2,
            )
            ax.set_xlim(0, len(chans))
            ax.set_ylim(len(langs), 0)
            ax.set_xticks(np.arange(len(chans)) + 0.5, [CHANNEL_NAMES[c] for c in chans])
            ax.set_yticks(np.arange(len(langs)) + 0.5, [LANG_NAMES[x] for x in langs])
            ax.tick_params(length=0)
            for spine in ax.spines.values():
                spine.set_visible(False)
            ns = [cell[k].n for k in cell]
            n_text = f"n = {min(ns)}" if ns and min(ns) == max(ns) else "n varies"
            ax.set_title(f"{ATTACK_NAMES.get(attack, attack)}  ({n_text} per cell)", fontsize=10)
            for i, lang in enumerate(langs):
                for j, ch in enumerate(chans):
                    r = cell.get((lang, ch))
                    if r is None:
                        ax.text(j + 0.5, i + 0.5, "n/a", ha="center", va="center", color=MUTED)
                        continue
                    ink = "#ffffff" if r.rate > 0.45 else INK
                    ax.text(
                        j + 0.5,
                        i + 0.4,
                        f"{r.rate:.0%}",
                        ha="center",
                        va="center",
                        color=ink,
                        fontsize=11,
                    )
                    ax.text(
                        j + 0.5,
                        i + 0.68,
                        f"{r.k}/{r.n}",
                        ha="center",
                        va="center",
                        color=ink,
                        fontsize=8,
                    )
        cbar = fig.colorbar(mesh, ax=list(axes.ravel()), fraction=0.02, pad=0.02)
        cbar.set_label("Attack success rate", color=INK2)
        cbar.outline.set_visible(False)
        cbar.ax.tick_params(length=0)
        cbar.set_ticks([0, 0.25, 0.5, 0.75, 1])
        cbar.set_ticklabels(["0%", "25%", "50%", "75%", "100%"])
        fig.suptitle(
            f"Attack success rate by language and channel, no defense\n{tag}",
            x=0.01,
            y=1.04,
            ha="left",
            fontsize=12,
        )
        fig.text(
            0.01,
            0.01,
            "Cell: rate and successes/runs. Runs share tasks, so intervals are approximate "
            "(95% Wilson intervals are in the CSV).",
            color=MUTED,
            fontsize=8,
        )
        path = out_dir / f"fig1_asr_heatmap_{_slug(tag)}.png"
        fig.savefig(path, dpi=200, bbox_inches="tight")
        plt.close(fig)
        paths.append(path)
    return paths


def _bars(ax: Any, labels: list[str], ks: list[int], ns: list[int]) -> None:
    """Bars with Wilson whiskers; the first bar (baseline) is gray, the others blue."""
    xs = np.arange(len(labels))
    rates = np.array([k / n for k, n in zip(ks, ns, strict=True)])
    cis = np.array([wilson(k, n) for k, n in zip(ks, ns, strict=True)])
    colors = [GRAY] + [BLUE] * (len(labels) - 1)
    ax.bar(xs, rates, width=0.55, color=colors, zorder=3)
    ax.errorbar(
        xs,
        rates,
        yerr=[rates - cis[:, 0], cis[:, 1] - rates],
        fmt="none",
        ecolor=INK2,
        elinewidth=1,
        capsize=3,
        zorder=4,
    )
    ax.set_ylim(0, 1.08)
    ax.set_yticks([0, 0.25, 0.5, 0.75, 1], ["0%", "25%", "50%", "75%", "100%"])
    ax.set_xticks(
        xs,
        [f"{lab}\n{k / n:.0%}\n{k}/{n}" for lab, k, n in zip(labels, ks, ns, strict=True)],
        fontsize=8,
    )
    ax.grid(axis="y", zorder=0)
    ax.set_axisbelow(True)
    ax.tick_params(length=0)
    ax.spines["left"].set_visible(False)


def fig_defense_effect(effects: Sequence[EffectRow], out_dir: Path) -> list[Path]:
    """ASR by defense for each language (top) and benign task success by defense (bottom)."""
    _style()
    out_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for tag in sorted({e.model_tag for e in effects}):
        mine = [e for e in effects if e.model_tag == tag]
        langs = [x for x in LANGUAGES if any(e.language == x for e in mine)]
        defenses = [d for d in DEFENSE_ORDER if d != "none" and any(e.defense == d for e in mine)]
        fig = plt.figure(figsize=(3.9 * len(langs) + 0.4, 7.4))
        gs = fig.add_gridspec(2, len(langs), height_ratios=[1.25, 1], hspace=0.55)
        for col, lang in enumerate(langs):
            ax = fig.add_subplot(gs[0, col])
            by = {e.defense: e for e in mine if e.language == lang}
            first = by[defenses[0]]
            labels = ["none"] + [DEFENSE_NAMES[d] for d in defenses if d in by]
            ks = [first.base_asr_k] + [by[d].asr_k for d in defenses if d in by]
            ns = [first.base_asr_n] + [by[d].asr_n for d in defenses if d in by]
            _bars(ax, labels, ks, ns)
            ax.set_title(f"{LANG_NAMES[lang]}", fontsize=10)
            if col == 0:
                ax.set_ylabel("Attack success rate")
        ax = fig.add_subplot(gs[1, :])
        first = mine[0]
        by_def = {e.defense: e for e in mine}
        labels = ["none"] + [DEFENSE_NAMES[d] for d in defenses if d in by_def]
        ks = [first.base_utility_k] + [by_def[d].utility_k for d in defenses if d in by_def]
        ns = [first.base_utility_n] + [by_def[d].utility_n for d in defenses if d in by_def]
        _bars(ax, labels, ks, ns)
        ax.set_title("Benign task success (utility), all languages", fontsize=10)
        ax.set_ylabel("Task success rate")
        fig.suptitle(
            f"Effect of each defense on attack success and on task success\n{tag}",
            x=0.01,
            y=0.99,
            ha="left",
            fontsize=12,
        )
        fig.text(
            0.01,
            0.005,
            "Gray = no defense on the same scenarios. Whiskers: 95% Wilson interval. "
            f"Channels: {first.channels}.",
            color=MUTED,
            fontsize=8,
        )
        path = out_dir / f"fig2_defense_effect_{_slug(tag)}.png"
        fig.savefig(path, dpi=200, bbox_inches="tight")
        plt.close(fig)
        paths.append(path)
    return paths


def fig_tradeoff(effects: Sequence[EffectRow], out_dir: Path) -> list[Path]:
    """Protection (ASR reduction) against cost (utility change), one panel per language."""
    _style()
    out_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for tag in sorted({e.model_tag for e in effects}):
        mine = [e for e in effects if e.model_tag == tag]
        langs = [x for x in LANGUAGES if any(e.language == x for e in mine)]
        fig, axes = plt.subplots(
            1, len(langs), figsize=(4.2 * len(langs), 4.6), squeeze=False, sharex=True, sharey=True
        )
        for ax, lang in zip(axes[0], langs, strict=True):
            ax.axhline(0, color=AXIS, linewidth=1, zorder=1)
            ax.axvline(0, color=AXIS, linewidth=1, zorder=1)
            ax.grid(True, zorder=0)
            ax.set_axisbelow(True)
            for e in (e for e in mine if e.language == lang):
                ax.errorbar(
                    e.utility_change_pp,
                    e.reduction_pp,
                    xerr=[
                        [e.utility_change_pp - e.utility_change_lo_pp],
                        [e.utility_change_hi_pp - e.utility_change_pp],
                    ],
                    yerr=[
                        [e.reduction_pp - e.reduction_lo_pp],
                        [e.reduction_hi_pp - e.reduction_pp],
                    ],
                    fmt="o",
                    color=BLUE,
                    ecolor=GRAY,
                    elinewidth=1,
                    markersize=8,
                    markeredgecolor=SURFACE,
                    markeredgewidth=1.5,
                    zorder=3,
                )
                ax.annotate(
                    DEFENSE_NAMES.get(e.defense, e.defense),
                    (e.utility_change_pp, e.reduction_pp),
                    xytext=(7, 7),
                    textcoords="offset points",
                    fontsize=9,
                    color=INK,
                )
            ax.set_title(LANG_NAMES[lang], fontsize=10)
            ax.tick_params(length=0)
            ax.set_xlabel("Change in task success (pp; left = costs utility)")
        axes[0][0].set_ylabel("ASR reduction vs no defense (pp; up = safer)")
        fig.suptitle(
            f"Protection versus cost of each defense\n{tag}", x=0.01, ha="left", fontsize=12
        )
        fig.text(
            0.01,
            -0.02,
            "Whiskers: 95% Newcombe intervals for a difference (conservative: they ignore that the "
            "same scenarios ran under both settings).",
            color=MUTED,
            fontsize=8,
        )
        path = out_dir / f"fig3_tradeoff_{_slug(tag)}.png"
        fig.savefig(path, dpi=200, bbox_inches="tight")
        plt.close(fig)
        paths.append(path)
    return paths
