import os
import json
import urllib.parse
import urllib.request

DISCORD_URL = os.environ.get("DISCORD_WEBHOOK_URL")

# 監視したいキーワードリスト
KEYWORDS = [
    "メタリックモンスターズギャラリー",
    "メタリックアイテムズギャラリー"
]

def send_discord(msg):
    if not DISCORD_URL:
        print(msg)
        return
    req = urllib.request.Request(
        DISCORD_URL,
        data=json.dumps({"content": msg}).encode('utf-8'),
        headers={'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'}
    )
    try:
        urllib.request.urlopen(req)
    except Exception as e:
        print(f"送信失敗: {e}")

def build_search_links(keyword):
    encoded = urllib.parse.quote(keyword)
    
    # 各ショップの検索URL構築
    links = {
        "スクエニ e-STORE (公式定価)": f"https://store.jp.square-enix.com/item_list.html?keyword={encoded}",
        "あみあみ (定価・割引)": f"https://slist.amiami.jp/top/search/list?s_keywords={encoded}&pagemax=30",
        "Amazon (在庫・価格比較)": f"https://www.amazon.co.jp/s?k={encoded}",
        "ビックカメラ": f"https://www.biccamera.com/bc/category/?q={encoded}",
        "ヨドバシカメラ": f"https://www.yodobashi.com/?word={encoded}",
        "Joshin web": f"https://joshinweb.jp/sitem/asp/search.jsp?keyword={encoded}"
    }
    
    body = f"【🔍 **{keyword}** の巡回リンク】\n"
    for name, url in links.items():
        body += f"・**{name}**: <{url}>\n"
    return body

def main():
    message_parts = ["**【本日のドラクエメタリックシリーズ 巡回チェック】**\n"]
    
    for kw in KEYWORDS:
        message_parts.append(build_search_links(kw))
    
    message_parts.append("※あみあみ・スクエニ公式は定期的に予約再開・定価再販が行われます。リンクから即時在庫を確認できます！")
    
    full_message = "\n".join(message_parts)
    send_discord(full_message)

if __name__ == "__main__":
    main()
