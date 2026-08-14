import os
import re
import json
import time
import random
import datetime
import urllib.parse
import urllib.request
from bs4 import BeautifulSoup

DISCORD_URL = os.environ.get("DISCORD_WEBHOOK_URL")

# 監視対象アイテムの設定（商品キーワードと定価 MSRP）
# 定価(msrp)を設定しておくことで「プレ値からの定価復帰」を正確に判定します
WATCH_ITEMS = [
    {
        "keyword": "メタリックモンスターズギャラリー",
        "msrp": 9000  # 定価の目安（個別の定価判定にも使用）
    },
    {
        "keyword": "メタリックアイテムズギャラリー",
        "msrp": 4500
    }
]

# ---------------------------------------------------------
# 1. 共通・通知・判定ロジック
# ---------------------------------------------------------

def send_discord(msg):
    """Discordへの通知送信"""
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

def sleep_random_delay(min_sec=3, max_sec=8):
    """Bot判定（BAN）を回避するため、アクセス時間をランダムに分散"""
    wait_time = random.uniform(min_sec, max_sec)
    print(f"[{wait_time:.1f}秒のアクセス分散待機中...]")
    time.sleep(wait_time)

def is_ignored(item_name):
    """【後日実装用】購入済み・通知不要リスト"""
    return False

def should_notify(old_price, new_price, msrp):
    """
    【パターンB】定価復帰 ＋ 5% / 1000円以上値下げ判定
    """
    if new_price is None:
        return False, ""
    
    # 1. 【最優先】プレ値（定価オーバー）から「定価以下」になった瞬間を検知
    if new_price <= msrp:
        if old_price is None or old_price > msrp:
            reason = f"🚨 **【定価復帰/定価以下入荷】**\n定価（{msrp:,}円）以下での販売を検知しました！"
            return True, reason

    # 2. 初回取得時（かつ定価より高い状態）なら保存のみで通知なし
    if old_price is None:
        return False, ""
    
    price_diff = old_price - new_price
    
    # 100円未満の微変動や値上がりは無視
    if price_diff < 100:
        return False, ""

    # 3. 通常の値下がり判定（5%以上 または 1000円以上）
    drop_rate = (price_diff / old_price) * 100
    if drop_rate >= 5.0 or price_diff >= 1000:
        reason = f"📉 **【値下げ検知】** {price_diff:,}円ダウン（-{drop_rate:.1f}%）"
        return True, reason

    return False, ""

# ---------------------------------------------------------
# 2. Webスクレイピング処理 (あみあみ & Amazon)
# ---------------------------------------------------------

def fetch_html(url, headers=None):
    """HTTPリクエスト共通処理"""
    if headers is None:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept-Language': 'ja,en-US;q=0.9,en;q=0.8'
        }
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as res:
            return res.read().decode('utf-8', errors='ignore')
    except Exception as e:
        print(f"取得エラー ({url}): {e}")
        return None

def check_amiami(item_config):
    """あみあみの検索・価格チェック"""
    sleep_random_delay(2, 5)
    kw = item_config["keyword"]
    msrp = item_config["msrp"]
    encoded_utf8 = urllib.parse.quote(kw)
    url = f"https://slist.amiami.jp/top/search/list?s_keywords={encoded_utf8}&pagemax=30"
    
    print(f"あみあみチェック中: {kw}")
    html = fetch_html(url)
    if not html:
        return

    soup = BeautifulSoup(html, 'html.parser')
    # あみあみの商品カード要素を抽出
    items = soup.find_all('li', class_=re.compile(r'product|item'))
    
    for item in items:
        name_elem = item.find(class_=re.compile(r'name|title'))
        price_elem = item.find(class_=re.compile(r'price'))
        
        if name_elem and price_elem:
            name = name_elem.text.strip()
            price_text = re.sub(r'[^\d]', '', price_elem.text)
            if not price_text:
                continue
            price = int(price_text)
            
            # 購入済みチェック
            if is_ignored(name):
                continue
                
            # TODO: 本来はデータベース/JSONファイルから前回価格(old_price)を呼び出す
            old_price = None  
            
            notify, reason = should_notify(old_price, price, msrp)
            if notify:
                msg = f"{reason}\n📦 **{name}**\n💰 価格: **{price:,}円**\n🔗 <{url}>"
                send_discord(msg)

def check_amazon(item_config):
    """Amazonの検索・価格チェック"""
    sleep_random_delay(3, 7)
    kw = item_config["keyword"]
    msrp = item_config["msrp"]
    encoded_utf8 = urllib.parse.quote(kw)
    url = f"https://www.amazon.co.jp/s?k={encoded_utf8}"
    
    print(f"Amazonチェック中: {kw}")
    html = fetch_html(url)
    if not html:
        return

    soup = BeautifulSoup(html, 'html.parser')
    # Amazon検索結果のカード要素
    items = soup.find_all('div', {'data-component-type': 's-search-result'})
    
    for item in items:
        title_elem = item.find('h2')
        price_whole = item.find('span', class_='a-price-whole')
        
        if title_elem and price_whole:
            name = title_elem.text.strip()
            price_text = re.sub(r'[^\d]', '', price_whole.text)
            if not price_text:
                continue
            price = int(price_text)
            
            if is_ignored(name):
                continue
            
            old_price = None  # DB等から取得する前回価格
            
            notify, reason = should_notify(old_price, price, msrp)
            if notify:
                link_elem = title_elem.find('a')
                item_url = f"https://www.amazon.co.jp{link_elem['href']}" if link_elem and 'href' in link_elem.attrs else url
                msg = f"{reason}\n📦 **{name}**\n💰 価格: **{price:,}円**\n🔗 <{item_url}>"
                send_discord(msg)

# ---------------------------------------------------------
# 3. スケジュール制御 ＆ メイン実行
# ---------------------------------------------------------

def send_daily_links():
    """1日1回送信する巡回リンク集"""
    message_parts = ["**【本日のドラクエメタリックシリーズ 巡回チェック】**\n"]
    for item in WATCH_ITEMS:
        kw = item["keyword"]
        encoded_utf8 = urllib.parse.quote(kw)
        encoded_sjis = urllib.parse.quote(kw.encode('cp932', errors='ignore'))
        links = [
            f"・[あみあみ](<https://slist.amiami.jp/top/search/list?s_keywords={encoded_utf8}&pagemax=30>)",
            f"・[Amazon](<https://www.amazon.co.jp/s?k={encoded_utf8}>)",
            f"・[ビックカメラ](<https://www.biccamera.com/bc/category/?q={encoded_sjis}>)",
            f"・[ヨドバシカメラ](<https://www.yodobashi.com/?word={encoded_utf8}>)"
        ]
        message_parts.append(f"🔍 **【{kw}】**\n" + "\n".join(links))
    
    common_links = [
        "\n🏠 **【トップページ（直検索不可サイト）】**",
        "・[スクエニ e-STORE](<https://store.jp.square-enix.com/>)",
        "・[Joshin web](<https://joshinweb.jp/>)"
    ]
    message_parts.append("\n".join(common_links))
    send_discord("\n\n".join(message_parts))

def main():
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    now_jst = now_utc + datetime.timedelta(hours=9)
    
    hour = now_jst.hour
    minute = now_jst.minute
    event_name = os.environ.get("GITHUB_EVENT_NAME", "")

    print(f"--- 実行開始 (JST: {now_jst.strftime('%Y-%m-%d %H:%M:%S')}) ---")

    # 朝7:50枠または手動実行時は巡回リンク集を送信
    if (hour == 7 and minute >= 30) or event_name == "workflow_dispatch":
        send_daily_links()

    # スケジュール制御（0時台高頻度 / 日中分散）
    is_amazon_time = (hour == 0) or (minute < 15) or (event_name == "workflow_dispatch")
    is_retailer_time = (hour == 0 and minute < 15) or (hour % 4 == 0 and minute < 15) or (event_name == "workflow_dispatch")

    for item_config in WATCH_ITEMS:
        if is_amazon_time:
            check_amazon(item_config)
            
        if is_retailer_time:
            check_amiami(item_config)

if __name__ == "__main__":
    main()
