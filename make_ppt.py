import csv
import os
import requests
from datetime import datetime
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from io import BytesIO

# ============================
# 設定
# ============================
CSV_FILE = "youtube_trends.csv"
OUTPUT_FILE = f"youtube_ranking_{datetime.now().strftime('%Y%m%d')}.pptx"

BG_DARK  = RGBColor(0x0F, 0x0F, 0x0F)
BG_CARD  = RGBColor(0x1E, 0x1E, 0x1E)
RED      = RGBColor(0xFF, 0x00, 0x00)
WHITE    = RGBColor(0xFF, 0xFF, 0xFF)
GRAY     = RGBColor(0xAA, 0xAA, 0xAA)
GOLD     = RGBColor(0xFF, 0xD7, 0x00)
SILVER   = RGBColor(0xC0, 0xC0, 0xC0)
BRONZE   = RGBColor(0xCD, 0x7F, 0x32)
RANK_COLORS = [GOLD, SILVER, BRONZE]


def load_csv():
    if not os.path.exists(CSV_FILE):
        print(f"❌ {CSV_FILE} が見つかりません")
        return [], {}

    with open(CSV_FILE, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    if not rows:
        return [], {}

    latest_time = max(r["fetched_at"] for r in rows)
    trending = []
    keyword_items = {}

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
    print("📋 ランク順:", [int(x["rank"]) for x in trending[:10]])
    return trending, keyword_items


def get_thumbnail(url):
    try:
        video_id = url.split("v=")[-1].split("&")[0]
        thumb_url = f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg"
        res = requests.get(thumb_url, timeout=10)
        if res.status_code == 200:
            return BytesIO(res.content)
    except Exception:
        pass
    return None


def add_bg(slide, prs, color=None):
    bg = slide.shapes.add_shape(
        1, Inches(0), Inches(0), prs.slide_width, prs.slide_height
    )
    bg.fill.solid()
    bg.fill.fore_color.rgb = color or BG_DARK
    bg.line.fill.background()


def make_title_slide(prs, date_str):
    """タイトルスライド"""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_bg(slide, prs)

    bar = slide.shapes.add_shape(1, Inches(0), Inches(2.1), prs.slide_width, Inches(1.3))
    bar.fill.solid()
    bar.fill.fore_color.rgb = RED
    bar.line.fill.background()

    tf = slide.shapes.add_textbox(Inches(0.5), Inches(2.18), Inches(9), Inches(1.0))
    p = tf.text_frame.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    run = p.add_run()
    run.text = "▶  YouTube トレンド ランキング"
    run.font.size = Pt(34)
    run.font.bold = True
    run.font.color.rgb = WHITE
    run.font.name = "Arial Black"

    tf2 = slide.shapes.add_textbox(Inches(0.5), Inches(3.6), Inches(9), Inches(0.6))
    p2 = tf2.text_frame.paragraphs[0]
    p2.alignment = PP_ALIGN.CENTER
    run2 = p2.add_run()
    run2.text = f"{date_str}  ·  急上昇 TOP 10 発表"
    run2.font.size = Pt(15)
    run2.font.color.rgb = GRAY
    run2.font.name = "Arial"


def make_rank_slide(prs, item, rank):
    """1枚に1動画（10位→2位）"""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_bg(slide, prs)

    rank_color = RANK_COLORS[rank - 1] if rank <= 3 else WHITE

    # ランク番号（大きく左上）
    tf_rank = slide.shapes.add_textbox(Inches(0.35), Inches(0.15), Inches(2), Inches(1.0))
    p = tf_rank.text_frame.paragraphs[0]
    run = p.add_run()
    run.text = f"#{rank}"
    run.font.size = Pt(52)
    run.font.bold = True
    run.font.color.rgb = rank_color
    run.font.name = "Arial Black"

    # サムネイル（左半分）
    thumb = get_thumbnail(item["url"])
    thumb_x, thumb_y, thumb_w, thumb_h = Inches(0.35), Inches(1.25), Inches(4.8), Inches(2.7)
    if thumb:
        try:
            slide.shapes.add_picture(thumb, thumb_x, thumb_y, thumb_w, thumb_h)
        except Exception:
            pass

    # タイトル（右側）
    title = item["title"]
    tf_title = slide.shapes.add_textbox(Inches(5.4), Inches(1.0), Inches(4.3), Inches(2.2))
    tf_title.text_frame.word_wrap = True
    p_title = tf_title.text_frame.paragraphs[0]
    run_title = p_title.add_run()
    run_title.text = title
    run_title.font.size = Pt(16)
    run_title.font.bold = True
    run_title.font.color.rgb = WHITE
    run_title.font.name = "Arial"

    # チャンネル名
    tf_ch = slide.shapes.add_textbox(Inches(5.4), Inches(3.3), Inches(4.3), Inches(0.4))
    p_ch = tf_ch.text_frame.paragraphs[0]
    run_ch = p_ch.add_run()
    run_ch.text = f"📺  {item['channel']}"
    run_ch.font.size = Pt(12)
    run_ch.font.color.rgb = GRAY
    run_ch.font.name = "Arial"

    # 再生数
    views = int(item["views"])
    tf_views = slide.shapes.add_textbox(Inches(5.4), Inches(3.75), Inches(4.3), Inches(0.4))
    p_views = tf_views.text_frame.paragraphs[0]
    run_views = p_views.add_run()
    run_views.text = f"👁  {views:,} 回視聴"
    run_views.font.size = Pt(13)
    run_views.font.bold = True
    run_views.font.color.rgb = rank_color
    run_views.font.name = "Arial"

    # 下部にYouTubeリンク
    tf_url = slide.shapes.add_textbox(Inches(0.35), Inches(4.9), Inches(9.3), Inches(0.4))
    p_url = tf_url.text_frame.paragraphs[0]
    run_url = p_url.add_run()
    run_url.text = item["url"]
    run_url.font.size = Pt(9)
    run_url.font.color.rgb = RGBColor(0x55, 0x55, 0x55)
    run_url.font.name = "Arial"


def make_first_place_slide(prs, item):
    """1位専用スライド（特別演出）"""
    slide = prs.slides.add_slide(prs.slide_layouts[6])

    # 背景：深い黒
    add_bg(slide, prs, RGBColor(0x08, 0x08, 0x08))

    # 金色のアクセントライン（上下）
    for y_pos in [Inches(0), Inches(5.5)]:
        line = slide.shapes.add_shape(1, Inches(0), y_pos, prs.slide_width, Inches(0.12))
        line.fill.solid()
        line.fill.fore_color.rgb = GOLD
        line.line.fill.background()

    # 🏆 と NO.1テキスト
    tf_crown = slide.shapes.add_textbox(Inches(0), Inches(0.12), Inches(10), Inches(1.1))
    p_crown = tf_crown.text_frame.paragraphs[0]
    p_crown.alignment = PP_ALIGN.CENTER
    run_crown = p_crown.add_run()
    run_crown.text = "🏆  NO. 1  🏆"
    run_crown.font.size = Pt(38)
    run_crown.font.bold = True
    run_crown.font.color.rgb = GOLD
    run_crown.font.name = "Arial Black"

    # サムネイル（中央・大きめ）
    thumb = get_thumbnail(item["url"])
    thumb_w, thumb_h = Inches(5.5), Inches(3.09)
    thumb_x = (Inches(10) - thumb_w) / 2
    thumb_y = Inches(1.3)
    if thumb:
        try:
            slide.shapes.add_picture(thumb, thumb_x, thumb_y, thumb_w, thumb_h)
        except Exception:
            pass

    # 動画タイトル
    title = item["title"][:55] + ("…" if len(item["title"]) > 55 else "")
    tf_title = slide.shapes.add_textbox(Inches(0.3), Inches(4.45), Inches(9.4), Inches(0.65))
    tf_title.text_frame.word_wrap = True
    p_title = tf_title.text_frame.paragraphs[0]
    p_title.alignment = PP_ALIGN.CENTER
    run_title = p_title.add_run()
    run_title.text = title
    run_title.font.size = Pt(15)
    run_title.font.bold = True
    run_title.font.color.rgb = WHITE
    run_title.font.name = "Arial"

    # チャンネル & 再生数
    views = int(item["views"])
    tf_info = slide.shapes.add_textbox(Inches(0.3), Inches(5.05), Inches(9.4), Inches(0.35))
    p_info = tf_info.text_frame.paragraphs[0]
    p_info.alignment = PP_ALIGN.CENTER
    run_info = p_info.add_run()
    run_info.text = f"📺 {item['channel']}  ·  👁 {views:,} 回視聴"
    run_info.font.size = Pt(11)
    run_info.font.color.rgb = GOLD
    run_info.font.name = "Arial"


def make_keyword_slide(prs, label, items):
    """キーワード別TOP5スライド"""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_bg(slide, prs)

    emoji = {"エンタメ": "🎬", "ゲーム": "🎮", "アニメ": "✨", "映画": "🍿"}.get(label, "📌")

    tf = slide.shapes.add_textbox(Inches(0.4), Inches(0.15), Inches(9), Inches(0.55))
    p = tf.text_frame.paragraphs[0]
    run = p.add_run()
    run.text = f"{emoji} {label} 人気動画 TOP {min(5, len(items))}"
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
        tf_rank = slide.shapes.add_textbox(Inches(2.4), y + Inches(0.05), Inches(0.6), Inches(0.6))
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
        tf_info = slide.shapes.add_textbox(Inches(2.95), y + Inches(0.52), Inches(6.6), Inches(0.32))
        p_info = tf_info.text_frame.paragraphs[0]
        run_info = p_info.add_run()
        run_info.text = f"📺 {item['channel']}  ·  👁 {views:,} 回視聴"
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

    # 1. タイトルスライド
    make_title_slide(prs, date_str)

    # 2. 急上昇：10位→2位（降順）
    top10 = trending[:10]
    for item in sorted(top10[1:], key=lambda x: int(x["rank"]), reverse=True):  # 10位→2位
        make_rank_slide(prs, item, int(item["rank"]))

    # 3. 1位（特別スライド）
    if top10:
        make_first_place_slide(prs, top10[0])

    # 4. キーワード別スライド
    for label, items in keyword_items.items():
        make_keyword_slide(prs, label, items)

    prs.save(OUTPUT_FILE)
    print(f"✅ {OUTPUT_FILE} を生成しました（{len(prs.slides)}スライド）")


if __name__ == "__main__":
    main()
