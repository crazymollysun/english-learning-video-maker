#!/usr/bin/env python3
"""
英语学习视频 v4 - 仿"Luna每日英语精读"风格
布局：上方视频区（约55%高度） + 下方字幕学习区（约45%高度）
字幕区：深色背景，当前句紫色高亮卡片，关键词黄色标注
"""

import re
import sys
import importlib.util
sys.path.insert(0, '.')
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import numpy as np
from moviepy import VideoFileClip, ImageClip, CompositeVideoClip, concatenate_videoclips
from moviepy.video.fx import FadeOut

import argparse as _argparse
_ap = _argparse.ArgumentParser(add_help=False)
_ap.add_argument('--input', default="lara_clip.mp4")
_ap.add_argument('--output', default="Lara_英语学习版_v13.mp4")
_ap.add_argument('--srt', default=None)
_ap.add_argument('--transcript', default=None)
_ap.add_argument('--title', default=None)
_ap.add_argument('--tag', default=None)   # 片头顶部标签文字，如 "TED精讲 · Reshma Saujani"
_ap.add_argument('--keywords', default=None)
_args, _ = _ap.parse_known_args()

INPUT    = _args.input
OUTPUT   = _args.output
SRT_FILE = _args.srt if _args.srt else INPUT.replace('.mp4', '_bilingual.srt')
_TRANSCRIPT_OVERRIDE = _args.transcript
_TITLE_OVERRIDE      = _args.title
_TAG_OVERRIDE        = _args.tag
_KEYWORDS_FILE       = _args.keywords

# 动态加载关键词
import os as _os
def _load_keywords():
    # 优先用命令行指定的关键词文件
    kw_path = _KEYWORDS_FILE
    if not kw_path:
        # 自动推断：clip_xxx_keywords.py
        kw_path = INPUT.replace('.mp4', '_keywords.py')
    if kw_path and _os.path.exists(kw_path):
        spec = importlib.util.spec_from_file_location("_kw_module", kw_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return getattr(mod, 'KEYWORDS', {})
    # fallback: 空关键词
    return {}

KEYWORDS = _load_keywords()

# 最终画布尺寸（竖屏）
W, H = 1080, 1920

# 布局：标题区（上） + 视频区（中） + 字幕区（下）
TITLE_H = 280    # 顶部标题区（加大给大字号）
VIDEO_H = 700    # 视频区
SUB_H   = 940    # 字幕区（TITLE_H+VIDEO_H+SUB_H = 1920）

# 配色
BG_VIDEO    = (15, 15, 20)       # 视频背景（黑）
BG_SUB      = (18, 18, 28)       # 字幕区背景（深蓝黑）
COLOR_HIGHLIGHT_BG  = (88, 50, 180)   # 当前句卡片背景（紫色）
COLOR_HIGHLIGHT_EN  = (255, 255, 255) # 当前句英文（白）
COLOR_HIGHLIGHT_ZH  = (220, 200, 255) # 当前句中文（浅紫白）
COLOR_KEYWORD_EN    = (255, 230, 80)  # 英文关键词（黄色）
COLOR_KEYWORD_ZH    = (255, 220, 60)  # 中文关键词注释（黄色）
COLOR_KEYWORD_PILL  = (60, 35, 120)   # 关键词背景pill（深紫）
COLOR_OTHER_EN      = (160, 160, 185) # 其他句英文（灰）
COLOR_OTHER_ZH      = (110, 110, 140) # 其他句中文（暗灰）
COLOR_COUNTER       = (120, 100, 200) # 序号（紫）
COLOR_DIVIDER       = (40, 40, 65)    # 分割线
COLOR_TAG           = (88, 50, 180)   # 标签背景

# ── 字体 ──────────────────────────────────────────────────────────────────────
def load_font(size, bold=False):
    candidates = [
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Medium.ttc",
        "/System/Library/Fonts/STHeiti Light.ttc",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for p in candidates:
        if Path(p).exists():
            try:
                idx = 1 if bold and "PingFang" in p else 0
                return ImageFont.truetype(p, size, index=idx)
            except:
                pass
    return ImageFont.load_default()

F_TITLE_BIG  = load_font(62, bold=True)
F_TITLE_MED  = load_font(44, bold=True)
F_STEP_ICON  = load_font(32)
F_STEP_TEXT  = load_font(28)
F_TAG        = load_font(24)
F_EN_CUR     = load_font(42, bold=True)   # 当前句英文
F_ZH_CUR     = load_font(50, bold=True)   # 当前句中文（加大）
F_EN_OTHER   = load_font(34)              # 其他句英文
F_ZH_OTHER   = load_font(40, bold=True)   # 其他句中文（加大加粗）
F_COUNTER    = load_font(24)
F_TIMESTAMP  = load_font(24)

# ── SRT 解析 ──────────────────────────────────────────────────────────────────
def parse_srt(path):
    with open(path, encoding="utf-8") as f:
        content = f.read()
    subs = []
    for block in re.split(r"\n\n+", content.strip()):
        lines = block.strip().splitlines()
        if len(lines) < 3:
            continue
        m = re.match(r"(\d+:\d+:\d+,\d+) --> (\d+:\d+:\d+,\d+)", lines[1])
        if not m:
            continue
        def ts(s):
            s = s.replace(",", ".")
            h, mn, sc = s.split(":")
            return int(h)*3600 + int(mn)*60 + float(sc)
        idx = int(lines[0].strip()) - 1  # 转为0-based，与KEYWORDS对齐
        subs.append({
            "idx": idx,
            "start": ts(m.group(1)),
            "end": ts(m.group(2)),
            "en": lines[2] if len(lines) > 2 else "",
            "zh": lines[3] if len(lines) > 3 else "",
        })
    return subs

# ── 绘图工具 ──────────────────────────────────────────────────────────────────
def tw(draw, text, font):
    bb = draw.textbbox((0,0), text, font=font)
    return bb[2] - bb[0]

def th(draw, text, font):
    bb = draw.textbbox((0,0), text, font=font)
    return bb[3] - bb[1]

def wrap_text(draw, text, font, max_width):
    """把文字按 max_width 自动换行，返回行列表。
    自动检测中文（CJK）文本，按字符逐个分割；英文按空格分词。
    """
    import unicodedata
    def is_cjk(s):
        for ch in s:
            cat = unicodedata.category(ch)
            cp = ord(ch)
            if 0x4E00 <= cp <= 0x9FFF or 0x3400 <= cp <= 0x4DBF or \
               0xF900 <= cp <= 0xFAFF or 0x3000 <= cp <= 0x303F:
                return True
        return False

    lines = []
    if is_cjk(text):
        # 中文：逐字符贪心换行
        cur = ""
        for ch in text:
            test = cur + ch
            if tw(draw, test, font) <= max_width:
                cur = test
            else:
                if cur:
                    lines.append(cur)
                cur = ch
        if cur:
            lines.append(cur)
    else:
        # 英文：按空格分词
        words = text.split()
        cur = ""
        for w in words:
            test = (cur + " " + w).strip()
            if tw(draw, test, font) <= max_width:
                cur = test
            else:
                if cur:
                    lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)
    return lines

def draw_wrapped(draw, x, y, text, font, fill, max_width, line_gap=6):
    """自动换行绘制，返回总高度"""
    lines = wrap_text(draw, text, font, max_width)
    lh = th(draw, "Ag", font) + line_gap
    for i, line in enumerate(lines):
        draw.text((x, y + i * lh), line, font=font, fill=fill)
    return lh * len(lines)

def measure_wrapped_height(draw, text, font, max_width, line_gap=6):
    lines = wrap_text(draw, text, font, max_width)
    lh = th(draw, "Ag", font) + line_gap
    return lh * len(lines)

def draw_highlighted_en(draw, x, y, text, font, keywords, max_width, line_gap=6):
    """
    逐词绘制英文，关键词用黄色，其余白色，自动换行。
    keywords: [(en_kw, zh_note), ...]
    返回总高度。
    """
    # 把关键词列表转成小写集合方便匹配
    kw_map = {kw.lower(): note for kw, note in keywords}

    words = text.split()
    lh = th(draw, "Ag", font) + line_gap
    cx, cy = x, y

    # 先按行分词（尊重max_width换行）
    lines_words = []
    cur_line = []
    cur_w = 0
    for word in words:
        word_w = tw(draw, word + " ", font)
        if cur_w + word_w > max_width and cur_line:
            lines_words.append(cur_line)
            cur_line = [word]
            cur_w = word_w
        else:
            cur_line.append(word)
            cur_w += word_w
    if cur_line:
        lines_words.append(cur_line)

    import re as _re
    def _strip_punct(w):
        """去掉词尾标点用于匹配，保留原词用于绘制"""
        return _re.sub(r"[,\.!?;:\"']+$", "", w)

    total_h = 0
    for line_words in lines_words:
        wx = x
        # 尝试多词短语匹配（最多4词），匹配时去掉标点
        i = 0
        while i < len(line_words):
            matched = False
            for span in [4, 3, 2, 1]:
                if i + span > len(line_words):
                    continue
                # 用去标点的词拼短语来匹配
                clean_phrase = " ".join(_strip_punct(w) for w in line_words[i:i+span])
                raw_phrase = " ".join(line_words[i:i+span])
                if clean_phrase.lower() in kw_map:
                    # 关键词：黄色（绘制原始词含标点）
                    pw = tw(draw, raw_phrase, font)
                    draw.text((wx, cy), raw_phrase, font=font, fill=COLOR_KEYWORD_EN)
                    wx += pw + tw(draw, " ", font)
                    i += span
                    matched = True
                    break
            if not matched:
                # 普通词：白色
                w = line_words[i]
                pw = tw(draw, w, font)
                draw.text((wx, cy), w, font=font, fill=COLOR_HIGHLIGHT_EN)
                wx += pw + tw(draw, " ", font)
                i += 1
        cy += lh
        total_h += lh

    return total_h

def draw_highlighted_zh(draw, x, y, text, font, keywords, line_gap=12):
    """
    绘制中文翻译 + 关键词标注（每个关键词单独一行，黄色字体比正文大一号）。
    返回总高度。
    """
    # 中文原文（浅紫，自动换行）
    base_h = draw_wrapped(draw, x, y, text, font, COLOR_HIGHLIGHT_ZH,
                          max_width=W - x - 52, line_gap=line_gap)

    if not keywords:
        return base_h

    # 关键词用比正文大6px的字体
    F_KW = load_font(46, bold=True)
    KW_LINE_GAP = 18  # 关键词行间距（更大）

    note_y = y + base_h + 14   # 中文与第一条关键词之间的间距加大
    total_extra = 14
    max_pill_w = W - x - 52  # pill最大宽度，防止超出画布
    for en_kw, zh_note in keywords:
        note_str = f"{en_kw}  ->  {zh_note}"
        # 如果文本太长，截断后加省略号
        while tw(draw, note_str, F_KW) > max_pill_w and len(note_str) > 10:
            note_str = note_str[:-1]
        if note_str != f"{en_kw}  ->  {zh_note}":
            note_str = note_str[:-1] + "…"
        lh = th(draw, note_str, F_KW) + KW_LINE_GAP
        nw = min(tw(draw, note_str, F_KW), max_pill_w)
        # pill 背景
        draw_rounded_rect(draw, x-8, note_y-6,
                          x+nw+8, note_y+lh-2, 10, COLOR_KEYWORD_PILL)
        draw.text((x, note_y), note_str, font=F_KW, fill=COLOR_KEYWORD_ZH)
        note_y += lh + 14    # 每条关键词之间间距也加大
        total_extra += lh + 14

    return base_h + total_extra

def draw_text_shadow(draw, x, y, text, font, fill, shadow=(0,0,0), sw=2):
    draw.text((x+sw, y+sw), text, font=font, fill=shadow)
    draw.text((x, y), text, font=font, fill=fill)

def draw_rounded_rect(draw, x1, y1, x2, y2, r, fill):
    draw.rounded_rectangle([x1, y1, x2, y2], radius=r, fill=fill)

def format_time(t):
    m = int(t // 60)
    s = int(t % 60)
    return f"{m:02d}:{s:02d}"

# ── 片头画面（5秒静止）─────────────────────────────────────────────────────
def make_intro_frame():
    img = Image.new("RGB", (W, H), (12, 10, 22))
    draw = ImageDraw.Draw(img)

    # 渐变感（多层横条）
    for i in range(H):
        alpha = int(30 * (1 - abs(i - H*0.4) / (H*0.6)))
        c = max(0, min(alpha, 30))
        draw.line([(0,i),(W,i)], fill=(60, 20, 120, c))

    # 顶部标签
    tag_text = _TAG_OVERRIDE if _TAG_OVERRIDE else "🧠  TED精讲  ·  Lara Boyd × TEDxVancouver"
    tag_w = tw(draw, tag_text, F_TAG) + 40
    tag_x = (W - tag_w) // 2
    draw_rounded_rect(draw, tag_x, 220, tag_x+tag_w, 265, 12, (60, 30, 140))
    draw.text((tag_x+20, 228), tag_text, font=F_TAG, fill=(200, 170, 255))

    # 主标题
    t1 = "这才是你在真实英语"
    t2 = "环境里会听到的英语"
    x1 = (W - tw(draw, t1, F_TITLE_BIG)) // 2
    x2 = (W - tw(draw, t2, F_TITLE_BIG)) // 2
    draw_text_shadow(draw, x1, 300, t1, F_TITLE_BIG, fill=(255,255,255), sw=3)
    draw_text_shadow(draw, x2, 385, t2, F_TITLE_BIG, fill=(255,255,255), sw=3)

    # 副标题
    sub = "Lara Boyd · TEDxVancouver · 大脑科学英语精讲"
    sx = (W - tw(draw, sub, F_STEP_TEXT)) // 2
    draw.text((sx, 480), sub, font=F_STEP_TEXT, fill=(140, 120, 200))

    # 分隔线
    draw.rectangle([80, 530, W-80, 532], fill=(60, 40, 120))

    # 学习步骤卡片
    steps = [
        ("①", "盲听",  "不看字幕先感受语速和语调"),
        ("②", "精读",  "借助翻译，留意地道用词"),
        ("③", "精听",  "关注连读、弱读、语气变化"),
        ("④", "跟读",  "跟着说，录下来对比原版"),
    ]
    card_y = 570
    for num, title, desc in steps:
        # 卡片背景
        draw_rounded_rect(draw, 60, card_y, W-60, card_y+88, 16, (28, 22, 55))
        # 序号圆
        draw_rounded_rect(draw, 80, card_y+20, 122, card_y+62, 20, (88, 50, 180))
        draw.text((88, card_y+26), num, font=F_STEP_ICON, fill=(255,255,255))
        # 标题
        draw.text((140, card_y+16), title, font=F_TITLE_MED, fill=(200, 170, 255))
        # 描述
        draw.text((140, card_y+56), desc, font=F_STEP_TEXT, fill=(130, 115, 170))
        card_y += 100

    # 底部提示
    tip = "📌 建议配合耳机，感受真实语速"
    tx = (W - tw(draw, tip, F_TAG)) // 2
    draw.text((tx, H-160), tip, font=F_TAG, fill=(100, 85, 160))

    # 底部紫色装饰条
    draw.rectangle([0, H-80, W, H], fill=(30, 20, 65))
    brand = "真实英语 · 原声训练"
    bx = (W - tw(draw, brand, F_TAG)) // 2
    draw.text((bx, H-55), brand, font=F_TAG, fill=(140, 110, 220))

    return np.array(img)

SCROLL_DUR = 0.30   # 滚动动画时长（秒）

def ease_out(x):
    """缓动函数：快进慢出"""
    return 1 - (1 - x) ** 3

def find_cur_idx(subs, t):
    """找当前/最近的字幕索引（间隔时段返回上一句）"""
    last = None
    for i, s in enumerate(subs):
        if s["start"] <= t:
            last = i
        if s["start"] > t:
            break
    return last

# ── 主体帧：视频区 + 字幕区 ───────────────────────────────────────────────
def make_main_frame(video_frame, subs, t):
    canvas = Image.new("RGB", (W, H), BG_VIDEO)
    draw_title = ImageDraw.Draw(canvas)

    # —— 顶部：标题区 ——
    # 背景渐变深紫
    for i in range(TITLE_H):
        alpha = i / TITLE_H
        c = tuple(int(BG_VIDEO[j] * (1-alpha) + (30,18,60)[j] * alpha) for j in range(3))
        draw_title.line([(0, i), (W, i)], fill=c)
    # 标题文字 — STHeiti 黑体，斜体用仿斜（shear变换）
    HEITI = "/System/Library/Fonts/STHeiti Medium.ttc"
    FONT_SIZE = 72
    try:
        F_TITLE_BIG = ImageFont.truetype(HEITI, FONT_SIZE)
    except Exception:
        F_TITLE_BIG = load_font(FONT_SIZE, bold=True)

    title_main = _TITLE_OVERRIDE if _TITLE_OVERRIDE else "大脑可塑性：你所不知道的秘密"

    # 渲染到临时图层，再做shear斜体变换
    tmp = Image.new("RGBA", (W, TITLE_H), (0, 0, 0, 0))
    tmp_draw = ImageDraw.Draw(tmp)
    tw_main = tw(tmp_draw, title_main, F_TITLE_BIG)
    title_h = th(tmp_draw, title_main, F_TITLE_BIG)
    # 贴近紫色线上方，留10px间距
    title_y = TITLE_H - title_h - 14
    tx = (W - tw_main) // 2
    tmp_draw.text((tx, title_y), title_main, font=F_TITLE_BIG, fill=(255, 255, 255, 255))
    # shear变换模拟斜体（向右倾斜0.2）
    import PIL.Image as PILImage
    shear = 0.2
    tmp_sheared = tmp.transform(
        (W, TITLE_H), PILImage.AFFINE,
        (1, shear, -shear * TITLE_H * 0.5, 0, 1, 0),
        resample=PILImage.BILINEAR
    )
    canvas.paste(tmp_sheared, (0, 0), tmp_sheared)
    # 装饰线
    draw_title.rectangle([40, TITLE_H-4, W-40, TITLE_H-1], fill=(120, 80, 220))

    # —— 中间：视频区（从TITLE_H开始） ——
    vf = Image.fromarray(video_frame)
    vw, vh = vf.size
    scale = min(W / vw, VIDEO_H / vh)
    nw, nh = int(vw*scale), int(vh*scale)
    vf = vf.resize((nw, nh), Image.LANCZOS)
    vx = (W - nw) // 2
    vy = TITLE_H + (VIDEO_H - nh)   # 视频在视频区内底部对齐
    canvas.paste(vf, (vx, vy))

    # 视频区底部渐变遮罩
    for i in range(60):
        y = TITLE_H + VIDEO_H - 60 + i
        draw_temp = ImageDraw.Draw(canvas)
        draw_temp.line([(0, y), (W, y)],
                       fill=tuple(int(c * (1 - i/60) + BG_SUB[j] * (i/60))
                                  for j, c in enumerate((0,0,0))))

    # —— 下方：字幕区（从TITLE_H+VIDEO_H开始） ——
    LINE_GAP = 24
    card_pad = 22

    # 找当前句（间隔时段也返回最近一句，不显示loading）
    cur_idx = find_cur_idx(subs, t)

    def calc_card_h(idx, draw_ref):
        """计算某句的卡片高度（用 dummy draw 精确测量，避免估算偏差）"""
        s = subs[idx]
        kws = KEYWORDS.get(s["idx"], [])
        en_h = measure_wrapped_height(draw_ref, s["en"], F_EN_CUR, W-100, line_gap=LINE_GAP) + 4
        # 用 dummy draw 精确测量 draw_highlighted_zh 实际高度
        dummy_img = Image.new("RGB", (W, 2000), (0, 0, 0))
        dummy_draw = ImageDraw.Draw(dummy_img)
        zh_real_h = draw_highlighted_zh(dummy_draw, 52, 0, s["zh"], F_ZH_CUR, kws)
        return card_pad*2 + en_h + zh_real_h + 18 + 16

    def calc_prev_block_h(idx, draw_ref):
        """计算前一句灰色区域高度（考虑换行）"""
        if idx <= 0:
            return 0
        s = subs[idx - 1]
        en_h = measure_wrapped_height(draw_ref, s["en"], F_EN_OTHER, W-60, line_gap=8)
        zh_h = measure_wrapped_height(draw_ref, s["zh"], F_ZH_OTHER, W-60, line_gap=8)
        return en_h + 12 + zh_h + 28

    def draw_sub_frame(draw, offset_y, cur_idx):
        """把完整字幕区渲染到 draw，y轴整体偏移 offset_y（用于滚动）"""
        if cur_idx is None:
            return

        cur = subs[cur_idx]
        cur_kws = KEYWORDS.get(cur["idx"], [])
        card_h = calc_card_h(cur_idx, draw)
        prev_block_h = calc_prev_block_h(cur_idx, draw)

        y = 36 + offset_y

        # 前一句（灰色，上方）
        if cur_idx > 0:
            prev = subs[cur_idx - 1]
            prev_en_h = draw_wrapped(draw, 30, y, prev["en"], F_EN_OTHER, COLOR_OTHER_EN, max_width=W-60, line_gap=8)
            y += prev_en_h + 12
            prev_zh_h = draw_wrapped(draw, 30, y, prev["zh"], F_ZH_OTHER, COLOR_OTHER_ZH, max_width=W-60, line_gap=8)
            y += prev_zh_h + 28

        # 时间戳 + 序号
        ts_str = f"{format_time(cur['start'])} – {format_time(cur['end'])}"
        draw.text((30, y), ts_str, font=F_TIMESTAMP, fill=(100, 85, 145))
        num_str = f"{cur['idx']:02d} / {len(subs):02d}"
        draw.text((W - tw(draw, num_str, F_TIMESTAMP) - 30, y),
                  num_str, font=F_TIMESTAMP, fill=(100, 85, 145))
        y += th(draw, "Ag", F_TIMESTAMP) + 14

        # 当前句紫色卡片
        draw_rounded_rect(draw, 20, y, W-20, y+card_h, 20, COLOR_HIGHLIGHT_BG)
        draw.rectangle([20, y, 30, y+card_h], fill=(160, 100, 255))
        ey = y + card_pad
        en_real_h = draw_highlighted_en(draw, 52, ey, cur["en"], F_EN_CUR,
                                        cur_kws, max_width=W-104, line_gap=LINE_GAP)
        zy = ey + en_real_h + 18
        draw_highlighted_zh(draw, 52, zy, cur["zh"], F_ZH_CUR, cur_kws)
        y += card_h + 26

        # 后一句（灰色，下方）
        if cur_idx < len(subs) - 1 and y + 60 < SUB_H + abs(offset_y) + 300:
            draw.rectangle([30, y, W-30, y+1], fill=COLOR_DIVIDER)
            y += 18
            nxt = subs[cur_idx + 1]
            nxt_en_h = draw_wrapped(draw, 30, y, nxt["en"], F_EN_OTHER, COLOR_OTHER_EN, max_width=W-60, line_gap=8)
            y += nxt_en_h + 12
            draw_wrapped(draw, 30, y, nxt["zh"], F_ZH_OTHER, COLOR_OTHER_ZH, max_width=W-60, line_gap=8)

    # ── 计算滚动动效 ──
    # 原理：句子开始时，渲染"上一句状态"和"当前句状态"两帧，按进度插值y偏移
    # 上一句状态 = cur_idx-1 为紫色；当前句状态 = cur_idx 为紫色
    # 切换时内容向上滚动一个"前一句区块"的高度
    scroll_shift = 0
    if cur_idx is not None:
        cur = subs[cur_idx]
        elapsed = t - cur["start"]
        is_in_gap = t > cur["end"]  # 在间隔时段不触发滚动

        if not is_in_gap and elapsed < SCROLL_DUR and cur_idx > 0:
            progress = ease_out(elapsed / SCROLL_DUR)
            # 滚动距离 = 当前句卡片高度 + 前句灰色块高度的差
            # 简化：用固定一个"前句块高"来滚动
            tmp_img = Image.new("RGB", (W, 10), BG_SUB)
            tmp_draw = ImageDraw.Draw(tmp_img)
            roll_h = calc_prev_block_h(cur_idx, tmp_draw) + th(tmp_draw, "Ag", F_TIMESTAMP) + 20
            scroll_shift = int(roll_h * (1 - progress))  # 从 roll_h→0，向上滚入

    # 渲染到超高画布
    sub_canvas_h = SUB_H + 600
    sub_img = Image.new("RGB", (W, sub_canvas_h), BG_SUB)
    draw = ImageDraw.Draw(sub_img)
    draw_sub_frame(draw, scroll_shift, cur_idx)

    # 裁切可视区域粘贴
    sub_cropped = sub_img.crop((0, 0, W, SUB_H))
    canvas.paste(sub_cropped, (0, TITLE_H + VIDEO_H))

    return np.array(canvas)

# ── 主流程 ────────────────────────────────────────────────────────────────────
def transcript_to_srt(transcript_path, srt_path):
    """把 whisper transcript.json 转成双语 SRT（英文+中文翻译用 googletrans）"""
    import json
    try:
        from googletrans import Translator
        translator = Translator()
    except ImportError:
        translator = None

    data = json.load(open(transcript_path, encoding='utf-8'))
    segs = data.get('segments', [])
    lines = []
    for i, s in enumerate(segs, 1):
        start = s['start']
        end = s['end']
        en = s['text'].strip()
        if translator:
            try:
                zh = translator.translate(en, src='en', dest='zh-cn').text
            except Exception:
                zh = ''
        else:
            zh = ''
        def fmt(t):
            h = int(t//3600); m = int((t%3600)//60); sc = t%60
            return f"{h:02d}:{m:02d}:{sc:06.3f}".replace('.',',')
        lines.append(f"{i}\n{fmt(start)} --> {fmt(end)}\n{en}\n{zh}\n")
    with open(srt_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    return srt_path

def main():
    print("解析字幕...")
    # 如果 SRT 不存在但有 transcript，自动转换
    import os
    if not os.path.exists(SRT_FILE) and _TRANSCRIPT_OVERRIDE and os.path.exists(_TRANSCRIPT_OVERRIDE):
        print(f"  SRT不存在，从transcript生成: {_TRANSCRIPT_OVERRIDE}")
        transcript_to_srt(_TRANSCRIPT_OVERRIDE, SRT_FILE)
    subs = parse_srt(SRT_FILE)
    print(f"共 {len(subs)} 条字幕")

    print("加载视频...")
    video = VideoFileClip(INPUT)
    fps = video.fps
    print(f"视频: {video.size}, {video.duration:.1f}s, {fps}fps")

    # 主体：逐帧处理（无片头封面）
    print("处理主体帧（字幕+双区布局）...")

    # 预热：提前渲染第0帧，让PIL字体缓存、关键词测量等全部初始化
    # 避免第一帧因冷启动拖慢导致视频开头卡顿
    print("预热渲染缓存...")
    _warmup_frame = video.get_frame(0)
    make_main_frame(_warmup_frame, subs, 0)
    make_main_frame(_warmup_frame, subs, 0)  # 第二次确保缓存稳定
    print("预热完成")

    FADE_IN_DUR = 1.0  # 主体开头淡入时长（秒）

    def process_frame(get_frame, t):
        frame = get_frame(t)
        result = make_main_frame(frame, subs, t)
        # 手动淡入：前 FADE_IN_DUR 秒与黑色混合，完全在 process_frame 内完成
        # 避免 moviepy FadeIn 在第一帧触发额外 seek/decode 导致卡顿
        if t < FADE_IN_DUR:
            alpha = t / FADE_IN_DUR          # 0.0 → 1.0
            result = (result * alpha).astype(np.uint8)
        return result

    main_clip = video.transform(process_frame, apply_to="video")

    # 片尾：定格最后一帧 2 秒，让最后一句话能落地
    last_frame = make_main_frame(video.get_frame(video.duration - 0.01), subs, video.duration - 0.01)
    outro_clip = ImageClip(last_frame, duration=2).with_fps(fps)

    # 拼接（无片头；主体淡入已在 process_frame 内手动完成）
    print("合成...")
    final = concatenate_videoclips([main_clip, outro_clip])

    print(f"导出 {OUTPUT}...")
    final.write_videofile(
        OUTPUT,
        codec="libx264",
        audio_codec="aac",
        fps=fps,
        preset="fast",
        ffmpeg_params=["-crf", "20"],
        logger="bar"
    )
    print(f"✅ 完成！→ {OUTPUT}")

if __name__ == "__main__":
    main()
