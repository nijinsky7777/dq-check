import os
import json
import urllib.parse
import urllib.request

DISCORD_URL = os.environ.get("DISCORD_WEBHOOK_URL")

KEYWORDS = [
    "メタリックモンスターズギャラリー",
    "メタリックアイテムズギャラリー"
]

def send_discord(msg):
    if not DISCORD_URL:
        print("Webhook URLが設定されていません")
        print(msg)
        return
    
    req = urllib.request.Request(
        DISCORD_URL,
        data=json.dumps({"content": msg}).encode('utf-8'),
        headers={'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'}
    )
    try:
        with urllib.request.urlopen(req) as res:
            print(f"送信成功 (Status: {res.status})")
    except Exception as e:
        print(f"Discord送信エラー: {e}")

def build_search_links(keyword):
    encoded = urllib.parse.quote(keyword)
    
    links = {
        "スクエニ e-STORE": f"https://store.jp.square-enix.com/item_list.html?keyword={encoded}",
        "あみあみ": f"https://slist.amiami.jp/top/search/list?s_keywords={encoded}&pagemax=30",
        "Amazon": f"https://www.amazon.co.jp/s?k={encoded}",
        "ビックカメラ": f"https://www.biccamera.com/bc/category/?q={encoded}",
        "ヨドバシカメラ": f"https://www.yodobashi.com/?word={encoded}",
        "Joshin web": f"https://joshinweb.jp/sitem/asp/search.jsp?keyword={encoded}"
    }
    
    body = f"🔍 **【{keyword}】** の巡回リンク\n"
    for name, url in links.items():
        body += f"・**{name}**: <{url}>\n"
    return body

def main():
    # ヘッダー送信
    send_discord("**【本日のドラクエメタリックシリーズ 巡回チェック】**")
    
    # キーワードごとに分けて送信（文字数オーバー対策）
    for kw in KEYWORDS:
        msg = build_search_links(kw)
        send_discord(msg)

if __name__ == "__main__":
    main()
