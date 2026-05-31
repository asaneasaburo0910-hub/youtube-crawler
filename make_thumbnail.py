import csv
import os
import requests
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO

# ============================
# 設定
# ============================
CSV_FILE = "youtube_trends.csv"
OUTPUT_FILE = f"thumbnail_{datetime.now().strftime('%Y%m%d')}.jpg"
ZUNDAMON_FILE = "zundamon-an.gif"

# YouTubeサムネイル推奨サイズ
W, H = 1280, 720


def load_rank1():
    """CSVから1位の動画を取得"""
    if not os.path.exists(CSV_FILE):
        print(f"❌ {CSV_FILE} が見つかりません")
        return None

    with open(CSV_FILE, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    if not rows:
        return None

    latest_time = max(r["fetched_at"] for r in rows)
    trending = [r for r in rows if r["fetched_at"] == latest_time and r["type"] == "急上昇動画"]
    trending.sort(key=lambda x: int(x["rank"]))
    return trending[0] if trending else None


def get_thumbnail(url):
    """YouTubeサムネイルを高解像度で取得"""
    try:
        video_id = url.split("v=")[-1].split("&")[0]
        for quality in ["maxresdefault", "hqdefault"]:
            res = requests.get(f"https://img.youtube.com/vi/{video_id}/{quality}.jpg", timeout=10)
            if res.status_code == 200:
                img = Image.open(BytesIO(res.content))
                if img.width >= 640:
                    return img
    except Exception as e:
        print(f"⚠️ サムネイル取得失敗: {e}")
    return None


def get_font(size):
    """フォントを取得（日本語対応）"""
    font_paths = [
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJKjp-Bold.otf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]
    for path in font_paths:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def make_thumbnail(item):
    """サムネイル画像を生成"""
    canvas = Image.new("RGB", (W, H), (10, 10, 20))
    draw = ImageDraw.Draw(canvas)

    # 1位のサムネイル画像を左側に大きく配置
    thumb = get_thumbnail(item["url"])
    if thumb:
        # 左側7割に配置
        thumb_w = int(W * 0.68)
        thumb_h = H
        thumb_resized = thumb.resize((thumb_w, thumb_h), Image.LANCZOS)
        canvas.paste(thumb_resized, (0, 0))

        # 左側に暗めのグラデーションオーバーレイ
        overlay = Image.new("RGBA", (thumb_w, H), (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        for x in range(thumb_w):
            alpha = int(180 * (1 - x / thumb_w) ** 0.5)
            overlay_draw.line([(x, 0), (x, H)], fill=(0, 0, 0, alpha))
        canvas.paste(Image.new("RGB", (thumb_w, H), (0, 0, 0)),
                     (0, 0), overlay)

    # 右側背景（黒）
    right_x = int(W * 0.68)
    draw.rectangle([right_x, 0, W, H], fill=(8, 8, 16))

    # 右側：赤い縦ライン
    draw.rectangle([right_x, 0, right_x + 6, H], fill=(255, 0, 0))

    # 右側：「急上昇」テキスト
    font_small = get_font(32)
    font_mid = get_font(52)
    font_large = get_font(88)
    font_title = get_font(28)

    right_center = right_x + (W - right_x) // 2

    draw.text((right_center, 80), "急上昇", font=font_mid,
              fill=(255, 215, 0), anchor="mm")

    # 「NO.1」大きく
    draw.text((right_center, 200), "NO.1", font=font_large,
              fill=(255, 215, 0), anchor="mm")

    # 金色アンダーライン
    line_w = 180
    draw.rectangle([right_center - line_w//2, 255, right_center + line_w//2, 261],
                   fill=(255, 215, 0))

    # 煽り文句
    draw.text((right_center, 330), "はコレだ！🔥", font=font_mid,
              fill=(255, 255, 255), anchor="mm")

    # 動画タイトル（折り返し）
    title = item["title"]
    max_chars = 12
    lines = [title[i:i+max_chars] for i in range(0, min(len(title), max_chars*2), max_chars)]
    for i, line in enumerate(lines[:2]):
        y = 430 + i * 40
        draw.text((right_center, y), line, font=font_title,
                  fill=(200, 200, 200), anchor="mm")

    # 再生数
    views = int(item["views"])
    if views >= 10000:
        views_str = f"👁 {views // 10000}万回視聴"
    else:
        views_str = f"👁 {views:,}回視聴"
    draw.text((right_center, 530), views_str, font=font_small,
              fill=(78, 201, 176), anchor="mm")

    # 左上に「1位」バッジ
    badge_r = 70
    draw.ellipse([20, 20, 20 + badge_r*2, 20 + badge_r*2], fill=(255, 0, 0))
    draw.text((20 + badge_r, 20 + badge_r), "1位", font=get_font(40),
              fill=(255, 255, 255), anchor="mm")

    # ずんだもん（右下）
    if os.path.exists(ZUNDAMON_FILE):
        try:
            zunda = Image.open(ZUNDAMON_FILE)
            # GIFの最初のフレームを使用
            zunda.seek(0)
            zunda_rgb = zunda.convert("RGBA")
            zunda_size = 200
            zunda_resized = zunda_rgb.resize((zunda_size, zunda_size), Image.LANCZOS)
            zunda_x = W - zunda_size - 10
            zunda_y = H - zunda_size - 10
            canvas.paste(zunda_resized, (zunda_x, zunda_y), zunda_resized)
            print("✅ ずんだもん配置完了")
        except Exception as e:
            print(f"⚠️ ずんだもん配置失敗: {e}")

    # 保存
    canvas.save(OUTPUT_FILE, "JPEG", quality=95)
    print(f"✅ {OUTPUT_FILE} を生成しました（{W}x{H}px）")


def main():
    print(f"🚀 サムネイル生成開始: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    item = load_rank1()
    if not item:
        print("❌ データがありません")
        return

    print(f"📌 1位の動画: {item['title'][:40]}")
    make_thumbnail(item)


if __name__ == "__main__":
    main()
