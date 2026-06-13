import csv
import os
import requests
from datetime import datetime
from collections import defaultdict
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor, white, black
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# ============================
# 設定
# ============================
CSV_FILE = "youtube_trends.csv"
OUTPUT_FILE = f"ranking_data_{datetime.now().strftime('%Y%m%d')}.pdf"

# カラー
C_BG       = HexColor("#0F0F14")
C_RED      = HexColor("#FF0000")
C_GOLD     = HexColor("#FFD700")
C_SILVER   = HexColor("#C0C0C0")
C_BRONZE   = HexColor("#CD7F32")
C_TEAL     = HexColor("#4EC9B0")
C_GRAY     = HexColor("#888888")
C_WHITE    = white
C_DARK     = HexColor("#1E1E2E")
C_ACCENT   = HexColor("#7C3AED")


def setup_fonts():
    """日本語フォントのセットアップ"""
    import glob
    # 利用可能なNotoフォントを探す
    search_patterns = [
        "/usr/share/fonts/**/Noto*CJK*Bold*.ttc",
        "/usr/share/fonts/**/Noto*CJK*Bold*.otf",
        "/usr/share/fonts/**/Noto*CJK*Regular*.ttc",
        "/usr/share/fonts/**/Noto*CJK*Regular*.otf",
        "/usr/share/fonts/**/NotoSans*Bold*.ttf",
        "/usr/share/fonts/**/NotoSans*Regular*.ttf",
    ]
    found_fonts = []
    for pattern in search_patterns:
        found_fonts.extend(glob.glob(pattern, recursive=True))

    print(f"🔍 見つかったフォント: {found_fonts[:3]}")

    registered = set()
    for path in found_fonts:
        name = "NotoSansJP-Bold" if "Bold" in path else "NotoSansJP"
        if name not in registered:
            try:
                pdfmetrics.registerFont(TTFont(name, path))
                registered.add(name)
                print(f"✅ フォント登録: {name} ({path})")
            except Exception as e:
                print(f"⚠️ フォント登録失敗: {path} → {e}")

    if "NotoSansJP-Bold" not in registered:
        print("⚠️ 日本語フォントなし。Helveticaを使用")
        return "Helvetica-Bold", "Helvetica"
    return "NotoSansJP-Bold", "NotoSansJP" if "NotoSansJP" in registered else "NotoSansJP-Bold"


def load_all_trending():
    if not os.path.exists(CSV_FILE):
        return []
    with open(CSV_FILE, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return [r for r in rows if r["type"] == "急上昇動画"]


def get_latest(rows, limit=100):
    if not rows:
        return []
    latest_time = max(r["fetched_at"] for r in rows)
    latest = [r for r in rows if r["fetched_at"] == latest_time]
    latest.sort(key=lambda x: int(x["rank"]))
    return latest[:limit]


def get_monthly_ranking(rows, limit=20):
    now = datetime.now()
    this_month = now.strftime("%Y-%m")
    monthly = [r for r in rows if r["fetched_at"].startswith(this_month)]
    count = defaultdict(lambda: {"title": "", "channel": "", "count": 0, "max_views": 0, "max_likes": 0, "url": ""})
    for r in monthly:
        vid = r["url"].split("v=")[-1].split("&")[0]
        count[vid]["title"] = r["title"]
        count[vid]["channel"] = r["channel"]
        count[vid]["count"] += 1
        count[vid]["max_views"] = max(count[vid]["max_views"], int(r["views"]))
        count[vid]["max_likes"] = max(count[vid]["max_likes"], int(r.get("likes", 0)))
        count[vid]["url"] = r["url"]
    return sorted(count.values(), key=lambda x: x["count"], reverse=True)[:limit]


def get_yearly_ranking(rows, limit=20):
    this_year = datetime.now().strftime("%Y")
    yearly = [r for r in rows if r["fetched_at"].startswith(this_year)]
    count = defaultdict(lambda: {"title": "", "channel": "", "count": 0, "max_views": 0, "max_likes": 0, "url": ""})
    for r in yearly:
        vid = r["url"].split("v=")[-1].split("&")[0]
        count[vid]["title"] = r["title"]
        count[vid]["channel"] = r["channel"]
        count[vid]["count"] += 1
        count[vid]["max_views"] = max(count[vid]["max_views"], int(r["views"]))
        count[vid]["max_likes"] = max(count[vid]["max_likes"], int(r.get("likes", 0)))
        count[vid]["url"] = r["url"]
    return sorted(count.values(), key=lambda x: x["count"], reverse=True)[:limit]


def format_views(views):
    views = int(views)
    if views >= 100_000_000:
        return f"{views // 100_000_000}億"
    elif views >= 10_000:
        return f"{views // 10_000}万"
    return f"{views:,}"


def rank_color(rank):
    if rank == 1: return C_GOLD
    if rank == 2: return C_SILVER
    if rank == 3: return C_BRONZE
    return C_WHITE


def make_pdf(trending_rows, date_str, month_str, year_str, font_bold, font_normal):
    doc = SimpleDocTemplate(
        OUTPUT_FILE,
        pagesize=A4,
        leftMargin=15*mm,
        rightMargin=15*mm,
        topMargin=15*mm,
        bottomMargin=15*mm,
    )

    # スタイル
    def style(size, color=C_WHITE, bold=False, align=TA_LEFT):
        return ParagraphStyle(
            name=f"s{size}{bold}",
            fontName=font_bold if bold else font_normal,
            fontSize=size,
            textColor=color,
            alignment=align,
            leading=size * 1.4,
            backColor=C_BG,
        )

    story = []
    W = A4[0] - 30*mm  # 使用可能幅

    def section_title(text, color=C_TEAL):
        story.append(Spacer(1, 4*mm))
        story.append(Paragraph(text, style(13, color, bold=True)))
        story.append(HRFlowable(width="100%", thickness=1, color=color, spaceAfter=3*mm))

    def ranking_table(items, cols):
        """ランキングテーブルを生成"""
        data = [cols[0]]  # ヘッダー行
        for i, item in enumerate(items, 1):
            row = cols[1](i, item)
            data.append(row)

        col_widths = cols[2]
        t = Table(data, colWidths=col_widths)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), C_ACCENT),
            ("TEXTCOLOR", (0, 0), (-1, 0), C_WHITE),
            ("FONTNAME", (0, 0), (-1, 0), font_bold),
            ("FONTSIZE", (0, 0), (-1, 0), 8),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [C_DARK, C_BG]),
            ("FONTNAME", (0, 1), (-1, -1), font_normal),
            ("FONTSIZE", (0, 1), (-1, -1), 7),
            ("TEXTCOLOR", (0, 1), (-1, -1), C_WHITE),
            ("GRID", (0, 0), (-1, -1), 0.3, HexColor("#333344")),
            ("PADDING", (0, 0), (-1, -1), 3),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(t)

    # ===== 表紙 =====
    story.append(Spacer(1, 20*mm))
    story.append(Paragraph("YouTube", style(28, C_RED, bold=True, align=TA_CENTER)))
    story.append(Paragraph("急上昇ランキング", style(22, C_WHITE, bold=True, align=TA_CENTER)))
    story.append(Paragraph("リサーチデータ", style(18, C_TEAL, bold=True, align=TA_CENTER)))
    story.append(Spacer(1, 8*mm))
    story.append(HRFlowable(width="60%", thickness=2, color=C_GOLD, hAlign="CENTER"))
    story.append(Spacer(1, 8*mm))
    story.append(Paragraph(date_str, style(14, C_GOLD, align=TA_CENTER)))
    story.append(Spacer(1, 4*mm))
    story.append(Paragraph("チャンネル登録・高評価者限定配布資料", style(10, C_GRAY, align=TA_CENTER)))
    story.append(Spacer(1, 4*mm))
    story.append(Paragraph("©本データの無断転載・再配布を禁じます", style(8, C_GRAY, align=TA_CENTER)))
    story.append(PageBreak())

    # ===== 本日のTOP100 =====
    latest = get_latest(trending_rows, 100)
    section_title(f"🔥 {date_str} 急上昇ランキング TOP{len(latest)}")

    def latest_row(i, item):
        rc = rank_color(i)
        views = format_views(item["views"])
        likes = format_views(item.get("likes", 0))
        comments = format_views(item.get("comments", 0))
        duration = item.get("duration", "-")
        return [
            Paragraph(f'<font color="#{rc.hexval()[2:]}"><b>#{i}</b></font>', style(8, rc, bold=True)),
            Paragraph(item["title"][:35], style(7)),
            Paragraph(item["channel"][:15], style(7, C_GRAY)),
            Paragraph(f"{views}回", style(7, C_TEAL)),
            Paragraph(f"{likes}", style(7)),
            Paragraph(f"{comments}", style(7)),
            Paragraph(duration, style(7, C_GRAY)),
        ]

    ranking_table(
        latest,
        cols=[
            ["順位", "タイトル", "チャンネル", "再生数", "いいね", "コメント", "長さ"],
            latest_row,
            [12*mm, 65*mm, 32*mm, 18*mm, 15*mm, 15*mm, 13*mm],
        ]
    )
    story.append(PageBreak())

    # ===== 月間ランキング =====
    monthly = get_monthly_ranking(trending_rows, 20)
    section_title(f"📅 {month_str} 月間ランキング（出現回数順）TOP{len(monthly)}")

    def monthly_row(i, item):
        rc = rank_color(i)
        return [
            Paragraph(f'<font color="#{rc.hexval()[2:]}"><b>#{i}</b></font>', style(8, rc, bold=True)),
            Paragraph(item["title"][:35], style(7)),
            Paragraph(item["channel"][:15], style(7, C_GRAY)),
            Paragraph(f'{item["count"]}日', style(7, C_TEAL, bold=True)),
            Paragraph(format_views(item["max_views"]) + "回", style(7)),
            Paragraph(format_views(item["max_likes"]), style(7)),
        ]

    ranking_table(
        monthly,
        cols=[
            ["順位", "タイトル", "チャンネル", "出現日数", "最高再生数", "最高いいね"],
            monthly_row,
            [12*mm, 72*mm, 32*mm, 18*mm, 22*mm, 18*mm],
        ]
    )
    story.append(PageBreak())

    # ===== 年間ランキング =====
    yearly = get_yearly_ranking(trending_rows, 20)
    section_title(f"🏆 {year_str} 年間ランキング（出現回数順）TOP{len(yearly)}")

    def yearly_row(i, item):
        rc = rank_color(i)
        return [
            Paragraph(f'<font color="#{rc.hexval()[2:]}"><b>#{i}</b></font>', style(8, rc, bold=True)),
            Paragraph(item["title"][:35], style(7)),
            Paragraph(item["channel"][:15], style(7, C_GRAY)),
            Paragraph(f'{item["count"]}日', style(7, C_TEAL, bold=True)),
            Paragraph(format_views(item["max_views"]) + "回", style(7)),
            Paragraph(format_views(item["max_likes"]), style(7)),
        ]

    ranking_table(
        yearly,
        cols=[
            ["順位", "タイトル", "チャンネル", "出現日数", "最高再生数", "最高いいね"],
            yearly_row,
            [12*mm, 72*mm, 32*mm, 18*mm, 22*mm, 18*mm],
        ]
    )

    # フッター
    story.append(Spacer(1, 8*mm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=C_GRAY))
    story.append(Spacer(1, 3*mm))
    story.append(Paragraph(
        f"発行日: {date_str}　©YouTube急上昇ランキングチャンネル　無断転載禁止",
        style(7, C_GRAY, align=TA_CENTER)
    ))

    # ビルド（背景色設定）
    def on_page(canvas, doc):
        canvas.saveState()
        canvas.setFillColor(C_BG)
        canvas.rect(0, 0, A4[0], A4[1], fill=1, stroke=0)
        canvas.restoreState()

    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    print(f"✅ {OUTPUT_FILE} を生成しました")


def main():
    print(f"🚀 PDF生成開始: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    font_bold, font_normal = setup_fonts()
    print(f"🔤 フォント: {font_bold} / {font_normal}")

    trending_rows = load_all_trending()
    if not trending_rows:
        print("❌ データがありません")
        return

    latest_date = max(r["fetched_at"] for r in trending_rows)[:10]
    dt = datetime.strptime(latest_date, "%Y-%m-%d")
    date_str = dt.strftime("%Y年%m月%d日")
    month_str = dt.strftime("%Y年%m月")
    year_str = dt.strftime("%Y年")

    make_pdf(trending_rows, date_str, month_str, year_str, font_bold, font_normal)
    print(f"📄 ページ構成: 表紙 + 本日TOP100 + 月間TOP20 + 年間TOP20")


if __name__ == "__main__":
    main()
