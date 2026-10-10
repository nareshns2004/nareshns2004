#!/usr/bin/env python3
"""Generate the profile README's SVG assets (light + dark variants).

    python3 scripts/build_assets.py

Writes assets/banner-{light,dark}.svg, assets/stack-{light,dark}.svg and
assets/systems-{light,dark}.svg and assets/pfc-{light,dark}.svg.
Standard library only. Brand icon paths come from Simple Icons (CC0) and are
cached in scripts/brand-icons.json; everything else is drawn here.

GitHub renders README images as <img>: no scripts and no web fonts, but CSS
animations, media queries and prefers-reduced-motion inside the SVG all work.
Sizes are drawn at ~880 px wide, the width of the profile README column, so
text renders close to 1:1.
"""
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets"
BRANDS = json.loads((ROOT / "scripts" / "brand-icons.json").read_text())

SANS = "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans', Helvetica, Arial, sans-serif"
MONO = "ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, 'Liberation Mono', monospace"

# The portfolio's "datasheet" palette.
THEMES = {
    "light": dict(paper="#F7F5F0", paper2="#EFECE4", rule="#D9D4C7", rule2="#BDB6A6", ink="#15171C",
                  ink2="#353A44", graphite="#555C6A", signal="#1D4ED8", copper="#B4470E", fault="#C2261D"),
    "dark": dict(paper="#10151D", paper2="#171E29", rule="#2A3341", rule2="#3B4656", ink="#ECE8E0",
                 ink2="#CFCAC0", graphite="#A3ABB8", signal="#86A8FF", copper="#F0935C", fault="#FF7D73"),
}
# Brand colours too faint on the light Paper background are drawn in Ink there.
LOW_CONTRAST_ON_LIGHT = {"c", "linux", "huggingface"}


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ───────────────────────────── banner ─────────────────────────────

def banner(t):
    W, H = 880, 300
    CX, CY, R = 712, 140, 88
    N = 8
    cycle = 12  # seconds
    pos = [(CX + R * math.cos(-math.pi / 2 + 2 * math.pi * i / N),
            CY + R * math.sin(-math.pi / 2 + 2 * math.pi * i / N)) for i in range(N)]

    # Timeline (% of the 12 s cycle): flow 0–40, link fails 40, stall spreads 41–60,
    # all ranks time out 60–74, restore on spare 74–85, resume 85–100.
    css = [f"""
    .k {{ font: 600 12.5px {MONO}; letter-spacing: .08em; fill: {t['graphite']}; }}
    .h {{ font: 600 26px {SANS}; fill: {t['ink']}; letter-spacing: -.01em; }}
    .s {{ fill: {t['copper']}; }} .r {{ fill: {t['signal']}; }}
    .sub {{ font: 500 13px {MONO}; fill: {t['ink2']}; }}
    .node rect {{ fill: {t['paper']}; stroke: {t['ink']}; stroke-width: 1.4; }}
    .node text {{ font: 600 11px {MONO}; fill: {t['ink']}; text-anchor: middle; }}
    .edge {{ stroke: {t['ink']}; stroke-width: 1.3; }}
    .lbl {{ font: 600 12px {MONO}; text-anchor: middle; opacity: 0; }}
    .cap {{ font: 500 11px {MONO}; fill: {t['graphite']}; letter-spacing: .06em; }}
    .pk {{ fill: {t['signal']}; }}
    .spin {{ transform-box: view-box; transform-origin: {CX}px {CY}px; animation: spin {cycle}s linear infinite; }}
    @keyframes spin {{ 0% {{ transform: rotate(0deg); }} 40% {{ transform: rotate(225deg); }}
                      85% {{ transform: rotate(225deg); }} 100% {{ transform: rotate(360deg); }} }}
    .bad {{ animation: bad {cycle}s step-end infinite; stroke: {t['ink']}; }}
    @keyframes bad {{ 0% {{ stroke: {t['ink']}; stroke-dasharray: none; }} 40% {{ stroke: {t['fault']}; stroke-dasharray: 5 4; stroke-width: 2.2; }}
                     85% {{ stroke: {t['ink']}; stroke-dasharray: none; stroke-width: 1.3; }} }}
    .x {{ stroke: {t['fault']}; stroke-width: 2.6; opacity: 0; animation: x {cycle}s step-end infinite; }}
    @keyframes x {{ 0% {{ opacity: 0; }} 40% {{ opacity: 1; }} 85% {{ opacity: 0; }} }}
    """]
    # ≤ 16 chars each so they fit between GPU6 and GPU2
    labels = [("all ranks busy", t['graphite'], 0, 40), ("link 2→3 fails", t['fault'], 40, 46),
              ("stall spreads", t['copper'], 46, 60), ("all 8 time out", t['fault'], 60, 74),
              ("restore → spare", t['signal'], 74, 85), ("training resumes", t['graphite'], 85, 100)]
    for i, (_, _, a, b) in enumerate(labels):
        frames = f"0% {{ opacity: {1 if a == 0 else 0}; }}"
        if a > 0:
            frames += f" {a}% {{ opacity: 1; }}"
        if b < 100:
            frames += f" {b}% {{ opacity: 0; }}"
        css.append(f".l{i} {{ animation: l{i} {cycle}s step-end infinite; }} @keyframes l{i} {{ {frames} }}")
    # Per-node state: waiting (copper) as the stall reaches it, fault at timeout, back to ink on resume.
    order = [(3 + j) % N for j in range(N)]
    for j, n in enumerate(order):
        start = 46 + j * 14 / N
        css.append(
            f".n{n} rect {{ animation: n{n} {cycle}s step-end infinite; }} "
            f"@keyframes n{n} {{ 0% {{ stroke: {t['ink']}; }} {start:.1f}% {{ stroke: {t['copper']}; stroke-dasharray: 4 3; }} "
            f"60% {{ stroke: {t['fault']}; stroke-dasharray: none; }} 74% {{ stroke: {t['ink']}; }} }}")
    # Spare swaps in for GPU3 during restore.
    css.append(f".spare {{ opacity: 0; animation: spare {cycle}s step-end infinite; }} @keyframes spare {{ 0% {{ opacity: 0; }} 74% {{ opacity: 1; }} 100% {{ opacity: 1; }} }}"
               f".orig {{ animation: orig {cycle}s step-end infinite; }} @keyframes orig {{ 0% {{ opacity: 1; }} 74% {{ opacity: 0; }} }}")
    # Goodput bar: segments grow in their windows.
    BX, BY, BW = 600, 258, 224
    segs = [("blue", 0, 40), ("stall", 40, 74), ("restart", 74, 85), ("blue", 85, 100)]
    bar = []
    for i, (kind, a, b) in enumerate(segs):
        x = BX + BW * a / 100
        w = BW * (b - a) / 100
        fill = {"blue": t['signal'], "stall": "url(#hatch)", "restart": t['fault']}[kind]
        css.append(f".g{i} {{ transform-box: fill-box; transform-origin: left center; animation: g{i} {cycle}s linear infinite; }}"
                   f"@keyframes g{i} {{ 0% {{ transform: scaleX(0); }} {a}% {{ transform: scaleX(0); }} {b}% {{ transform: scaleX(1); }} 100% {{ transform: scaleX(1); }} }}")
        bar.append(f'<rect class="g{i}" x="{x:.1f}" y="{BY}" width="{w:.1f}" height="12" fill="{fill}"/>')
    css.append("""@media (prefers-reduced-motion: reduce) {
      .spin, .bad, .x, .lbl, .node rect, .spare, .orig, [class^="g"] { animation: none !important; }
      .l4 { opacity: 1; } .spare { opacity: 1; } .orig { opacity: 0; }
      .x { opacity: 0; } [class^="g"] { transform: none; } }""")

    edges = []
    for i in range(N):
        (x1, y1), (x2, y2) = pos[i], pos[(i + 1) % N]
        cls = "edge bad" if i == 2 else "edge"
        edges.append(f'<line class="{cls}" x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}"/>')
    (x1, y1), (x2, y2) = pos[2], pos[3]
    mx, my = (x1 + x2) / 2, (y1 + y2) / 2
    edges.append(f'<path class="x" d="M{mx-6:.1f},{my-6:.1f} L{mx+6:.1f},{my+6:.1f} M{mx+6:.1f},{my-6:.1f} L{mx-6:.1f},{my+6:.1f}"/>')
    packets = "".join(
        f'<circle class="pk" cx="{CX + R * 0.93 * math.cos(-math.pi / 2 + 2 * math.pi * (i + .5) / N):.1f}" '
        f'cy="{CY + R * 0.93 * math.sin(-math.pi / 2 + 2 * math.pi * (i + .5) / N):.1f}" r="3.6"/>' for i in range(N))
    nodes = []
    for i, (x, y) in enumerate(pos):
        lab = f'<text x="{x:.1f}" y="{y+4:.1f}">GPU{i}</text>'
        if i == 3:
            lab = (f'<g class="orig">{lab}</g><g class="spare"><text x="{x:.1f}" y="{y+4:.1f}">GPU3′</text></g>')
        nodes.append(f'<g class="node n{i}"><rect x="{x-24:.1f}" y="{y-12:.1f}" width="48" height="24" rx="2"/>{lab}</g>')
    lbls = "".join(f'<text class="lbl l{i}" x="{CX}" y="{CY+18}" fill="{c}">{esc(s)}</text>' for i, (s, c, _, _) in enumerate(labels))

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-labelledby="t d">
<title id="t">Naresh Kumar: GPU cluster networking and distributed-training infrastructure</title>
<desc id="d">A GPU cluster is only as fast as its slowest link and as reliable as its weakest. I make it lose less time to both. An animated ring of eight GPUs loses a link, every rank stalls and times out, the job restores onto a spare and resumes; a goodput timeline records the cost.</desc>
<defs><pattern id="hatch" width="5" height="5" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="5" height="5" fill="{t['paper2']}"/><line x1="0" y1="0" x2="0" y2="5" stroke="{t['graphite']}" stroke-width="1.6"/></pattern></defs>
<style>{''.join(css)}</style>
<rect x=".5" y=".5" width="{W-1}" height="{H-1}" rx="12" fill="{t['paper']}" stroke="{t['rule']}"/>
<text class="k" x="36" y="48">NARESH KUMAR</text>
<text class="k" x="36" y="68" style="font-weight:500">GPU CLUSTER NETWORKING · DISTRIBUTED-TRAINING INFRA</text>
<text class="h" x="36" y="116">A GPU cluster is only as fast as its</text>
<text class="h" x="36" y="150"><tspan class="s">slowest link</tspan> and as reliable as its</text>
<text class="h" x="36" y="184"><tspan class="r">weakest</tspan>. I make it lose less time</text>
<text class="h" x="36" y="218">to both.</text>
<text class="sub" x="36" y="262">Distributed Systems &amp; GPU Networking Engineering</text>
<text class="sub" x="36" y="281" style="fill:{t['graphite']}">RDMA · RoCE · NCCL · DPDK · SR-IOV · KVM · eBPF</text>
<line x1="560" y1="28" x2="560" y2="272" stroke="{t['rule']}"/>
<text class="cap" x="580" y="30">FIG. 0 · RING ALL-REDUCE</text>
{''.join(edges)}
<g class="spin">{packets}</g>
{''.join(nodes)}
<text x="{CX}" y="{CY-2}" text-anchor="middle" style="font:500 11px {MONO};fill:{t['graphite']}">8 ranks</text>
{lbls}
<rect x="{BX}" y="{BY}" width="{BW}" height="12" fill="none" stroke="{t['rule2']}"/>
{''.join(bar)}
<text class="cap" x="{BX}" y="{BY+28}">GOODPUT · blue = training</text>
</svg>
"""


# ───────────────────────────── stack ─────────────────────────────

# Custom glyphs for concepts that have no logo (24×24, stroked).
GLYPHS = {
    "gpu": '<rect x="4" y="6" width="16" height="12" rx="1.5"/><rect x="8" y="9.5" width="8" height="5" rx=".5"/><path d="M7 3v3M10.5 3v3M14 3v3M17 3v3M7 18v3M10.5 18v3M14 18v3M17 18v3"/>',
    "nvlink": '<rect x="2" y="7" width="7" height="10" rx="1"/><rect x="15" y="7" width="7" height="10" rx="1"/><path d="M9 10.5h6M9 13.5h6"/>',
    "nccl": '<circle cx="12" cy="12" r="7"/><circle cx="12" cy="5" r="2" class="f"/><circle cx="19" cy="12" r="2" class="f"/><circle cx="12" cy="19" r="2" class="f"/><circle cx="5" cy="12" r="2" class="f"/>',
    "rdma": '<rect x="2" y="13" width="6" height="7" rx="1"/><rect x="16" y="13" width="6" height="7" rx="1"/><path d="M8 16.5h7.5M13 14l2.5 2.5L13 19"/><rect x="9" y="3.5" width="6" height="5" rx="1" stroke-dasharray="2 1.6"/><path d="M10 4.5l4 3M14 4.5l-4 3"/>',
    "roce": '<rect x="4" y="6" width="16" height="13" rx="1.5"/><path d="M8 19v-4h8v4M9 9.5h1M11.5 9.5h1M14 9.5h1"/>',
    "ib": '<path d="M4 12c0-4.5 5-4.5 8 0s8 4.5 8 0-5-4.5-8 0-8 4.5-8 0z"/>',
    "gdr": '<rect x="2" y="9" width="6" height="6" rx="1"/><rect x="14" y="6" width="8" height="12" rx="1"/><path d="M8 12h4.5M10.5 9.8l2.2 2.2-2.2 2.2"/><path d="M16.5 9v6M19.5 9v6"/>',
    "pfc": '<circle cx="12" cy="12" r="8.5"/><path d="M9.5 8.5v7M14.5 8.5v7" stroke-width="2.4"/>',
    "rail": '<path d="M6 5v14M12 5v14M18 5v14"/><circle cx="6" cy="5" r="1.6" class="f"/><circle cx="12" cy="5" r="1.6" class="f"/><circle cx="18" cy="5" r="1.6" class="f"/><circle cx="6" cy="19" r="1.6" class="f"/><circle cx="12" cy="19" r="1.6" class="f"/><circle cx="18" cy="19" r="1.6" class="f"/>',
    "ebpf": '<path d="M12 2.8l7.8 4.5v9.4L12 21.2l-7.8-4.5V7.3z"/><path d="M10 9l-2.5 3L10 15M14 9l2.5 3L14 15"/>',
    "dpdk": '<path d="M3 9h18M3 15h18" stroke-dasharray="2 2"/><path d="M12 21V4M8.8 7.2L12 4l3.2 3.2"/>',
    "sriov": '<rect x="7" y="3" width="10" height="5" rx="1"/><rect x="2" y="16" width="5" height="5" rx="1"/><rect x="9.5" y="16" width="5" height="5" rx="1"/><rect x="17" y="16" width="5" height="5" rx="1"/><path d="M12 8v4M4.5 16v-4h15v4M12 12v4"/>',
    "kvm": '<rect x="3" y="4.5" width="13" height="10" rx="1"/><rect x="8" y="9.5" width="13" height="10" rx="1" class="bg"/>',
    "trace": '<rect x="3" y="16" width="18" height="4" rx=".5"/><rect x="3" y="11" width="11" height="4" rx=".5"/><rect x="15" y="11" width="5" height="4" rx=".5"/><rect x="5" y="6" width="7" height="4" rx=".5"/>',
    "cuda": '<rect x="4" y="4" width="4.5" height="4.5" rx=".6"/><rect x="9.75" y="4" width="4.5" height="4.5" rx=".6"/><rect x="15.5" y="4" width="4.5" height="4.5" rx=".6"/><rect x="4" y="9.75" width="4.5" height="4.5" rx=".6"/><rect x="9.75" y="9.75" width="4.5" height="4.5" rx=".6" class="f"/><rect x="15.5" y="9.75" width="4.5" height="4.5" rx=".6"/><rect x="4" y="15.5" width="4.5" height="4.5" rx=".6"/><rect x="9.75" y="15.5" width="4.5" height="4.5" rx=".6"/><rect x="15.5" y="15.5" width="4.5" height="4.5" rx=".6"/>',
    "triton": '<rect x="4" y="4" width="16" height="16" rx="1"/><path d="M4 9.3h16M4 14.6h16M9.3 4v16M14.6 4v16"/><rect x="9.3" y="9.3" width="5.3" height="5.3" class="f"/>',
    "kv": '<rect x="3.5" y="4" width="7" height="4" rx=".6"/><rect x="3.5" y="10" width="7" height="4" rx=".6"/><rect x="3.5" y="16" width="7" height="4" rx=".6"/><rect x="13.5" y="4" width="7" height="4" rx=".6" class="f"/><rect x="13.5" y="10" width="7" height="4" rx=".6" class="f"/><rect x="13.5" y="16" width="7" height="4" rx=".6" class="f"/>',
    "par": '<rect x="3" y="9" width="9" height="9" rx="1"/><rect x="7.5" y="5.5" width="9" height="9" rx="1" class="bg"/><rect x="12" y="2" width="9" height="9" rx="1" class="bg"/>',
    "ckpt": '<path d="M19.5 12A7.5 7.5 0 1 1 17 6.4"/><path d="M17.5 2.5v4.2h-4.2"/><circle cx="12" cy="12" r="2" class="f"/>',
    "slurm": '<path d="M4 6h16M4 10.5h11M4 15h14M4 19.5h7"/>',
    "dcgm": '<path d="M2 12h5l2-6 3 12 3-9 2 3h5"/>',
    "nic": '<rect x="2.5" y="6" width="19" height="10" rx="1"/><rect x="5" y="9" width="4" height="4" rx=".5"/><rect x="11" y="9" width="4" height="4" rx=".5"/><path d="M4 16v3M7 16v3M10 16v3M13 16v3"/>',
    "pcie": '<rect x="3" y="5" width="18" height="10" rx="1"/><path d="M5 15v4M7.5 15v4M10 15v4M14 15v4M16.5 15v4M19 15v4"/>',
}

LAYERS = [
    ("L5", "Models & serving", "training loops, LLM inference, kernels",
     [("b:pytorch", "PyTorch"), ("b:vllm", "vLLM"), ("b:huggingface", "Hugging Face"), ("g:cuda", "CUDA"),
      ("g:triton", "Triton kernels"), ("g:kv", "KV cache")],
     ["kvwire", "triton kernels", "HF models"]),
    ("L4", "Collectives & orchestration", "many GPUs acting as one job",
     [("g:nccl", "NCCL"), ("g:par", "DP·TP·PP"), ("g:ckpt", "checkpoint restart"), ("b:ray", "Ray"),
      ("g:slurm", "Slurm"), ("b:kubernetes", "Kubernetes")],
     ["goodput", "dist-training-nccl"]),
    ("L3", "Transport & fabric", "bytes between GPUs across nodes",
     [("g:rdma", "RDMA verbs"), ("g:roce", "RoCE v2"), ("g:ib", "InfiniBand"), ("g:gdr", "GPUDirect RDMA"),
      ("g:pfc", "PFC · ECN"), ("g:rail", "rail optimized")],
     ["nicprof", "kvwire"]),
    ("L2", "Host datapath", "kernel, drivers, virtualization",
     [("b:linux", "Linux net"), ("g:ebpf", "eBPF · XDP"), ("g:dpdk", "DPDK"), ("g:sriov", "SR-IOV"),
      ("g:kvm", "KVM · virtio"), ("g:trace", "perf · ftrace")],
     ["kptk", "traffic-shaper"]),
    ("L1", "Hardware", "the parts that fail, and the links",
     [("b:nvidia", "NVIDIA GPUs"), ("g:nvlink", "NVLink"), ("g:nic", "RDMA NICs"), ("g:pcie", "PCIe"),
      ("g:gpu", "GPU health")],
     ["nicprof"]),
]
EXTRA = [
    ("Run & observe", [("b:docker", "Docker"), ("b:prometheus", "Prometheus"), ("b:grafana", "Grafana"), ("g:dcgm", "DCGM")]),
    ("Languages", [("b:c", "C"), ("b:cplusplus", "C++"), ("b:python", "Python"), ("b:go", "Go"), ("b:gnubash", "Bash")]),
]


def chip(t, theme, kind, label, x, y):
    out = [f'<rect x="{x}" y="{y}" width="52" height="52" rx="10" class="tile"/>']
    if kind.startswith("b:"):
        slug = kind[2:]
        color = t['ink'] if (theme == "light" and slug in LOW_CONTRAST_ON_LIGHT) else "#" + BRANDS[slug]['hex']
        out.append(f'<svg x="{x+13}" y="{y+13}" width="26" height="26" viewBox="0 0 24 24"><path d="{BRANDS[slug]["path"]}" fill="{color}"/></svg>')
    else:
        out.append(f'<svg x="{x+12}" y="{y+12}" width="28" height="28" viewBox="0 0 24 24" class="glyph">{GLYPHS[kind[2:]]}</svg>')
    words = label.split(" ")
    lines, cur = [], ""
    for w in words:
        if len(cur) + len(w) + (1 if cur else 0) > 10 and cur:
            lines.append(cur); cur = w
        else:
            cur = f"{cur} {w}".strip()
    lines.append(cur)
    for i, ln in enumerate(lines[:2]):
        out.append(f'<text x="{x+26}" y="{y+68+i*14}" class="cl">{esc(ln)}</text>')
    return "".join(out)


def stack(t, theme):
    W = 880
    ROW = 110
    TOP = 56
    LX, CX0, PITCH, EX = 30, 262, 74, 712
    rows = len(LAYERS) + len(EXTRA)
    H = TOP + rows * ROW + 24
    datapath_x = 246
    css = f"""
    .ln {{ font: 600 12px {MONO}; fill: {t['signal']}; letter-spacing: .06em; }}
    .lt {{ font: 600 16px {SANS}; fill: {t['ink']}; }}
    .ld {{ font: 400 12.5px {SANS}; fill: {t['graphite']}; }}
    .tile {{ fill: {t['paper2']}; stroke: {t['rule']}; }}
    .glyph {{ fill: none; stroke: {t['signal']}; stroke-width: 1.7; stroke-linecap: round; stroke-linejoin: round; }}
    .glyph .f {{ fill: {t['signal']}; stroke: none; }}
    .glyph .bg {{ fill: {t['paper2']}; }}
    .cl {{ font: 500 11.5px {MONO}; fill: {t['ink2']}; text-anchor: middle; }}
    .eh {{ font: 600 10.5px {MONO}; fill: {t['graphite']}; letter-spacing: .08em; }}
    .ev {{ font: 500 12.5px {MONO}; fill: {t['signal']}; }}
    .cap {{ font: 600 11px {MONO}; fill: {t['graphite']}; letter-spacing: .08em; }}
    .row {{ fill: transparent; }}
    .pkt {{ fill: {t['copper']}; animation: pkt 7s ease-in-out infinite; }}
    @keyframes pkt {{ 0% {{ transform: translateY(0); }} 45% {{ transform: translateY({(len(LAYERS)-1)*ROW}px); }}
                      55% {{ transform: translateY({(len(LAYERS)-1)*ROW}px); }} 100% {{ transform: translateY(0); }} }}
    @media (prefers-reduced-motion: reduce) {{ .pkt {{ animation: none; }} .flash {{ animation: none !important; opacity: 0 !important; }} }}
    """
    # Row highlight as the packet passes (down then up).
    for i in range(len(LAYERS)):
        down = i / (len(LAYERS) - 1) * 45
        up = 100 - down
        a, b = max(down - 4, 0), min(down + 4, 100)
        c, d = max(up - 4, 0), min(up + 4, 100)
        css += (f".fl{i} {{ animation: fl{i} 7s linear infinite; opacity: 0; }}"
                f"@keyframes fl{i} {{ 0% {{ opacity: {0.9 if i == 0 else 0}; }} {a:.1f}% {{ opacity: {0.9 if i == 0 else 0}; }} {down:.1f}% {{ opacity: .9; }} {b:.1f}% {{ opacity: 0; }}"
                f" {c:.1f}% {{ opacity: 0; }} {up:.1f}% {{ opacity: .9; }} {d:.1f}% {{ opacity: 0; }} 100% {{ opacity: {0.9 if i == 0 else 0}; }} }}")
    body = [f'<rect x=".5" y=".5" width="{W-1}" height="{H-1}" rx="12" fill="{t["paper"]}" stroke="{t["rule"]}"/>',
            f'<text class="cap" x="{LX}" y="34">FIG. 1 · WHERE I WORK IN THE STACK</text>',
            f'<text class="eh" x="{EX}" y="34">EVIDENCE (REPOS)</text>']
    y = TOP
    # bracket: the layers I focus on (below the framework)
    top_br, bot_br = TOP + ROW + 6, TOP + len(LAYERS) * ROW - 10
    body.append(f'<path d="M14 {top_br} h-4 v{bot_br-top_br} h4" fill="none" stroke="{t["copper"]}" stroke-width="2"/>')
    body.append(f'<text transform="translate(8 {(top_br+bot_br)/2}) rotate(-90)" text-anchor="middle" style="font:600 10.5px {MONO};fill:{t["copper"]};letter-spacing:.08em">PRIMARY FOCUS · L1–L4</text>')
    body.append(f'<line x1="{datapath_x}" y1="{TOP+20}" x2="{datapath_x}" y2="{TOP+(len(LAYERS)-1)*ROW+20}" stroke="{t["rule2"]}" stroke-width="1.5" stroke-dasharray="3 4"/>')
    for i, (num, name, desc, chips, ev) in enumerate(LAYERS):
        body.append(f'<rect class="flash fl{i}" x="{LX-8}" y="{y-6}" width="{W-2*LX+16}" height="{ROW-8}" rx="8" fill="{t["paper2"]}"/>')
        body.append(f'<line x1="{LX}" y1="{y+ROW-10}" x2="{W-LX}" y2="{y+ROW-10}" stroke="{t["rule"]}"/>')
        body.append(f'<text class="ln" x="{LX}" y="{y+16}">{num}</text>')
        body.append(f'<text class="lt" x="{LX}" y="{y+38}">{esc(name)}</text>')
        body.append(f'<text class="ld" x="{LX}" y="{y+58}">{esc(desc)}</text>')
        body.append(f'<circle cx="{datapath_x}" cy="{y+20}" r="3.2" fill="{t["paper"]}" stroke="{t["rule2"]}" stroke-width="1.5"/>')
        for j, (kind, label) in enumerate(chips):
            body.append(chip(t, theme, kind, label, CX0 + j * PITCH, y))
        for k, e in enumerate(ev):
            body.append(f'<text class="ev" x="{EX}" y="{y+22+k*20}">→ {esc(e)}</text>')
        y += ROW
    body.append(f'<circle class="pkt" cx="{datapath_x}" cy="{TOP+20}" r="5"/>')
    for name, chips in EXTRA:
        body.append(f'<line x1="{LX}" y1="{y+ROW-10}" x2="{W-LX}" y2="{y+ROW-10}" stroke="{t["rule"]}"/>' if name != EXTRA[-1][0] else "")
        body.append(f'<text class="ln" x="{LX}" y="{y+16}" style="fill:{t["graphite"]}">+</text>')
        body.append(f'<text class="lt" x="{LX}" y="{y+38}">{esc(name)}</text>')
        for j, (kind, label) in enumerate(chips):
            body.append(chip(t, theme, kind, label, CX0 + j * PITCH, y))
        y += ROW
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-labelledby="t d">
<title id="t">Where I work in the stack</title>
<desc id="d">Five layers from hardware to models. L5 models and serving: PyTorch, vLLM, Hugging Face, CUDA, Triton kernels, KV cache. L4 collectives and orchestration: NCCL, data/tensor/pipeline parallelism, checkpoint-restart, Ray, Slurm, Kubernetes. L3 transport and fabric: RDMA verbs, RoCE v2, InfiniBand, GPUDirect RDMA, PFC and ECN, rail-optimized fabrics. L2 host datapath: Linux networking, eBPF and XDP, DPDK, SR-IOV, KVM and virtio, perf and ftrace. L1 hardware: NVIDIA GPUs, NVLink, RDMA NICs, PCIe, GPU health. Also: Docker, Prometheus, Grafana, DCGM; languages C, C++, Python, Go, Bash.</desc>
<style>{css}</style>
{''.join(body)}
</svg>
"""


# ───────────────────────────── systems ─────────────────────────────

def window(name, a, b, cycle):
    """Keyframes that show an element from a% to b% of the cycle."""
    frames = f"0% {{ opacity: 0; }} {a}% {{ opacity: 1; }}" + (f" {b}% {{ opacity: 0; }}" if b < 100 else "")
    return f".{name} {{ opacity: 0; animation: {name} {cycle}s step-end infinite; }} @keyframes {name} {{ {frames} }}"


def systems(t):
    W, H = 880, 296
    cycle = 8   # goodput panel
    kv = 6      # kvwire panel
    css = [f"""
    .cap {{ font: 600 11px {MONO}; fill: {t['graphite']}; letter-spacing: .08em; }}
    .pn {{ font: 600 15px {SANS}; }}
    .ps {{ font: 500 11px {MONO}; fill: {t['graphite']}; }}
    .box {{ fill: {t['paper2']}; stroke: {t['rule2']}; stroke-width: 1.2; }}
    .bt {{ font: 500 10.5px {MONO}; fill: {t['ink2']}; text-anchor: middle; }}
    .dim {{ fill: none; stroke: {t['rule2']}; stroke-dasharray: 3 3; }}
    .dt {{ font: 500 10.5px {MONO}; fill: {t['graphite']}; }}
    .wire {{ fill: none; stroke: {t['rule2']}; stroke-width: 1.3; }}
    .foot {{ font: 500 11px {MONO}; fill: {t['graphite']}; }}
    .dot {{ fill: {t['signal']}; }}
    .kvb {{ fill: {t['copper']}; animation: kv {kv}s linear infinite; }}
    @keyframes kv {{ 0% {{ transform: translateX(0); opacity: 0; }} 8% {{ opacity: 1; }} 88% {{ opacity: 1; }}
                    100% {{ transform: translateX(124px); opacity: 0; }} }}
    .pf {{ fill: {t['signal']}; animation: pf 1.1s ease-in-out infinite alternate; }}
    @keyframes pf {{ from {{ fill-opacity: .25; }} to {{ fill-opacity: .9; }} }}
    .dc {{ fill: {t['copper']}; animation: dc 2.4s ease-in-out infinite alternate; }}
    @keyframes dc {{ from {{ fill-opacity: .2; }} to {{ fill-opacity: .7; }} }}
    .hb {{ fill: none; stroke: {t['graphite']}; stroke-width: 1.2; stroke-dasharray: 3 4; animation: hb 1.4s linear infinite; }}
    @keyframes hb {{ to {{ stroke-dashoffset: -14; }} }}
    """]
    # goodput: three evidence streams converge on the topology join (0–30%), the join names
    # the culprit (40%), then the cheapest safe recovery is chosen (55%).
    sig = [("NCCL flight rec.", 111), ("DCGM · Xid", 155), ("NIC · PFC ctrs", 199)]
    JY = 155
    dots = []
    for i, (_, y) in enumerate(sig):
        dy = JY - y
        css.append(f".d{i} {{ animation: d{i} {cycle}s linear infinite; }} @keyframes d{i} {{ "
                   f"0% {{ transform: translate(0px,0px); opacity: 1; }} 10% {{ transform: translate(16px,0px); }} "
                   f"20% {{ transform: translate(16px,{dy}px); }} 28% {{ transform: translate(32px,{dy}px); opacity: 1; }} "
                   f"30% {{ transform: translate(32px,{dy}px); opacity: 0; }} 100% {{ transform: translate(32px,{dy}px); opacity: 0; }} }}")
        dots.append(f'<circle class="dot d{i}" cx="158" cy="{y}" r="3.4"/>')
    css.append(window("jhi", 30, 100, cycle))
    css.append(window("cul", 40, 100, cycle))
    css.append(window("pick", 55, 100, cycle))
    css.append("""@media (prefers-reduced-motion: reduce) {
      .dot, .kvb, .pf, .dc, .hb, .jhi, .cul, .pick { animation: none !important; }
      .dot { opacity: 0; } .jhi, .cul, .pick { opacity: 1; } .kvb { transform: translateX(62px); } }""")

    left = [f'<text x="30" y="68"><tspan class="pn" fill="{t["signal"]}">goodput</tspan><tspan class="ps" dx="10">fault attribution &amp; recovery</tspan></text>']
    for name, y in sig:
        left.append(f'<rect class="box" x="30" y="{y-15}" width="128" height="30" rx="4"/><text class="bt" x="94" y="{y+4}">{esc(name)}</text>')
        left.append(f'<path class="wire" d="M158 {y} H174 V{JY} H190"/>')
    left.append(f'<rect class="box" x="190" y="{JY-25}" width="100" height="50" rx="4"/>'
                f'<rect class="jhi" x="190" y="{JY-25}" width="100" height="50" rx="4" fill="none" stroke="{t["signal"]}" stroke-width="2"/>'
                f'<text class="bt" x="240" y="{JY-3}">join on</text><text class="bt" x="240" y="{JY+12}">topology</text>')
    left.append(f'<path class="wire" d="M290 {JY} H304 V116 H318"/><path class="wire" d="M369 136 V150"/>')
    left.append(f'<rect class="dim" x="318" y="96" width="102" height="40" rx="4"/>'
                f'<g class="cul"><rect x="318" y="96" width="102" height="40" rx="4" fill="{t["paper"]}" stroke="{t["fault"]}" stroke-width="2"/>'
                f'<text class="bt" x="369" y="112" style="fill:{t["fault"]}">culprit</text><text class="bt" x="369" y="127">rank 5 · NIC 2</text></g>')
    for k, name in enumerate(["comm re-init", "swap node", "peer ckpt"]):
        y = 150 + k * 28
        left.append(f'<rect class="dim" x="318" y="{y}" width="102" height="22" rx="3"/><text class="dt" x="326" y="{y+15}">{k+1} {name}</text>')
    left.append(f'<g class="pick"><rect x="318" y="150" width="102" height="22" rx="3" fill="{t["signal"]}" fill-opacity=".14" stroke="{t["signal"]}" stroke-width="1.6"/>'
                f'<text x="326" y="165" style="font:600 10.5px {MONO};fill:{t["signal"]}">1 comm re-init</text></g>')
    left.append(f'<text class="foot" x="30" y="272">detect → attribute → smallest safe recovery</text>')
    left.extend(dots)

    # kvwire: prefill pool → KV blocks over GPUDirect RDMA → decode pool, with a coordinator.
    right = [f'<text x="470" y="68"><tspan class="pn" fill="{t["copper"]}">kvwire</tspan><tspan class="ps" dx="10">RDMA KV-cache transport</tspan></text>']
    for x0, title, sub, cls in [(470, "PREFILL", "compute-bound", "pf"), (730, "DECODE", "memory-bound", "dc")]:
        right.append(f'<rect class="box" x="{x0}" y="92" width="120" height="108" rx="6"/>'
                     f'<text class="bt" x="{x0+60}" y="108" style="font-weight:600;fill:{t["ink"]};letter-spacing:.08em">{title}</text>'
                     f'<text class="bt" x="{x0+60}" y="192" style="fill:{t["graphite"]}">{sub}</text>')
        for r in range(2):
            for c in range(2):
                gx, gy = x0 + 28 + c * 36, 116 + r * 32
                delay = f' style="animation-delay:-{(r * 2 + c) * 0.35:.2f}s"'
                right.append(f'<rect x="{gx}" y="{gy}" width="28" height="26" rx="2" fill="{t["paper"]}" stroke="{t["ink"]}" stroke-width="1.2"/>'
                             f'<rect class="{cls}" x="{gx+4}" y="{gy+4}" width="20" height="18" rx="1"{delay}/>')
    right.append(f'<line x1="590" y1="142" x2="730" y2="142" stroke="{t["ink"]}" stroke-width="1.3"/>'
                 f'<line x1="590" y1="152" x2="730" y2="152" stroke="{t["ink"]}" stroke-width="1.3"/>'
                 f'<text class="bt" x="660" y="132">GPUDirect RDMA</text>'
                 f'<text class="bt" x="660" y="172" style="fill:{t["graphite"]}">re-layout kernel</text>')
    for k in range(3):
        right.append(f'<rect class="kvb" x="594" y="143.5" width="12" height="7" rx="1" style="animation-delay:-{k * kv / 3:.1f}s"/>')
    right.append(f'<path class="hb" d="M630 218 L540 200"/><path class="hb" d="M690 218 L780 200"/>'
                 f'<rect class="box" x="600" y="218" width="120" height="28" rx="4"/><text class="bt" x="660" y="236">coordinator</text>')
    right.append(f'<text class="foot" x="470" y="272">safe when the network fails mid-transfer</text>')

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-labelledby="t d">
<title id="t">The two problems, as systems</title>
<desc id="d">Left, goodput: NCCL flight-recorder, DCGM/Xid and NIC/PFC counter evidence converge on a topology join that names the culprit rank and component, then the smallest safe recovery is chosen: communicator re-init before node swap before peer checkpoint restore. Right, kvwire: a compute-bound prefill pool sends KV-cache blocks over GPUDirect RDMA, through a re-layout kernel, to a memory-bound decode pool, supervised by a coordinator that stays correct if the network fails mid-transfer.</desc>
<style>{''.join(css)}</style>
<rect x=".5" y=".5" width="{W-1}" height="{H-1}" rx="12" fill="{t['paper']}" stroke="{t['rule']}"/>
<text class="cap" x="30" y="34">FIG. 2 · THE TWO PROBLEMS, AS SYSTEMS</text>
<line x1="445" y1="52" x2="445" y2="276" stroke="{t['rule']}"/>
{''.join(left)}
{''.join(right)}
</svg>
"""


# ───────────────────────────── pfc ─────────────────────────────

def pfc(t):
    W, H = 880, 280
    cycle = 12
    # Timeline (%): traffic flows 0–22, incast fills leaf B's egress queue 18–30, PAUSE goes
    # upstream one hop at a time (32, 42, 52), the unrelated flow is stalled (60), origin named (70).
    css = [f"""
    .cap {{ font: 600 11px {MONO}; fill: {t['graphite']}; letter-spacing: .08em; }}
    .sw {{ fill: {t['paper2']}; stroke: {t['ink']}; stroke-width: 1.3; }}
    .st {{ font: 600 11px {MONO}; fill: {t['ink']}; text-anchor: middle; letter-spacing: .06em; }}
    .hs {{ fill: {t['paper']}; stroke: {t['rule2']}; stroke-width: 1.2; }}
    .ht {{ font: 500 10.5px {MONO}; fill: {t['ink2']}; text-anchor: middle; }}
    .wire {{ fill: none; stroke: {t['rule2']}; stroke-width: 1.4; }}
    .pz {{ fill: none; stroke: {t['copper']}; stroke-width: 2.4; stroke-dasharray: 5 4; }}
    .pt {{ font: 600 10px {MONO}; fill: {t['copper']}; text-anchor: middle; letter-spacing: .06em; }}
    .note {{ font: 500 11px {MONO}; }}
    .dot {{ fill: {t['signal']}; }}
    .q {{ fill: {t['fault']}; transform-box: fill-box; transform-origin: center bottom; animation: q {cycle}s linear infinite; }}
    @keyframes q {{ 0% {{ transform: scaleY(0); }} 18% {{ transform: scaleY(0); }} 30% {{ transform: scaleY(1); }} 100% {{ transform: scaleY(1); }} }}
    """]
    for i in range(3):
        css.append(f".f{i} {{ animation: f {cycle}s linear infinite; animation-delay: -{i * 0.25:.2f}s; }}")
    css.append(f"@keyframes f {{ 0% {{ transform: translateX(0); opacity: 1; }} 22% {{ transform: translateX(80px); opacity: 1; }}"
               f" 23% {{ opacity: 0; }} 100% {{ opacity: 0; }} }}")
    for name, a in [("hot", 20), ("p1", 32), ("p2", 42), ("p3", 52), ("vic", 60), ("org", 70)]:
        css.append(window(name, a, 100, cycle))
    css.append("""@media (prefers-reduced-motion: reduce) {
      .q, .dot, .hot, .p1, .p2, .p3, .vic, .org { animation: none !important; }
      .dot { opacity: 0; } .hot, .p1, .p2, .p3, .vic, .org { opacity: 1; } .q { transform: none; } }""")

    LA, SP, LB = 190, 390, 590   # switch x positions, 100 wide
    MID = 145
    hosts = [("H0", 76), ("H1", 104), ("H2", 132), ("H3", 160), ("H4", 202)]
    body = [f'<rect x=".5" y=".5" width="{W-1}" height="{H-1}" rx="12" fill="{t["paper"]}" stroke="{t["rule"]}"/>',
            f'<text class="cap" x="30" y="34">FIG. 3 · PFC PAUSE PROPAGATION: VICTIM VS ORIGIN</text>']
    # links
    for _, y in hosts:
        body.append(f'<path class="wire" d="M110 {y} H{LA}"/>')
    body.append(f'<path class="wire" d="M{LA+100} {MID} H{SP}"/><path class="wire" d="M{SP+100} {MID} H{LB}"/>')
    body.append(f'<path class="wire" d="M{LB+100} 115 H770"/><path class="wire" d="M{LB+100} 185 H770"/>')
    # incast hot link and queue
    body.append(f'<path class="hot" d="M{LB+100} 115 H770" stroke="{t["fault"]}" stroke-width="2.6" fill="none"/>')
    # pause overlays, hop by hop upstream
    body.append(f'<g class="p1"><path class="pz" d="M{SP+100} {MID} H{LB}"/><text class="pt" x="{SP+150}" y="{MID-8}">◀ PAUSE</text></g>')
    body.append(f'<g class="p2"><path class="pz" d="M{LA+100} {MID} H{SP}"/><text class="pt" x="{LA+150}" y="{MID-8}">◀ PAUSE</text></g>')
    body.append('<g class="p3">' + "".join(f'<path class="pz" d="M110 {y} H{LA}"/>' for _, y in hosts) + '</g>')
    # nodes
    for name, y in hosts:
        body.append(f'<rect class="hs" x="30" y="{y-11}" width="80" height="22" rx="3"/><text class="ht" x="70" y="{y+4}">{name}</text>')
    for x, name in [(LA, "LEAF A"), (SP, "SPINE"), (LB, "LEAF B")]:
        body.append(f'<rect class="sw" x="{x}" y="88" width="100" height="114" rx="6"/><text class="st" x="{x+50}" y="{MID+4}">{name}</text>')
    body.append(f'<rect x="{LB+78}" y="98" width="14" height="30" fill="none" stroke="{t["rule2"]}"/>'
                f'<rect class="q" x="{LB+79}" y="99" width="12" height="28"/>')
    for name, y in [("R · incast", 115), ("R2", 185)]:
        body.append(f'<rect class="hs" x="770" y="{y-11}" width="80" height="22" rx="3"/><text class="ht" x="810" y="{y+4}">{name}</text>')
    for i, (x, y) in enumerate([(LA + 100, MID), (SP + 100, MID), (LB + 100, 115)]):
        body.append(f'<circle class="dot f{i}" cx="{x}" cy="{y}" r="3.4"/>')
    body.append(f'<text class="note" x="30" y="56" style="fill:{t["graphite"]}">H0–H3 → R (incast) · H4 → R2 (unrelated)</text>')
    body.append(f'<g class="vic"><rect x="28" y="189" width="84" height="26" rx="4" fill="none" stroke="{t["copper"]}" stroke-width="2"/>'
                f'<text class="note" x="30" y="240" style="fill:{t["copper"]}">victim · H4 → R2 stalls, though it never touches the hot port</text></g>')
    body.append(f'<g class="org"><rect x="{LB+74}" y="94" width="22" height="38" rx="3" fill="none" stroke="{t["fault"]}" stroke-width="2"/>'
                f'<text class="note" x="{LB+100}" y="72" text-anchor="middle" style="fill:{t["fault"]}">origin · leaf B egress → R</text>'
                f'<text class="note" x="30" y="262" style="fill:{t["signal"]}">nicprof traces pause counters hop by hop to the origin, not the loudest victim</text></g>')
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-labelledby="t d">
<title id="t">PFC pause propagation: victim vs origin</title>
<desc id="d">Four hosts send incast traffic through leaf A, a spine and leaf B to one receiver, while host H4 sends an unrelated flow to R2. Leaf B's egress queue toward the incast receiver fills, and PFC pause frames propagate upstream hop by hop: leaf B to spine, spine to leaf A, leaf A to every host. H4's flow stalls even though it never uses the congested port: it is a victim. The origin is the leaf B egress port; nicprof follows pause counters back to it.</desc>
<style>{''.join(css)}</style>
{''.join(body)}
</svg>
"""


def main():
    OUT.mkdir(exist_ok=True)
    for theme, t in THEMES.items():
        (OUT / f"banner-{theme}.svg").write_text(banner(t))
        (OUT / f"stack-{theme}.svg").write_text(stack(t, theme))
        (OUT / f"systems-{theme}.svg").write_text(systems(t))
        (OUT / f"pfc-{theme}.svg").write_text(pfc(t))
    print("wrote", sorted(p.name for p in OUT.glob("*.svg")))


if __name__ == "__main__":
    main()
