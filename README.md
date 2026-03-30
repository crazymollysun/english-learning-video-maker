# 英语学习视频制作工具 🎬
# English Learning Video Maker

自动把 TED 演讲 / 名人演讲制作成**双语字幕精读视频**，仿小红书爆款"Luna每日英语精读"风格。

Automatically turn TED talks and celebrity speeches into **bilingual subtitle learning videos**, inspired by viral Chinese social media English learning content.

---

## 效果 / Preview

- 上方：原版英语视频 | Top: Original English video
- 下方：当前句紫色高亮卡片（英文 + 中文翻译）| Bottom: Purple highlight card (EN + ZH translation)
- 关键词黄色标注 + 中文释义 | Key vocabulary highlighted in yellow with explanations

---

## 工作流 / Workflow

```
1. 小红书找爆款帖子（点赞 > 1000）
   Find viral posts on Xiaohongshu (likes > 1000)

2. 找到对应 YouTube 原版视频
   Match to the original YouTube video

3. yt-dlp 下载 → ffmpeg 转 H.264 → 截取精华片段
   Download with yt-dlp → convert to H.264 → cut key segment

4. Whisper 生成时间戳 → 写双语 SRT
   Whisper transcription → write bilingual SRT

5. 写关键词文件
   Write keywords file

6. burn_lara.py 渲染输出
   Render with burn_lara.py
```

---

## 使用方法 / Usage

### 依赖 / Dependencies

```bash
pip install moviepy pillow numpy
brew install ffmpeg
pip install openai-whisper
```

> ⚠️ 需要 macOS（字体依赖 STHeiti / PingFang）。Linux 用户需自备中文字体并修改 `load_font()` 里的路径。
>
> Requires macOS (uses STHeiti / PingFang fonts). Linux users need to provide their own Chinese fonts and update the `load_font()` paths.

### 渲染视频 / Render

```bash
python burn_lara.py \
  --input clip_celeste.mp4 \
  --output Celeste_英语学习版.mp4 \
  --srt clip_celeste_bilingual.srt \
  --keywords clip_celeste_keywords.py \
  --title "10条让对话质量翻倍的建议" \
  --tag "TED精讲 · Celeste Headlee × TEDxCreativeCoast"
```

### 关键词文件格式 / Keywords Format

```python
# clip_xxx_keywords.py
# key = SRT 句子的 0-based 索引（第1句=0）
# key = 0-based sentence index in SRT (first sentence = 0)

# 关键词选词原则 / Selection principles:
# ✅ 标注：地道表达、口语短语、高级词汇、容易误解的用法
#    Mark: idiomatic expressions, colloquial phrases, advanced vocab, easily misunderstood usage
# ✅ 没有好词时：标注短语的常规用法或句型
#    When no good word: mark the phrase's common usage or sentence pattern
# ❌ 不标注：基础词汇（teach/look/talk/time 等所有人都认识的词）
#    Don't mark: basic vocabulary that everyone knows

KEYWORDS = {
    0:  [("I'd like to", "比 I want to 更礼貌客气的表达 | more polite than 'I want to'")],
    4:  [("crap", "废话/垃圾——非正式强烈否定 | informal: nonsense, worthless stuff")],
    14: [("multitask", "一心多用 | doing multiple things at once"),
         ("set down", "放下——比 put down 更正式 | more formal than 'put down'")],
    18: [("pontificate", "说教——自以为是地长篇发表意见 | to lecture others arrogantly"),
         ("pushback", "反驳/阻力 | resistance or objection from others")],
}
```

### 双语 SRT 格式 / Bilingual SRT Format

```
1
00:00:00,000 --> 00:00:05,419
So I'd like to spend the next 10 minutes teaching you how to talk.
接下来约10分钟，我想教你们如何说话。
```

---

## 视频库 / Video Library

已整理 50 条爆款视频（TED 30 + 名人演讲 20），见 [video_library_50.md](video_library_50.md)。

50 curated viral videos (30 TED + 20 celebrity speeches/interviews). See [video_library_50.md](video_library_50.md).

---

## License

MIT
