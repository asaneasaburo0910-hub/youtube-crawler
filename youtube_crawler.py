import requests
import csv
import os
from datetime import datetime

# ============================
# 設定
# ============================
YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY")
OUTPUT_FILE = "youtube_trends.csv"

SEARCH_QUERIES = [
    {"label": "エンタメ", "query": "エンタメ"},
    {"label": "ゲーム", "query": "ゲーム 実況"},
    {"label": "アニメ", "query": "アニメ"},
    {"label": "映画", "query": "映画 レビュー"},
]


def parse_duration(iso_duration):
    """ISO 8601形式の動画長を分:秒に変換（例: PT4M13S → 4:13）"""
    import re
    match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', iso_duration)
    if not match:
        return "不明"
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    if hours > 0:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes}:{seconds:02d}"


def format_published(published_at):
    """公開日時を日本時間に変換（例: 2026-05-09T10:00:00Z → 2026-05-09 19:00）"""
    from datetime import timezone, timedelta
    dt = datetime.strptime(published_at, "%Y-%m-%dT%H:%M:%SZ")
    jst = dt.replace(tzinfo=timezone.utc).astimezone(timezone(timedelta(hours=9)))
    return jst.strftime("%Y-%m-%d %H:%M")


def fetch_youtube_trending():
    """YouTubeの急上昇動画を取得（日本）"""
    results = []
    try:
        url = "https://www.googleapis.com/youtube/v3/videos"
        params = {
            "part": "snippet,statistics,contentDetails",  # contentDetailsで動画長を取得
            "chart": "mostPopular",
            "regionCode": "JP",
            "maxResults": 50,
            "key": YOUTUBE_API_KEY,
        }
        res = requests.get(url, params=params, timeout=15)
        data = res.json()

        if "error" in data:
            print(f"❌ APIエラー: {data['error']}")
            return results

        items_all = data.get("items", [])

        # 2ページ目を取得（50件追加して合計100件）
        next_token = data.get("nextPageToken")
        if next_token:
            params2 = dict(params)
            params2["pageToken"] = next_token
            res2 = requests.get(url, params=params2, timeout=15)
            data2 = res2.json()
            items_all += data2.get("items", [])

        for i, item in enumerate(items_all, 1):
            snippet = item.get("snippet", {})
            stats = item.get("statistics", {})
            content = item.get("contentDetails", {})
            results.append({
                "source": "急上昇動画",
                "type": "急上昇動画",
                "label": "総合",
                "title": snippet.get("title", ""),
                "channel": snippet.get("channelTitle", ""),
                "views": int(stats.get("viewCount", 0)),
                "likes": int(stats.get("likeCount", 0)),
                "comments": int(stats.get("commentCount", 0)),
                "duration": parse_duration(content.get("duration", "PT0S")),
                "published_at": format_published(snippet.get("publishedAt", "2000-01-01T00:00:00Z")),
                "rank": i,
                "url": f"https://www.youtube.com/watch?v={item['id']}",
                "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            })

        print(f"✅ 急上昇動画: {len(results)}件取得")

    except Exception as e:
        print(f"❌ 急上昇動画取得失敗: {e}")

    return results


def fetch_youtube_search(query_info):
    """キーワードで動画を検索してランキング取得"""
    results = []
    try:
        url = "https://www.googleapis.com/youtube/v3/search"
        params = {
            "part": "snippet",
            "q": query_info["query"],
            "type": "video",
            "order": "viewCount",
            "regionCode": "JP",
            "relevanceLanguage": "ja",
            "maxResults": 10,
            "key": YOUTUBE_API_KEY,
        }
        res = requests.get(url, params=params, timeout=15)
        data = res.json()

        if "error" in data:
            print(f"❌ {query_info['label']} APIエラー: {data['error']['message']}")
            return results

        video_ids = [item["id"]["videoId"] for item in data.get("items", [])]
        if not video_ids:
            return results

        # 詳細情報取得（contentDetails追加）
        stats_url = "https://www.googleapis.com/youtube/v3/videos"
        stats_params = {
            "part": "snippet,statistics,contentDetails",
            "id": ",".join(video_ids),
            "key": YOUTUBE_API_KEY,
        }
        stats_res = requests.get(stats_url, params=stats_params, timeout=15)
        stats_data = stats_res.json()

        if "error" in stats_data:
            print(f"❌ {query_info['label']} 詳細取得エラー: {stats_data['error']['message']}")
            return results

        items = stats_data.get("items", [])
        items.sort(key=lambda x: int(x.get("statistics", {}).get("viewCount", 0)), reverse=True)

        for i, item in enumerate(items, 1):
            snippet = item.get("snippet", {})
            stats = item.get("statistics", {})
            content = item.get("contentDetails", {})
            results.append({
                "source": "キーワード検索",
                "type": "キーワード検索",
                "label": query_info["label"],
                "title": snippet.get("title", ""),
                "channel": snippet.get("channelTitle", ""),
                "views": int(stats.get("viewCount", 0)),
                "likes": int(stats.get("likeCount", 0)),
                "comments": int(stats.get("commentCount", 0)),
                "duration": parse_duration(content.get("duration", "PT0S")),
                "published_at": format_published(snippet.get("publishedAt", "2000-01-01T00:00:00Z")),
                "rank": i,
                "url": f"https://www.youtube.com/watch?v={item['id']}",
                "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            })

        print(f"✅ {query_info['label']}: {len(results)}件取得")

    except Exception as e:
        print(f"❌ {query_info['label']} 取得失敗: {e}")

    return results


def save_csv(items):
    file_exists = os.path.exists(OUTPUT_FILE)
    fieldnames = ["type", "label", "title", "channel", "views", "likes", "comments",
                  "duration", "published_at", "rank", "url", "fetched_at"]

    with open(OUTPUT_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        if not file_exists:
            writer.writeheader()
        writer.writerows(items)

    print(f"💾 {OUTPUT_FILE} に {len(items)}件保存しました")


def main():
    print(f"🚀 YouTube トレンド収集開始: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"🔑 APIキー確認: {'設定済み' if YOUTUBE_API_KEY else '未設定！'}")

    all_results = []

    trending = fetch_youtube_trending()
    all_results.extend(trending)

    for query in SEARCH_QUERIES:
        items = fetch_youtube_search(query)
        all_results.extend(items)

    save_csv(all_results)

    print("\n📊 急上昇動画 トップ5:")
    for item in [i for i in all_results if i["type"] == "急上昇動画"][:5]:
        print(f"  {item['rank']}. {item['title'][:40]} (再生数: {item['views']:,} / {item['duration']} / 公開: {item['published_at']})")

    print(f"\n✨ 完了！合計 {len(all_results)} 件")


if __name__ == "__main__":
    main()
