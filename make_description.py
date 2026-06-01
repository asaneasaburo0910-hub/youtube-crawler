import csv
import os
from datetime import datetime
from collections import defaultdict

# ============================
# 設定
# ============================
CSV_FILE = "youtube_trends.csv"
OUTPUT_FILE = f"description_{datetime.now().strftime('%Y%m%d')}.txt"
RANK_EMOJI = {1: "🥇", 2: "🥈", 3: "🥉"}


def load_all_trending():
    """CSVから全期間の急上昇データを読み込む"""
    if not os.path.exists(CSV_FILE):
        print(f"❌ {CSV_FILE} が見つかりません")
        return [], []

    with open(CSV_FILE, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    trending_rows = [r for r in rows if r["type"] == "急上昇動画"]
    return trending_rows


def get_latest(trending_rows):
    """最新データのTOP10"""
    if not trending_rows:
        return []
    latest_time = max(r["fetched_at"] for r in trending_rows)
    latest = [r for r in trending_rows if r["fetched_at"] == latest_time]
    latest.sort(key=lambda x: int(x["rank"]))
    return latest[:10]


def get_monthly(trending_rows):
    """今月の出現回数ランキング"""
    now = datetime.now()
    this_month = now.strftime("%Y-%m")
    monthly = [r for r in trending_rows if r["fetched_at"].startswith(this_month)]

    count = defaultdict(lambda: {"title": "", "channel": "", "count": 0, "max_views": 0, "url": ""})
    for r in monthly:
        vid = r["url"].split("v=")[-1].split("&")[0]
        count[vid]["title"] = r["title"]
        count[vid]["channel"] = r["channel"]
        count[vid]["count"] += 1
        count[vid]["max_views"] = max(count[vid]["max_views"], int(r["views"]))
        count[vid]["url"] = r["url"]

    ranked = sorted(count.values(), key=lambda x: x["count"], reverse=True)
    return ranked[:5]


def get_yearly(trending_rows):
    """今年の出現回数ランキング"""
    this_year = datetime.now().strftime("%Y")
    yearly = [r for r in trending_rows if r["fetched_at"].startswith(this_year)]

    count = defaultdict(lambda: {"title": "", "channel": "", "count": 0, "max_views": 0, "url": ""})
    for r in yearly:
        vid = r["url"].split("v=")[-1].split("&")[0]
        count[vid]["title"] = r["title"]
        count[vid]["channel"] = r["channel"]
        count[vid]["count"] += 1
        count[vid]["max_views"] = max(count[vid]["max_views"], int(r["views"]))
        count[vid]["url"] = r["url"]

    ranked = sorted(count.values(), key=lambda x: x["count"], reverse=True)
    return ranked[:5]


def get_bonus_rankings(trending_rows):
    """番外編ランキング"""
    now = datetime.now()
    this_month = now.strftime("%Y-%m")
    monthly = [r for r in trending_rows if r["fetched_at"].startswith(this_month)]

    # コメント数1位
    most_comments = sorted(monthly, key=lambda x: int(x.get("comments", 0)), reverse=True)

    # 最速ランクイン（公開から最短時間）
    fastest = []
    for r in monthly:
        try:
            published = datetime.strptime(r.get("published_at", ""), "%Y-%m-%d %H:%M")
            fetched = datetime.strptime(r["fetched_at"], "%Y-%m-%d %H:%M")
            hours = (fetched - published).total_seconds() / 3600
            if hours > 0:
                fastest.append((hours, r))
        except Exception:
            continue
    fastest.sort(key=lambda x: x[0])

    # 最多連続ランクイン
    vid_dates = defaultdict(set)
    for r in monthly:
        vid = r["url"].split("v=")[-1].split("&")[0]
        vid_dates[vid].add(r["fetched_at"][:10])
    consecutive = sorted(
        [{"title": trending_rows[[r["url"].split("v=")[-1].split("&")[0] for r in monthly].index(vid) if vid in [r["url"].split("v=")[-1].split("&")[0] for r in monthly] else 0]["title"] if monthly else "",
          "days": len(dates), "url": ""}
         for vid, dates in vid_dates.items()],
        key=lambda x: x["days"], reverse=True
    )

    # 最大伸び率（前日比）
    best_growth = []
    dates = sorted(set(r["fetched_at"][:10] for r in monthly))
    for i in range(1, len(dates)):
        prev_date = dates[i-1]
        curr_date = dates[i]
        prev_data = {r["url"].split("v=")[-1].split("&")[0]: int(r["views"])
                     for r in monthly if r["fetched_at"][:10] == prev_date}
        curr_data = [r for r in monthly if r["fetched_at"][:10] == curr_date]
        for r in curr_data:
            vid = r["url"].split("v=")[-1].split("&")[0]
            if vid in prev_data and prev_data[vid] > 0:
                growth = (int(r["views"]) - prev_data[vid]) / prev_data[vid] * 100
                best_growth.append((growth, r))
    best_growth.sort(key=lambda x: x[0], reverse=True)

    return most_comments, fastest, best_growth


def format_views(views):
    views = int(views)
    if views >= 100_000_000:
        return f"{views // 100_000_000}億"
    elif views >= 10_000:
        return f"{views // 10_000}万"
    return f"{views:,}"


def make_description(trending_rows, date_str, month_str, year_str):
    lines = []
    latest = get_latest(trending_rows)
    monthly = get_monthly(trending_rows)
    yearly = get_yearly(trending_rows)
    most_comments, fastest, best_growth = get_bonus_rankings(trending_rows)

    # ヘッダー
    lines.append(f"📊 {date_str} YouTube急上昇ランキング")
    lines.append("毎日自動集計！急上昇動画をランキング＆分析してお届けします🌿")
    lines.append("")

    # 本日TOP10
    lines.append("─" * 25)
    lines.append("🔥 本日の急上昇 TOP10")
    lines.append("")
    for item in latest:
        rank = int(item["rank"])
        emoji = RANK_EMOJI.get(rank, f"#{rank}")
        views_str = format_views(item["views"])
        lines.append(f"{emoji}{rank}位 {item['title'][:30]}")
        lines.append(f"👁{views_str}回 📺{item['channel'][:15]}")
        lines.append(f"🔗{item['url']}")
        lines.append("")

    # 月間ランキング
    lines.append("─" * 25)
    lines.append(f"📅 {month_str}月間ランキング（出現回数）")
    lines.append("")
    for i, item in enumerate(monthly, 1):
        emoji = RANK_EMOJI.get(i, f"#{i}")
        views_str = format_views(item["max_views"])
        lines.append(f"{emoji}{i}位 {item['title'][:30]}")
        lines.append(f"📆{item['count']}日ランクイン 👁最高{views_str}回")
        lines.append(f"🔗{item['url']}")
        lines.append("")

    # 年間ランキング
    lines.append("─" * 25)
    lines.append(f"🏆 {year_str}年間ランキング（出現回数）")
    lines.append("")
    for i, item in enumerate(yearly, 1):
        emoji = RANK_EMOJI.get(i, f"#{i}")
        views_str = format_views(item["max_views"])
        lines.append(f"{emoji}{i}位 {item['title'][:30]}")
        lines.append(f"📆{item['count']}日ランクイン 👁最高{views_str}回")
        lines.append(f"🔗{item['url']}")
        lines.append("")

    # 番外編
    lines.append("─" * 25)
    lines.append("🎖 今月の番外編ランキング")
    lines.append("")

    # コメント数1位
    if most_comments:
        r = most_comments[0]
        lines.append(f"💬 最も議論を呼んだ動画")
        lines.append(f"「{r['title'][:30]}」")
        lines.append(f"コメント{format_views(r.get('comments',0))}件 🔗{r['url']}")
        lines.append("")

    # 最速ランクイン
    if fastest:
        hours, r = fastest[0]
        lines.append(f"⚡ 最速ランクイン（公開{int(hours)}時間で急上昇！）")
        lines.append(f"「{r['title'][:30]}」")
        lines.append(f"🔗{r['url']}")
        lines.append("")

    # 最大伸び率
    if best_growth:
        growth, r = best_growth[0]
        lines.append(f"📈 最大伸び率（前日比+{int(growth)}%）")
        lines.append(f"「{r['title'][:30]}」")
        lines.append(f"🔗{r['url']}")
        lines.append("")

    # フッター
    lines.append("─" * 25)
    lines.append("✅ チャンネル登録・高評価よろしくお願いします！")
    lines.append("💬 気になった動画は何位？コメントで教えてください！")
    lines.append("")

    # ハッシュタグ
    tags = ["#YouTube急上昇", "#ランキング", "#トレンド", "#急上昇ランキング",
            "#YouTubeランキング", "#ゲーム", "#アニメ", "#映画", "#エンタメ", "#毎日更新"]
    lines.append(" ".join(tags))

    return "\n".join(lines)


def main():
    print(f"🚀 概要欄生成開始: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    trending_rows = load_all_trending()
    if not trending_rows:
        print("❌ データがありません")
        return

    latest_date = max(r["fetched_at"] for r in trending_rows)[:10]
    dt = datetime.strptime(latest_date, "%Y-%m-%d")
    date_str = dt.strftime("%Y年%m月%d日")
    month_str = dt.strftime("%Y年%m月")
    year_str = dt.strftime("%Y年")

    description = make_description(trending_rows, date_str, month_str, year_str)

    char_count = len(description)
    print(f"📝 文字数: {char_count} / 5000")

    if char_count > 5000:
        print("⚠️ 5000文字を超えています！調整が必要です")
    else:
        print(f"✅ 文字数OK（残り{5000 - char_count}文字）")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(description)

    print(f"✅ {OUTPUT_FILE} を生成しました")


if __name__ == "__main__":
    main()
