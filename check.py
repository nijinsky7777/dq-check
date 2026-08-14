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
    # 通常のUTF-8エンコード
    encoded_utf8 = urllib.parse.quote(keyword)
    
    # ビックカメラ用: Shift_JIS(CP932)エンコード
    encoded_sjis = urllib.parse.quote(keyword.encode('cp932', errors='ignore'))

    # 各サイトの修正URL一覧
    links = {
        # スクエニ: キーワード検索+リダイレクト回避のパラメータ
        "スクエニ e-STORE": f"https://store.jp.square-enix.com/item_list.html?x=0&y=0&keyword={encoded_utf8}",
        "あみあみ": f"https://slist.amiami.jp/top/search/list?s_keywords={encoded_utf8}&pagemax=30",
        "Amazon": f"https://www.amazon.co.jp/s?k={encoded_utf8}",
        "ビックカメラ": f"https://www.biccamera.com/bc/category/?q={encoded_sjis}",
        "ヨドバシカメラ": f"https://www.yodobashi.com/?word={encoded_utf8}",
        # Joshin: 直リンク拒否を回避するWeb検索用URL
        "Joshin web": f"https://joshinweb.jp/sitem/asp/spex.jsp?keyword={encoded_utf8}"
    }
    
    body = f"🔍 **【{keyword}】** の巡回リンク\n"
    for name, url in links.items():
        body += f"・**{name}**: <{url}>\n"
    return body

def main():
    # ヘッダー送信
    send_discord("**【本日のドラクエメタリックシリーズ 巡回チェック】**")
    
    # キーワードごとに分割して送信
    for kw in KEYWORDS:
        msg = build_search_links(kw)
        send_discord(msg)

if __name__ == "__main__":
    main()
