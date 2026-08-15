import os
import time
import datetime
import urllib.parse
import urllib.request
import json

DISCORD_URL = os.environ.get("DISCORD_WEBHOOK_URL")

WATCH_ITEMS = [
    "メタリックモンスターズギャラリー",
    "メタリックアイテムズギャラリー"
]

def send_discord(msg):
    if not DISCORD_URL:
        print("Webhook URLが設定されていません")
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
    time.sleep(1)

def main():
    now_jst = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=9)
    date_str = now_jst.strftime('%Y年%m月%d日')
    
    send_discord(f"🔔 **【ドラクエメタリックシリーズ 本日の巡回リンク】**\n📅 配信日: **{date_str}**")
    time.sleep(1)

    for kw in WATCH_ITEMS:
        # Amazon・あみあみ・ヨドバシ用のエンコード (UTF-8)
        encoded_utf8 = urllib.parse.quote(kw)
        
        # ビックカメラ・ソフマップ用のエンコード (Shift_JIS)
        # ※ errors='replace' で安全に変換し文字化けを防止します
        encoded_sjis = urllib.parse.quote(kw.encode('shift_jis', errors='replace'))
        
        lines = [
            f"**【{kw}】**",
            f"・[あみあみ](<https://slist.amiami.jp/top/search/list?s_keywords={encoded_utf8}&pagemax=30>)",
            f"・[Amazon](<https://www.amazon.co.jp/s?k={encoded_utf8}>)",
            f"・[ビックカメラ](<https://www.biccamera.com/bc/category/?q={encoded_sjis}>)",
            f"・[ヨドバシカメラ](<https://www.yodobashi.com/?word={encoded_utf8}>)",
            f"・[ソフマップ](<https://www.sofmap.com/search_result.aspx?keyword={encoded_sjis}>)"
        ]
        send_discord("\n".join(lines))
        time.sleep(1)

    common_links = [
        "**【トップページ（直検索不可サイト）】**",
        "・[スクエニ e-STORE](<https://store.jp.square-enix.com/>)",
        "・[Joshin web](<https://joshinweb.jp/>)"
    ]
    send_discord("\n".join(common_links))
    time.sleep(1)

    # もしリポジトリに「retail_prices.txt」という価格メモファイルがあれば、一緒に送信する
    price_file_path = "retail_prices.txt"
    if os.path.exists(price_file_path):
        try:
            with open(price_file_path, "r", encoding="utf-8") as f:
                content = f.read()
            send_discord(f"📋 **【定価・価格メモ】**\n```\n{content}\n```")
        except Exception as e:
            print(f"価格表読み込みエラー: {e}")

if __name__ == "__main__":
    print("巡回リンクの送信を開始します...")
    main()
    print("完了しました。")
