import requests
import csv
import os
from datetime import datetime

# ============================
# 設定
# ============================
YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY")  # GitHubのSecretsから自動取得
OUTPUT_FILE = "youtube_trends.csv"

# 検索キーワード
SEARCH_QUERIES = [
    {"label": "エンタメ", "query": "エンタメ"},
    {"label": "ゲーム", "query": "ゲーム 実況"},
    {"label": "アニメ", "query": "アニメ"},
    {"label": "映画", "query": "映画 レビュー"},
]


def fetch_youtube_trending():
    """YouTubeの急上昇動画を取得（日本）"""
    results = []
    try:
        url = "https://www.googleapis.com/youtube/v3/videos"
        params = {
            "part": "snippet,statistics",
            "chart": "mostPopular",
            "regionCode": "JP",
            "videoCategoryId": "0",  # 全カテゴリ
            "maxResults": 20,
            "key": YOUTUBE_API_KEY,
        }
        res = requests.get(url, params=params, timeout=15)
        data = res.json()

        for i, item in enumerate(data.get("items", []), 1):
            snippet = item.get("snippet", {})
            stats = item.get("statistics", {})
            results.append({
                "type": "急上昇動画",
                "label": "総合",
                "title": snippet.get("title", ""),
                "channel": snippet.get("channelTitle", ""),
                "views": int(stats.get("viewCount", 0)),
                "likes": int(stats.get("likeCount", 0)),
                "comments": int(stats.get("commentCount", 0)),
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

        video_ids = [item["id"]["videoId"] for item in data.get("items", [])]
        if not video_ids:
            return results

        # 再生数などの詳細を取得
        stats_url = "https://www.googleapis.com/youtube/v3/videos"
        stats_params = {
            "part": "snippet,statistics",
            "id": ",".join(video_ids),
            "key": YOUTUBE_API_KEY,
        }
        stats_res = requests.get(stats_url, params=stats_params, timeout=15)
        stats_data = stats_res.json()

        items = stats_data.get("items", [])
        items.sort(key=lambda x: int(x.get("statistics", {}).get("viewCount", 0)), reverse=True)

        for i, item in enumerate(items, 1):
            snippet = item.get("snippet", {})
            stats = item.get("statistics", {})
            results.append({
                "type": "キーワード検索",
                "label": query_info["label"],
                "title": snippet.get("title", ""),
                "channel": snippet.get("channelTitle", ""),
                "views": int(stats.get("viewCount", 0)),
                "likes": int(stats.get("likeCount", 0)),
                "comments": int(stats.get("commentCount", 0)),
                "rank": i,
                "url": f"https://www.youtube.com/watch?v={item['id']}",
                "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            })

        print(f"✅ {query_info['label']}: {len(results)}件取得")

    except Exception as e:
        print(f"❌ {query_info['label']} 取得失敗: {e}")

    return results


def save_csv(items):
    """結果をCSVに保存（追記モード）"""
    file_exists = os.path.exists(OUTPUT_FILE)
    fieldnames = ["type", "label", "title", "channel", "views", "likes", "comments", "rank", "url", "fetched_at"]

    with open(OUTPUT_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerows(items)

    print(f"💾 {OUTPUT_FILE} に {len(items)}件保存しました")


def main():
    print(f"🚀 YouTube トレンド収集開始: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    all_results = []

    # 急上昇動画
    trending = fetch_youtube_trending()
    all_results.extend(trending)

    # キーワード検索
    for query in SEARCH_QUERIES:
        items = fetch_youtube_search(query)
        all_results.extend(items)

    save_csv(all_results)

    # 上位5件表示
    print("\n📊 急上昇動画 トップ5:")
    for item in [i for i in all_results if i["type"] == "急上昇動画"][:5]:
        print(f"  {item['rank']}. {item['title'][:40]}... (再生数: {item['views']:,})")

    for query in SEARCH_QUERIES:
        print(f"\n📊 {query['label']} トップ3:")
        for item in [i for i in all_results if i["label"] == query["label"]][:3]:
            print(f"  {item['rank']}. {item['title'][:40]}... (再生数: {item['views']:,})")

    print(f"\n✨ 完了！合計 {len(all_results)} 件")


if __name__ == "__main__":
    main()
