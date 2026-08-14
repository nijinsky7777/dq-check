import os
import urllib.parse
import urllib.request
import json

# 設定
DISCORD_URL = os.environ.get("DISCORD_WEBHOOK_URL")
KEYWORD = "ドラゴンクエスト メタリックモンスターズギャラリー"

def send_discord(msg):
    if not DISCORD_URL:
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

def main():
    # 楽天の簡易検索（WEBページを直接検索する仕組み）
    encoded_keyword = urllib.parse.quote(KEYWORD)
    search_url = f"https://search.rakuten.co.jp/search/mall/{encoded_keyword}/"
    
    msg = f"**【本日のお知らせ】**\n『{KEYWORD}』のチェックが完了しました！\n最新の在庫・新商品一覧はこちらから確認できます：\n<{search_url}>"
    
    send_discord(msg)

if __name__ == "__main__":
    main()
