import csv
import os
from datetime import datetime
from collections import defaultdict

# ============================
# 設定
# ============================
CSV_FILE = "youtube_trends.csv"
OUTPUT_FILE = f"ranking_data_{datetime.now().strftime('%Y%m%d')}.csv"


def load_all_trending():
    if not os.path.exists(CSV_FILE):
        print(f"❌ {CSV_FILE} が見つかりません")
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
    this_month = datetime.now().strftime("%Y-%m")
    monthly = [r for r in rows if r["fetched_at"].startswith(this_month)]
    count = defaultdict(lambda: {"title": "", "channel": "", "count": 0, "max_views": 0, "max_likes": 0, "max_comments": 0, "url": ""})
    for r in monthly:
        vid = r["url"].split("v=")[-1].split("&")[0]
        count[vid]["title"] = r["title"]
        count[vid]["channel"] = r["channel"]
        count[vid]["count"] += 1
        count[vid]["max_views"] = max(count[vid]["max_views"], int(r["views"]))
        count[vid]["max_likes"] = max(count[vid]["max_likes"], int(r.get("likes", 0)))
        count[vid]["max_comments"] = max(count[vid]["max_comments"], int(r.get("comments", 0)))
        count[vid]["url"] = r["url"]
    return sorted(count.values(), key=lambda x: x["count"], reverse=True)[:limit]


def get_yearly_ranking(rows, limit=20):
    this_year = datetime.now().strftime("%Y")
    yearly = [r for r in rows if r["fetched_at"].startswith(this_year)]
    count = defaultdict(lambda: {"title": "", "channel": "", "count": 0, "max_views": 0, "max_likes": 0, "max_comments": 0, "url": ""})
    for r in yearly:
        vid = r["url"].split("v=")[-1].split("&")[0]
        count[vid]["title"] = r["title"]
        count[vid]["channel"] = r["channel"]
        count[vid]["count"] += 1
        count[vid]["max_views"] = max(count[vid]["max_views"], int(r["views"]))
        count[vid]["max_likes"] = max(count[vid]["max_likes"], int(r.get("likes", 0)))
        count[vid]["max_comments"] = max(count[vid]["max_comments"], int(r.get("comments", 0)))
        count[vid]["url"] = r["url"]
    return sorted(count.values(), key=lambda x: x["count"], reverse=True)[:limit]


def get_bonus_rankings(rows):
    this_month = datetime.now().strftime("%Y-%m")
    monthly = [r for r in rows if r["fetched_at"].startswith(this_month)]

    # コメント数1位
    most_comments = sorted(monthly, key=lambda x: int(x.get("comments", 0)), reverse=True)[:5]

    # 最速ランクイン
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
    fastest = fastest[:5]

    # 最大伸び率
    best_growth = []
    dates = sorted(set(r["fetched_at"][:10] for r in monthly))
    for i in range(1, len(dates)):
        prev_date = dates[i-1]
        curr_date = dates[i]
        prev_data = {r["url"].split("v=")[-1].split("&")[0]: int(r["views"])
                     for r in monthly if r["fetched_at"][:10] == prev_date}
        for r in monthly:
            if r["fetched_at"][:10] != curr_date:
                continue
            vid = r["url"].split("v=")[-1].split("&")[0]
            if vid in prev_data and prev_data[vid] > 0:
                growth = (int(r["views"]) - prev_data[vid]) / prev_data[vid] * 100
                best_growth.append((growth, r))
    best_growth.sort(key=lambda x: x[0], reverse=True)
    best_growth = best_growth[:5]

    return most_comments, fastest, best_growth


def main():
    print(f"🚀 ランキングCSV生成開始: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    rows = load_all_trending()
    if not rows:
        print("❌ データがありません")
        return

    latest_date = max(r["fetched_at"] for r in rows)[:10]
    dt = datetime.strptime(latest_date, "%Y-%m-%d")
    date_str = dt.strftime("%Y年%m月%d日")
    month_str = dt.strftime("%Y年%m月")
    year_str = dt.strftime("%Y年")

    latest = get_latest(rows, 100)
    monthly = get_monthly_ranking(rows, 20)
    yearly = get_yearly_ranking(rows, 20)
    most_comments, fastest, best_growth = get_bonus_rankings(rows)

    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)

        # ===== 本日TOP100 =====
        writer.writerow([f"■ {date_str} 急上昇ランキング TOP100"])
        writer.writerow(["順位", "タイトル", "チャンネル", "再生数", "いいね数", "コメント数", "動画長", "公開日時", "URL"])
        for item in latest:
            writer.writerow([
                f"#{item['rank']}",
                item["title"],
                item["channel"],
                item["views"],
                item.get("likes", 0),
                item.get("comments", 0),
                item.get("duration", ""),
                item.get("published_at", ""),
                item["url"],
            ])

        writer.writerow([])  # 空行

        # ===== 月間ランキング =====
        writer.writerow([f"■ {month_str} 月間ランキング（出現回数順）TOP20"])
        writer.writerow(["順位", "タイトル", "チャンネル", "出現日数", "最高再生数", "最高いいね数", "最高コメント数", "URL"])
        for i, item in enumerate(monthly, 1):
            writer.writerow([
                f"#{i}",
                item["title"],
                item["channel"],
                item["count"],
                item["max_views"],
                item["max_likes"],
                item["max_comments"],
                item["url"],
            ])

        writer.writerow([])

        # ===== 年間ランキング =====
        writer.writerow([f"■ {year_str} 年間ランキング（出現回数順）TOP20"])
        writer.writerow(["順位", "タイトル", "チャンネル", "出現日数", "最高再生数", "最高いいね数", "最高コメント数", "URL"])
        for i, item in enumerate(yearly, 1):
            writer.writerow([
                f"#{i}",
                item["title"],
                item["channel"],
                item["count"],
                item["max_views"],
                item["max_likes"],
                item["max_comments"],
                item["url"],
            ])

        writer.writerow([])

        # ===== 番外編 =====
        writer.writerow([f"■ {month_str} 番外編ランキング"])

        writer.writerow(["コメント数ランキング（最も議論を呼んだ動画）"])
        writer.writerow(["順位", "タイトル", "チャンネル", "コメント数", "再生数", "URL"])
        for i, item in enumerate(most_comments, 1):
            writer.writerow([f"#{i}", item["title"], item["channel"],
                             item.get("comments", 0), item["views"], item["url"]])

        writer.writerow([])

        writer.writerow(["最速ランクイン（公開から最短時間で急上昇入り）"])
        writer.writerow(["順位", "タイトル", "チャンネル", "公開からの時間(h)", "再生数", "URL"])
        for i, (hours, item) in enumerate(fastest, 1):
            writer.writerow([f"#{i}", item["title"], item["channel"],
                             f"{int(hours)}時間", item["views"], item["url"]])

        writer.writerow([])

        writer.writerow(["最大伸び率（前日比）"])
        writer.writerow(["順位", "タイトル", "チャンネル", "伸び率(%)", "再生数", "URL"])
        for i, (growth, item) in enumerate(best_growth, 1):
            writer.writerow([f"#{i}", item["title"], item["channel"],
                             f"+{int(growth)}%", item["views"], item["url"]])

    print(f"✅ {OUTPUT_FILE} を生成しました")
    print(f"   本日TOP100: {len(latest)}件")
    print(f"   月間TOP20: {len(monthly)}件")
    print(f"   年間TOP20: {len(yearly)}件")


if __name__ == "__main__":
    main()
