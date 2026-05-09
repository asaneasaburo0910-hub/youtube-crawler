import csv
import os
import requests
from datetime import datetime
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from io import BytesIO

# ============================
# 設定
# ============================
CSV_FILE = "youtube_trends.csv"
OUTPUT_FILE = f"youtube_ranking_{datetime.now().strftime('%Y%m%d')}.pptx"

# カラーパレット（ダーク系・YouTube風）
BG_DARK   = RGBColor(0x0F, 0x0F, 0x0F)   # ほぼ黒
BG_CARD   = RGBColor(0x1E, 0x1E, 0x1E)   # カード背景
RED       = RGBColor(0xFF, 0x00, 0x00)   # YouTubeレッド
WHITE     = RGBColor(0xFF, 0xFF, 0xFF)
GRAY      = RGBColor(0xAA, 0xAA, 0xAA)
GOLD      = RGBColor(0xFF, 0xD7, 0x00)
SILVER    = RGBColor(0xC0, 0xC0, 0xC0)
BRONZE    = RGBColor(0xCD, 0x7F, 0x32)
RANK_COLORS = [GOLD, SILVER, BRONZE]


def load_csv():
    """CSVから最新データを読み込む"""
    if not os.path.exists(CSV_FILE):
        print(f"❌ {CSV_FILE} が見つかりません")
        return [], []

    trending = []
    keyword_items = {}

    with open(CSV_FILE, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    # 最新の fetched_at を取得
    if not rows:
        return [], []
    latest_time = max(r["fetched_at"] for r in rows)

    for row in rows:
        if row["fetched_at"] != latest_time:
            continue
        if row["type"] == "急上昇動画":
            trending.append(row)
        elif row["type"] == "キーワード検索":
            label = row["label"]
            if label not in keyword_items:
                keyword_items[label] = []
            keyword_items[label].append(row)

    trending.sort(key=lambda x: int(x["rank"]))
    return trending, keyword_items


def get_thumbnail(url):
    """YouTubeサムネイルを取得してBytesIOで返す"""
    try:
        video_id = url.split("v=")[-1].split("&")[0]
        thumb_url = f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg"
        res = requests.get(thumb_url, timeout=10)
        if res.status_code == 200:
            return BytesIO(res.content)
    except Exception:
        pass
    return None


def add_bg(slide, prs):
    """スライド背景を黒に"""
    from pptx.util import Inches
    bg = slide.shapes.add_shape(
        1,  # RECTANGLE
        Inches(0), Inches(0), prs.slide_width, prs.slide_height
    )
    bg.fill.solid()
    bg.fill.fore_color.rgb = BG_DARK
    bg.line.fill.background()


def make_title_slide(prs, date_str):
    """タイトルスライド"""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_bg(slide, prs)

    # YouTubeロゴ風赤帯
    bar = slide.shapes.add_shape(1, Inches(0), Inches(2.2), prs.slide_width, Inches(1.2))
    bar.fill.solid()
    bar.fill.fore_color.rgb = RED
    bar.line.fill.background()

    # タイトル
    tf = slide.shapes.add_textbox(Inches(0.5), Inches(2.25), Inches(9), Inches(1.0))
    p = tf.text_frame.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    run = p.add_run()
    run.text = "▶  YouTube トレンド ランキング"
    run.font.size = Pt(32)
    run.font.bold = True
    run.font.color.rgb = WHITE
    run.font.name = "Arial Black"

    # 日付
    tf2 = slide.shapes.add_textbox(Inches(0.5), Inches(3.6), Inches(9), Inches(0.6))
    p2 = tf2.text_frame.paragraphs[0]
    p2.alignment = PP_ALIGN.CENTER
    run2 = p2.add_run()
    run2.text = date_str
    run2.font.size = Pt(16)
    run2.font.color.rgb = GRAY
    run2.font.name = "Arial"


def make_trending_slide(prs, items, start_rank=1):
    """急上昇ランキングスライド（5件ずつ）"""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_bg(slide, prs)

    # スライドタイトル
    tf = slide.shapes.add_textbox(Inches(0.4), Inches(0.15), Inches(9), Inches(0.55))
    p = tf.text_frame.paragraphs[0]
    run = p.add_run()
    run.text = f"🔥 急上昇動画 TOP {start_rank}〜{start_rank + len(items) - 1}"
    run.font.size = Pt(22)
    run.font.bold = True
    run.font.color.rgb = WHITE
    run.font.name = "Arial Black"

    # 各動画カード
    card_h = Inches(0.88)
    thumb_w = Inches(1.9)
    thumb_h = Inches(1.07)

    for i, item in enumerate(items):
        rank = start_rank + i
        y = Inches(0.82) + i * (card_h + Inches(0.08))

        # カード背景
        card = slide.shapes.add_shape(1, Inches(0.3), y, Inches(9.4), card_h)
        card.fill.solid()
        card.fill.fore_color.rgb = BG_CARD
        card.line.color.rgb = RGBColor(0x33, 0x33, 0x33)
        card.line.width = Pt(0.5)

        # サムネイル
        thumb = get_thumbnail(item["url"])
        if thumb:
            try:
                slide.shapes.add_picture(thumb, Inches(0.35), y + Inches(0.0), thumb_w, thumb_h)
            except Exception:
                pass

        # ランク番号
        rank_color = RANK_COLORS[rank - 1] if rank <= 3 else GRAY
        tf_rank = slide.shapes.add_textbox(Inches(2.4), y + Inches(0.05), Inches(0.5), Inches(0.6))
        p_rank = tf_rank.text_frame.paragraphs[0]
        run_rank = p_rank.add_run()
        run_rank.text = f"#{rank}"
        run_rank.font.size = Pt(15)
        run_rank.font.bold = True
        run_rank.font.color.rgb = rank_color
        run_rank.font.name = "Arial Black"

        # タイトル
        title = item["title"][:45] + ("…" if len(item["title"]) > 45 else "")
        tf_title = slide.shapes.add_textbox(Inches(2.95), y + Inches(0.05), Inches(6.6), Inches(0.45))
        tf_title.text_frame.word_wrap = True
        p_title = tf_title.text_frame.paragraphs[0]
        run_title = p_title.add_run()
        run_title.text = title
        run_title.font.size = Pt(13)
        run_title.font.bold = True
        run_title.font.color.rgb = WHITE
        run_title.font.name = "Arial"

        # チャンネル名 & 再生数
        views = int(item["views"])
        views_str = f"{views:,} 回視聴"
        info = f"📺 {item['channel']}  ·  👁 {views_str}"
        tf_info = slide.shapes.add_textbox(Inches(2.95), y + Inches(0.52), Inches(6.6), Inches(0.32))
        p_info = tf_info.text_frame.paragraphs[0]
        run_info = p_info.add_run()
        run_info.text = info
        run_info.font.size = Pt(10)
        run_info.font.color.rgb = GRAY
        run_info.font.name = "Arial"


def make_keyword_slide(prs, label, items):
    """キーワード別ランキングスライド"""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_bg(slide, prs)

    emoji = {"エンタメ": "🎬", "ゲーム": "🎮", "アニメ": "✨", "映画": "🍿"}.get(label, "📌")

    tf = slide.shapes.add_textbox(Inches(0.4), Inches(0.15), Inches(9), Inches(0.55))
    p = tf.text_frame.paragraphs[0]
    run = p.add_run()
    run.text = f"{emoji} {label} 人気動画 TOP {len(items)}"
    run.font.size = Pt(22)
    run.font.bold = True
    run.font.color.rgb = WHITE
    run.font.name = "Arial Black"

    card_h = Inches(0.88)
    thumb_w = Inches(1.9)
    thumb_h = Inches(1.07)

    for i, item in enumerate(items[:5]):
        rank = int(item["rank"])
        y = Inches(0.82) + i * (card_h + Inches(0.08))

        card = slide.shapes.add_shape(1, Inches(0.3), y, Inches(9.4), card_h)
        card.fill.solid()
        card.fill.fore_color.rgb = BG_CARD
        card.line.color.rgb = RGBColor(0x33, 0x33, 0x33)
        card.line.width = Pt(0.5)

        thumb = get_thumbnail(item["url"])
        if thumb:
            try:
                slide.shapes.add_picture(thumb, Inches(0.35), y, thumb_w, thumb_h)
            except Exception:
                pass

        rank_color = RANK_COLORS[rank - 1] if rank <= 3 else GRAY
        tf_rank = slide.shapes.add_textbox(Inches(2.4), y + Inches(0.05), Inches(0.5), Inches(0.6))
        p_rank = tf_rank.text_frame.paragraphs[0]
        run_rank = p_rank.add_run()
        run_rank.text = f"#{rank}"
        run_rank.font.size = Pt(15)
        run_rank.font.bold = True
        run_rank.font.color.rgb = rank_color
        run_rank.font.name = "Arial Black"

        title = item["title"][:45] + ("…" if len(item["title"]) > 45 else "")
        tf_title = slide.shapes.add_textbox(Inches(2.95), y + Inches(0.05), Inches(6.6), Inches(0.45))
        tf_title.text_frame.word_wrap = True
        p_title = tf_title.text_frame.paragraphs[0]
        run_title = p_title.add_run()
        run_title.text = title
        run_title.font.size = Pt(13)
        run_title.font.bold = True
        run_title.font.color.rgb = WHITE
        run_title.font.name = "Arial"

        views = int(item["views"])
        views_str = f"{views:,} 回視聴"
        info = f"📺 {item['channel']}  ·  👁 {views_str}"
        tf_info = slide.shapes.add_textbox(Inches(2.95), y + Inches(0.52), Inches(6.6), Inches(0.32))
        p_info = tf_info.text_frame.paragraphs[0]
        run_info = p_info.add_run()
        run_info.text = info
        run_info.font.size = Pt(10)
        run_info.font.color.rgb = GRAY
        run_info.font.name = "Arial"


def main():
    print(f"🚀 PPT生成開始: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    trending, keyword_items = load_csv()
    if not trending and not keyword_items:
        print("❌ データがありません")
        return

    prs = Presentation()
    prs.slide_width  = Inches(10)
    prs.slide_height = Inches(5.625)

    date_str = datetime.now().strftime("%Y年%m月%d日")

    # タイトルスライド
    make_title_slide(prs, date_str)

    # 急上昇TOP10（5件ずつ2スライド）
    for chunk_start in range(0, min(10, len(trending)), 5):
        chunk = trending[chunk_start:chunk_start + 5]
        make_trending_slide(prs, chunk, start_rank=chunk_start + 1)

    # キーワード別スライド
    for label, items in keyword_items.items():
        make_keyword_slide(prs, label, items)

    prs.save(OUTPUT_FILE)
    print(f"✅ {OUTPUT_FILE} を生成しました（{len(prs.slides)}スライド）")


if __name__ == "__main__":
    main()
