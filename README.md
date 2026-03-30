# 英语学习视频制作工具 🎬

自动把 TED 演讲 / 名人演讲制作成**双语字幕精读视频**，仿小红书爆款"Luna每日英语精读"风格。

## 效果预览

- 上方：原版英语视频
- 下方：当前句紫色高亮卡片（英文 + 中文翻译）
- 关键词黄色标注 + 中文释义

## 工作流

```
1. 小红书找爆款帖子（点赞 > 1000）
2. 找到对应 YouTube 原版视频
3. yt-dlp 下载 → ffmpeg 转 H.264 → 截取精华片段
4. Whisper 生成时间戳 → 写双语 SRT
5. 写关键词文件
6. burn_lara.py 渲染输出
```

## 使用方法

### 依赖

```bash
pip install moviepy pillow numpy
brew install ffmpeg
pip install openai-whisper
```

> ⚠️ 需要 macOS（字体依赖 STHeiti / PingFang）。Linux 用户需自备中文字体并修改 `load_font()` 里的路径。

### 渲染视频

```bash
python burn_lara.py \
  --input clip_celeste.mp4 \
  --output Celeste_英语学习版.mp4 \
  --srt clip_celeste_bilingual.srt \
  --keywords clip_celeste_keywords.py \
  --title "提高交流质量的建议" \
  --tag "TED精讲 · Celeste Headlee × TEDxCreativeCoast"
```

### 关键词文件格式

```python
# clip_xxx_keywords.py
# key = SRT 句子的 0-based 索引（第1句=0）
KEYWORDS = {
    0:  [("multitask", "一心多用——同时做多件事")],
    3:  [("pontificate", "说教"), ("pushback", "反驳/阻力")],
    # 没有关键词的句子不需要写
}
```

### 双语 SRT 格式

```
1
00:00:00,000 --> 00:00:05,419
So I'd like to spend the next 10 minutes teaching you how to talk.
接下来约10分钟，我想教你们如何说话。
```

## 视频库

已整理 50 条爆款视频（TED 30 + 名人演讲 20），见 [video_library_50.md](video_library_50.md)。

## License

MIT
