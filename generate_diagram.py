"""Generates architecture.png — a system diagram for PawPal+."""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch

OUT_FILE = "assets/architecture.png"


def add_box(ax, cx, cy, w, h, text, facecolor, edgecolor="#2c2c2c",
            fontsize=9, text_color="white", style="round,pad=0.15", lw=1.8):
    box = FancyBboxPatch((cx - w / 2, cy - h / 2), w, h,
                         boxstyle=style, facecolor=facecolor,
                         edgecolor=edgecolor, linewidth=lw, zorder=3)
    ax.add_patch(box)
    ax.text(cx, cy, text, ha="center", va="center", fontsize=fontsize,
            color=text_color, fontweight="bold", zorder=4,
            multialignment="center", linespacing=1.4)


def add_arrow(ax, x1, y1, x2, y2, label="", label_dx=0.15):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle="-|>", color="#444",
                                lw=1.6, mutation_scale=14),
                zorder=2)
    if label:
        mx, my = (x1 + x2) / 2 + label_dx, (y1 + y2) / 2
        ax.text(mx, my, label, fontsize=7.5, color="#555", style="italic",
                ha="left", va="center")


def add_dashed_box(ax, cx, cy, w, h, label, color="#888"):
    box = FancyBboxPatch((cx - w / 2, cy - h / 2), w, h,
                         boxstyle="round,pad=0.1", facecolor="#f0f4ff",
                         edgecolor=color, linewidth=1.5, linestyle="--", zorder=1)
    ax.add_patch(box)
    ax.text(cx - w / 2 + 0.15, cy + h / 2 - 0.18, label,
            fontsize=7.5, color=color, style="italic", va="top", zorder=4)


# ── colours ────────────────────────────────────────────────────────────────
C_USER    = "#5c7cfa"
C_UI      = "#339af0"
C_RAG     = "#20c997"
C_KB      = "#51cf66"
C_SCHED   = "#94d82d"
C_GEMINI  = "#f76707"
C_LOG     = "#868e96"
C_HUMAN   = "#cc5de8"

fig, ax = plt.subplots(figsize=(11, 13))
fig.patch.set_facecolor("#fafafa")
ax.set_xlim(0, 11)
ax.set_ylim(0, 13)
ax.axis("off")

# ── title ───────────────────────────────────────────────────────────────────
ax.text(5.5, 12.5, "PawPal+ — System Architecture",
        ha="center", va="center", fontsize=14, fontweight="bold", color="#1a1a2e")

# ── main column (x=5.5) ─────────────────────────────────────────────────────
# 1. User
add_box(ax, 5.5, 11.5, 2.8, 0.65, "[ User ]", C_USER)

# 2. Streamlit UI
add_box(ax, 5.5, 10.3, 3.4, 0.7, "Streamlit UI\napp.py", C_UI)

# RAG pipeline dashed container
add_dashed_box(ax, 5.5, 7.8, 7.6, 3.6, "RAG Pipeline  ·  rag.py", "#2c7be5")

# 3. Retriever
add_box(ax, 3.7, 8.7, 2.8, 0.65, "Retriever\nkeyword overlap scoring", C_RAG, fontsize=8)

# 4. Knowledge Base
add_box(ax, 2.0, 7.5, 2.6, 0.65, "Knowledge Base\n5 markdown files", C_KB, fontsize=8)

# 5. Pet context from scheduler
add_box(ax, 7.3, 8.7, 2.8, 0.65, "Pet Context\nfrom Scheduler", C_SCHED,
        text_color="#1a1a1a", fontsize=8)

# 6. Prompt builder
add_box(ax, 5.5, 7.1, 3.2, 0.65, "Prompt Builder\nchunks + context + question", C_RAG, fontsize=8)

# 7. Gemini API
add_box(ax, 5.5, 5.6, 3.4, 0.7, "Gemini 2.0 Flash API\n(Google AI)", C_GEMINI)

# 8. Answer + sources
add_box(ax, 5.5, 4.2, 3.4, 0.7, "Answer  +  Retrieved Sources\n(returned to UI)", C_UI)

# 9. Human review
add_box(ax, 5.5, 2.9, 3.8, 0.7,
        "User Reviews Answer\n& Verifies Sources", C_HUMAN)

# ── logger (right side) ──────────────────────────────────────────────────────
add_box(ax, 9.5, 7.5, 2.0, 4.2,
        "Logger\n\npawpal.log\n\n· chunks retrieved\n· token counts\n· retries\n· errors",
        C_LOG, fontsize=8, style="round,pad=0.2")

# ── arrows ───────────────────────────────────────────────────────────────────
# User → Streamlit
add_arrow(ax, 5.5, 11.17, 5.5, 10.65, "question")

# Streamlit → Retriever
add_arrow(ax, 4.8, 9.95, 3.9, 9.03)

# Streamlit → Pet Context
add_arrow(ax, 6.2, 9.95, 7.1, 9.03)

# Retriever ← Knowledge Base
add_arrow(ax, 2.7, 7.5, 3.3, 8.38, "top-3 chunks")

# Retriever → Prompt Builder
add_arrow(ax, 4.2, 8.38, 5.0, 7.43)

# Pet Context → Prompt Builder
add_arrow(ax, 6.8, 8.38, 6.0, 7.43)

# Prompt Builder → Gemini
add_arrow(ax, 5.5, 6.77, 5.5, 5.95, "prompt")

# Gemini → Answer
add_arrow(ax, 5.5, 5.25, 5.5, 4.55, "response")

# Answer → Human review
add_arrow(ax, 5.5, 3.85, 5.5, 3.25)

# Logger monitoring arrows (dashed)
for y_src in [8.7, 7.1, 5.6]:
    ax.annotate("", xy=(8.5, 7.5), xytext=(7.1, y_src),
                arrowprops=dict(arrowstyle="-", color="#aaa",
                                lw=1.0, linestyle="dotted"),
                zorder=1)

# ── legend ───────────────────────────────────────────────────────────────────
legend_items = [
    mpatches.Patch(color=C_USER,   label="User / Human"),
    mpatches.Patch(color=C_UI,     label="Streamlit UI"),
    mpatches.Patch(color=C_RAG,    label="RAG components"),
    mpatches.Patch(color=C_KB,     label="Knowledge Base"),
    mpatches.Patch(color=C_SCHED,  label="Pet Scheduler"),
    mpatches.Patch(color=C_GEMINI, label="Gemini API (external)"),
    mpatches.Patch(color=C_LOG,    label="Logger / Guardrails"),
    mpatches.Patch(color=C_HUMAN,  label="Human oversight"),
]
ax.legend(handles=legend_items, loc="lower left", fontsize=7.5,
          framealpha=0.9, ncol=2, bbox_to_anchor=(0.0, 0.0))

plt.tight_layout()
plt.savefig(OUT_FILE, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
print(f"Saved {OUT_FILE}")
