import json
import random
import math

with open('/home/claude/dots.json') as f:
    DOTS_DATA = json.load(f)
with open('/home/claude/config.json') as f:
    CFG = json.load(f)

GRID_W, GRID_H = DOTS_DATA['grid_w'], DOTS_DATA['grid_h']
DOTS = DOTS_DATA['dots']

CANVAS_W, CANVAS_H = CFG['canvas']['w'], CFG['canvas']['h']
COLORS = CFG['colors']
TITLEBAR_H = 40
PAD = 22
LEFT_W = int(CANVAS_W * 0.38)
RIGHT_X = LEFT_W + 14

N_GROUPS = 16
random.seed(7)


def build_portrait_layer(mode='dark'):
    # portrait viewport inside left column
    vp_x0, vp_y0 = PAD, TITLEBAR_H + 46
    vp_x1, vp_y1 = LEFT_W - PAD, CANVAS_H - 30
    vp_w, vp_h = vp_x1 - vp_x0, vp_y1 - vp_y0
    scale = min(vp_w / GRID_W, vp_h / GRID_H)
    off_x = vp_x0 + (vp_w - GRID_W * scale) / 2
    off_y = vp_y0 + (vp_h - GRID_H * scale) / 2
    r = max(0.55, scale * 0.42)

    shuffled = DOTS[:]
    random.shuffle(shuffled)
    groups = [[] for _ in range(N_GROUPS)]
    for i, (gx, gy) in enumerate(shuffled):
        groups[i % N_GROUPS].append((off_x + gx * scale, off_y + gy * scale))

    dot_color = COLORS['portrait_dot'] if mode == 'dark' else '#1E5F78'
    parts = [f'<g id="portrait" clip-path="url(#portraitClip)">']
    parts.append(f'<rect x="{vp_x0}" y="{vp_y0}" width="{vp_w}" height="{vp_h}" fill="transparent"/>')
    for gi, pts in enumerate(groups):
        drift_variant = ['driftA', 'driftB', 'driftC'][gi % 3]
        path_cmds = []
        for (x, y) in pts:
            path_cmds.append(f'M{x - r:.2f} {y:.2f}a{r:.2f} {r:.2f} 0 1 0 {2*r:.2f} 0a{r:.2f} {r:.2f} 0 1 0 -{2*r:.2f} 0')
        d = ''.join(path_cmds)
        # outer <g> carries the slow organic drift (transform); inner <path>
        # carries the intro fade-in + idle opacity breathing. Kept on two
        # elements so the two animations never collide in one shorthand.
        parts.append(f'<g class="{drift_variant}"><path class="dotgrp dg{gi}" d="{d}" fill="{dot_color}"/></g>')
    parts.append('</g>')
    return ''.join(parts), (vp_x0, vp_y0, vp_w, vp_h)


def build_style():
    css = [':root{}']
    css.append('.dotgrp{opacity:0;transform-box:fill-box;transform-origin:center;}')
    # intro: staggered fade-in per group, then hand off to idle breathing
    intro_dur = 0.85
    stagger = 0.11
    for gi in range(N_GROUPS):
        delay = gi * stagger
        idle_delay = delay + intro_dur
        breathe_dur = 4.2 + (gi % 5) * 0.5
        css.append(
            f'.dg{gi}{{animation: dotIntro {intro_dur}s ease-out {delay:.2f}s both, '
            f'breathe {breathe_dur:.1f}s ease-in-out {idle_delay:.2f}s infinite;}}'
        )
    css.append('@keyframes dotIntro{0%{opacity:0;}100%{opacity:1;}}')
    css.append('@keyframes breathe{0%,100%{opacity:0.82;}50%{opacity:1;}}')
    css.append('@keyframes driftA{0%,100%{transform:translate(0,0);}50%{transform:translate(0.5px,-0.4px);}}')
    css.append('@keyframes driftB{0%,100%{transform:translate(0,0);}50%{transform:translate(-0.4px,0.5px);}}')
    css.append('@keyframes driftC{0%,100%{transform:translate(0,0);}50%{transform:translate(0.3px,0.3px);}}')
    css.append('.driftA{transform-box:fill-box;transform-origin:center;animation:driftA 7.5s ease-in-out 2.6s infinite;}')
    css.append('.driftB{transform-box:fill-box;transform-origin:center;animation:driftB 8.2s ease-in-out 2.6s infinite;}')
    css.append('.driftC{transform-box:fill-box;transform-origin:center;animation:driftC 6.8s ease-in-out 2.6s infinite;}')
    css.append('.live-dot{animation:livePulse 1.6s ease-in-out infinite;}')
    css.append('@keyframes livePulse{0%,100%{opacity:1;}50%{opacity:0.25;}}')
    css.append('text{font-family: ui-monospace, SFMono-Regular, "JetBrains Mono", Menlo, Consolas, monospace;}')
    return ''.join(css)


def dotted_leader(x_start, x_end, y, font_size, color):
    char_w = font_size * 0.6
    gap = x_end - x_start
    n = max(1, int(gap / char_w))
    run = '.' * n
    return (f'<text x="{x_start:.1f}" y="{y:.1f}" font-size="{font_size}" fill="{color}" '
            f'textLength="{gap:.1f}" lengthAdjust="spacingAndGlyphs">{run}</text>')


def build_info_panel(mode='dark'):
    text_main = COLORS['text_main'] if mode == 'dark' else '#0B1A24'
    text_dim = COLORS['text_dim'] if mode == 'dark' else '#5E7482'
    label_color = COLORS['chrome'] if mode == 'dark' else '#0E7C92'
    value_color = text_main
    parts = []
    header_y = TITLEBAR_H + 40
    parts.append(f'<text x="{RIGHT_X}" y="{header_y}" font-size="15" font-weight="600" '
                 f'letter-spacing="2" fill="{label_color}">SYSTEM.INFO</text>')
    parts.append(f'<line x1="{RIGHT_X}" y1="{header_y+12}" x2="{CANVAS_W-PAD}" y2="{header_y+12}" '
                 f'stroke="{label_color}" stroke-opacity="0.25"/>')

    row_h = 30
    y0 = header_y + 40
    label_x = RIGHT_X
    value_right = CANVAS_W - PAD
    font_size = 13

    for i, row in enumerate(CFG['rows']):
        y = y0 + i * row_h
        label = row['label']
        value = row['value']
        parts.append(f'<text x="{label_x}" y="{y}" font-size="{font_size}" fill="{text_dim}">{label}</text>')
        label_w = len(label) * font_size * 0.6
        value_w = len(value) * font_size * 0.6
        leader_start = label_x + label_w + 8
        leader_end = value_right - value_w - 8
        if leader_end > leader_start:
            parts.append(dotted_leader(leader_start, leader_end, y, font_size, text_dim))
        vc = COLORS['accent'] if row['label'] == 'Grid.GitHub' else value_color
        parts.append(f'<text x="{value_right}" y="{y}" font-size="{font_size}" fill="{vc}" '
                     f'text-anchor="end">{value}</text>')
    return ''.join(parts), y0 + len(CFG['rows']) * row_h


def build_chrome(mode='dark'):
    bg = COLORS['bg'] if mode == 'dark' else '#F4F8FB'
    chrome = COLORS['chrome'] if mode == 'dark' else '#0E7C92'
    parts = []
    parts.append(f'<rect x="0" y="0" width="{CANVAS_W}" height="{CANVAS_H}" rx="14" fill="{bg}"/>')
    # title bar
    parts.append(f'<rect x="0" y="0" width="{CANVAS_W}" height="{TITLEBAR_H}" rx="14" fill="{bg}"/>')
    parts.append(f'<rect x="0" y="{TITLEBAR_H-14}" width="{CANVAS_W}" height="14" fill="{bg}"/>')
    for i, c in enumerate(['#FF5F56', '#FFBD2E', '#27C93F']):
        parts.append(f'<circle cx="{28 + i*20}" cy="{TITLEBAR_H/2}" r="6" fill="{c}" opacity="0.85"/>')
    parts.append(f'<text x="{CANVAS_W/2}" y="{TITLEBAR_H/2+5}" font-size="13" fill="{chrome}" '
                 f'text-anchor="middle" opacity="0.9">{CFG["terminal_title"]}</text>')
    # live badge (top right of title bar)
    lx, ly = CANVAS_W - 90, TITLEBAR_H/2
    parts.append(f'<circle class="live-dot" cx="{lx}" cy="{ly}" r="5" fill="{COLORS["accent"]}"/>')
    parts.append(f'<text x="{lx+12}" y="{ly+4}" font-size="11" letter-spacing="1.5" '
                 f'fill="{COLORS["accent"]}">LIVE</text>')
    # divider between columns
    parts.append(f'<line x1="{LEFT_W}" y1="{TITLEBAR_H+10}" x2="{LEFT_W}" y2="{CANVAS_H-14}" '
                 f'stroke="{chrome}" stroke-opacity="0.18"/>')
    # VISUAL.MAP label
    parts.append(f'<text x="{PAD}" y="{TITLEBAR_H+30}" font-size="13" font-weight="600" '
                 f'letter-spacing="2" fill="{chrome}">VISUAL.MAP</text>')
    return ''.join(parts)


def build_handle_pill(mode='dark'):
    handle = '@koyya-suchitra'
    w = len(handle) * 7.4 + 24
    x = PAD
    y = CANVAS_H - 26
    fill = COLORS['violet']
    parts = [f'<rect x="{x}" y="{y-16}" width="{w}" height="24" rx="12" fill="{fill}" fill-opacity="0.16" '
             f'stroke="{fill}" stroke-opacity="0.55"/>']
    parts.append(f'<text x="{x + w/2}" y="{y}" font-size="12" text-anchor="middle" fill="{fill}">{handle}</text>')
    return ''.join(parts)


def build_svg(mode='dark'):
    portrait_svg, (vx, vy, vw, vh) = build_portrait_layer(mode)
    info_svg, _ = build_info_panel(mode)
    chrome_svg = build_chrome(mode)
    pill_svg = build_handle_pill(mode)
    style = build_style()

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {CANVAS_W} {CANVAS_H}" width="{CANVAS_W}" height="{CANVAS_H}">
<defs>
<clipPath id="portraitClip"><rect x="{vx}" y="{vy}" width="{vw}" height="{vh}"/></clipPath>
<style>{style}</style>
</defs>
{chrome_svg}
{portrait_svg}
{info_svg}
{pill_svg}
</svg>'''
    return svg


if __name__ == '__main__':
    dark = build_svg('dark')
    with open('/home/claude/dark.svg', 'w') as f:
        f.write(dark)
    print('dark.svg bytes:', len(dark.encode()))
