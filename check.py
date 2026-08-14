import os
import json
import datetime
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

def send_daily_links():
    """1日1回送信する巡回リンク集"""
    send_discord("**【本日のドラクエメタリックシリーズ 巡回チェック】**")
    for kw in KEYWORDS:
        encoded_utf8 = urllib.parse.quote(kw)
        encoded_sjis = urllib.parse.quote(kw.encode('cp932', errors='ignore'))
        
        links = [
            f"・[あみあみ (在庫・割引)](https://slist.amiami.jp/top/search/list?s_keywords={encoded_utf8}&pagemax=30)",
            f"・[Amazon (価格比較)](https://www.amazon.co.jp/s?k={encoded_utf8})",
            f"・[ビックカメラ](https://www.biccamera.com/bc/category/?q={encoded_sjis})",
            f"・[ヨドバシカメラ](https://www.yodobashi.com/?word={encoded_utf8})",
            f"・[スクエニ e-STORE (公式TOP)](https://store.jp.square-enix.com/)",
            f"・[Joshin web (公式TOP)](https://joshinweb.jp/)"
        ]
        msg = f"🔍 **【{kw}】** の巡回リンク\n" + "\n".join(links)
        send_discord(msg)

def check_stock_and_notify():
    """30分おきの自動検知用（新商品・再入荷などの検知処理）"""
    pass

def main():
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    now_jst = now_utc + datetime.timedelta(hours=9)
    
    event_name = os.environ.get("GITHUB_EVENT_NAME", "")
    
    # 日本時間 7:30〜7:59の枠（朝7時台の後半実行）または手動実行時にリンク送信
    is_morning_link_time = (now_jst.hour == 7 and now_jst.minute >= 30)
    
    if is_morning_link_time or event_name == "workflow_dispatch":
        send_daily_links()
    
    # 自動検知チェック（毎回実行）
    check_stock_and_notify()

if __name__ == "__main__":
    main()
