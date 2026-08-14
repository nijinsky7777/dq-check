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
DISCORD_LOG_URL = os.environ.get("DISCORD_WEBHOOK_URL_LOG") or DISCORD_URL
DATA_FILE = "data/prices.json"

WATCH_ITEMS = [
    {
        "keyword": "メタリックモンスターズギャラリー"
    },
    {
        "keyword": "メタリックアイテムズギャラリー"
    }
]

def load_price_history():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"履歴読み込みエラー: {e}")
    return {}

def save_price_history(data):
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"価格履歴を保存しました（件数: {len(data)}件）")
    except Exception as e:
        print(f"履歴保存エラー: {e}")

def send_discord(msg, target_url=None):
    url = target_url or DISCORD_URL
    if not url:
        print("Webhook URLが設定されていません")
        print(msg)
        return

    max_len = 1900
    chunks = [msg[i:i+max_len] for i in range(0, len(msg), max_len)]

    for chunk in chunks:
        req = urllib.request.Request(
            url,
            data=json.dumps({"content": chunk}).encode('utf-8'),
            headers={'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'}
        )
        try:
            with urllib.request.urlopen(req) as res:
                print(f"送信成功 (Status: {res.status})")
        except Exception as e:
            print(f"Discord送信エラー: {e}")
        time.sleep(1)

def send_price_list_text(price_history, target_url=None):
    if not price_history:
        send_discord("📊 **【現在の保存価格リスト】**\n現在保存されている価格データはありません。\n（※まだ一度も価格が正常に取得できていないか、初回実行中です）", target_url=target_url)
        return

    now_jst = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=9)
    date_str = now_jst.strftime('%Y年%m月%d日 %H:%M')
    
    header = f"📊 **【取得価格リスト ({date_str} 時点)】**\n```\n"
    footer = "\n```"
    
    lines = []
    for name, price in price_history.items():
        lines.append(f"{name}: {price:,}円")

    content_body = "\n".join(lines)
    full_message = header + content_body + footer

    if len(full_message) <= 1900:
        send_discord(full_message, target_url=target_url)
    else:
        send_discord(f"📊 **【取得価格リスト ({date_str} 時点)】**", target_url=target_url)
        chunk_lines = []
        for line in lines:
            chunk_lines.append(line)
            if len(chunk_lines) >= 15:
                send_discord("```\n" + "\n".join(chunk_lines) + "\n```", target_url=target_url)
                chunk_lines = []
        if chunk_lines:
            send_discord("```\n" + "\n".join(chunk_lines) + "\n```", target_url=target_url)

def sleep_random_delay(min_sec=3, max_sec=8):
    wait_time = random.uniform(min_sec, max_sec)
    print(f"[{wait_time:.1f}秒のアクセス分散待機中...]")
    time.sleep(wait_time)

def is_ignored(item_name):
    return False

def should_notify(old_price, new_price):
    if new_price is None or old_price is None:
        return False, ""
    
    price_diff = old_price - new_price
    
    if price_diff < 100:
        return False, ""

    drop_rate = (price_diff / old_price) * 100
    if drop_rate >= 5.0 or price_diff >= 1000:
        reason = f"📉 **【値下げ検知】** 前回より {price_diff:,}円ダウン（-{drop_rate:.1f}%）"
        return True, reason

    return False, ""

def fetch_html(url, headers=None):
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

def check_amiami(item_config, price_history):
    sleep_random_delay(2, 5)
    kw = item_config["keyword"]
    encoded_utf8 = urllib.parse.quote(kw)
    url = f"https://slist.amiami.jp/top/search/list?s_keywords={encoded_utf8}&pagemax=30"
    
    print(f"あみあみチェック中: {kw}")
    html = fetch_html(url)
    if not html:
        return

    soup = BeautifulSoup(html, 'html.parser')
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
            
            if is_ignored(name):
                continue
                
            store_key = f"[あみあみ] {name}"
            old_price = price_history.get(store_key)
            
            notify, reason = should_notify(old_price, price)
            if notify:
                msg = f"{reason}\n📦 **{store_key}**\n💰 価格: **{price:,}円**\n🔗 <{url}>"
                send_discord(msg, target_url=DISCORD_URL)

            price_history[store_key] = price

def check_amazon(item_config, price_history):
    sleep_random_delay(3, 7)
    kw = item_config["keyword"]
    encoded_utf8 = urllib.parse.quote(kw)
    url = f"https://www.amazon.co.jp/s?k={encoded_utf8}"
    
    print(f"Amazonチェック中: {kw}")
    html = fetch_html(url)
    if not html:
        return

    soup = BeautifulSoup(html, 'html.parser')
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
            
            store_key = f"[Amazon] {name}"
            old_price = price_history.get(store_key)
            
            notify, reason = should_notify(old_price, price)
            if notify:
                link_elem = title_elem.find('a')
                item_url = f"https://www.amazon.co.jp{link_elem['href']}" if link_elem and 'href' in link_elem.attrs else url
                msg = f"{reason}\n📦 **{store_key}**\n💰 価格: **{price:,}円**\n🔗 <{item_url}>"
                send_discord(msg, target_url=DISCORD_URL)

            price_history[store_key] = price

def check_biccamera(item_config, price_history):
    sleep_random_delay(3, 6)
    kw = item_config["keyword"]
    encoded_sjis = urllib.parse.quote(kw.encode('cp932', errors='ignore'))
    url = f"https://www.biccamera.com/bc/category/?q={encoded_sjis}"
    
    print(f"ビックカメラチェック中: {kw}")
    html = fetch_html(url)
    if not html:
        return

    soup = BeautifulSoup(html, 'html.parser')
    items = soup.find_all('div', class_=re.compile(r'bcs_box|bcs_listItem'))
    
    for item in items:
        title_elem = item.find('p', class_=re.compile(r'bcs_title')) or item.find('a', class_=re.compile(r'title'))
        price_elem = item.find('p', class_=re.compile(r'bcs_price')) or item.find('span', class_=re.compile(r'price'))
        
        if title_elem and price_elem:
            name = title_elem.text.strip()
            price_text = re.sub(r'[^\d]', '', price_elem.text)
            if not price_text:
                continue
            price = int(price_text)
            
            if is_ignored(name):
                continue
            
            link_elem = title_elem.find('a') if title_elem.name != 'a' else title_elem
            item_url = f"https://www.biccamera.com{link_elem['href']}" if link_elem and 'href' in link_elem.attrs else url
            
            store_key = f"[ビックカメラ] {name}"
            old_price = price_history.get(store_key)
            
            notify, reason = should_notify(old_price, price)
            if notify:
                msg = f"{reason}\n📦 **{store_key}**\n💰 価格: **{price:,}円**\n🔗 <{item_url}>"
                send_discord(msg, target_url=DISCORD_URL)

            price_history[store_key] = price

def check_sofmap(item_config, price_history):
    sleep_random_delay(3, 6)
    kw = item_config["keyword"]
    encoded_utf8 = urllib.parse.quote(kw)
    url = f"https://a.sofmap.com/search_result.aspx?gid=&keyword={encoded_utf8}"
    
    print(f"ソフマップチェック中: {kw}")
    html = fetch_html(url)
    if not html:
        return

    soup = BeautifulSoup(html, 'html.parser')
    items = soup.find_all('div', class_=re.compile(r'product_box|item_box|product_list_item'))
    
    for item in items:
        title_elem = item.find('p', class_=re.compile(r'name|title')) or item.find('a', class_=re.compile(r'name'))
        price_elem = item.find('p', class_=re.compile(r'price')) or item.find('span', class_=re.compile(r'price'))
        
        if title_elem and price_elem:
            name = title_elem.text.strip()
            price_text = re.sub(r'[^\d]', '', price_elem.text)
            if not price_text:
                continue
            price = int(price_text)
            
            if is_ignored(name):
                continue
            
            link_elem = title_elem.find('a') if title_elem.name != 'a' else title_elem
            item_url = f"https://a.sofmap.com{link_elem['href']}" if link_elem and 'href' in link_elem.attrs else url
            
            store_key = f"[ソフマップ] {name}"
            old_price = price_history.get(store_key)
            
            notify, reason = should_notify(old_price, price)
            if notify:
                msg = f"{reason}\n📦 **{store_key}**\n💰 価格: **{price:,}円**\n🔗 <{item_url}>"
                send_discord(msg, target_url=DISCORD_URL)

            price_history[store_key] = price

def send_daily_links():
    """1日1回送信する巡回リンク集（年月日表記 ＋ アイコン・プレビューが出ない形式）"""
    now_jst = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=9)
    date_str = now_jst.strftime('%Y年%m月%d日')
    
    send_discord(f"🔔 **【ドラクエメタリックシリーズ 本日の巡回リンク】**\n📅 配信日: **{date_str}**", target_url=DISCORD_URL)
    time.sleep(1)

    for item in WATCH_ITEMS:
        kw = item["keyword"]
        encoded_utf8 = urllib.parse.quote(kw)
        encoded_sjis = urllib.parse.quote(kw.encode('cp932', errors='ignore'))
        
        # <>で囲むことで、アイコンやプレビューカードの発生を完全に防ぎます
        lines = [
            f"🔍 **【{kw}】**",
            f"・あみあみ: <https://slist.amiami.jp/top/search/list?s_keywords={encoded_utf8}&pagemax=30>",
            f"・Amazon: <https://www.amazon.co.jp/s?k={encoded_utf8}>",
            f"・ビックカメラ: <https://www.biccamera.com/bc/category/?q={encoded_sjis}>",
            f"・ソフマップ: <https://a.sofmap.com/search_result.aspx?gid=&keyword={encoded_utf8}>",
            f"・ヨドバシカメラ: <https://www.yodobashi.com/?word={encoded_utf8}>"
        ]
        send_discord("\n".join(lines), target_url=DISCORD_URL)
        time.sleep(1)

    common_links = [
        "🏠 **【公式・その他ショップ】**",
        "・スクエニ e-STORE: <https://store.jp.square-enix.com/>",
        "・Joshin web: <https://joshinweb.jp/>"
    ]
    send_discord("\n".join(common_links), target_url=DISCORD_URL)

def main():
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    now_jst = now_utc + datetime.timedelta(hours=9)
    
    hour = now_jst.hour
    minute = now_jst.minute
    event_name = os.environ.get("GITHUB_EVENT_NAME", "")

    print(f"--- 実行開始 (JST: {now_jst.strftime('%Y-%m-%d %H:%M:%S')}) ---")

    is_manual_run = (event_name == "workflow_dispatch")
    is_daily_time = (hour == 7 and minute >= 30)

    if is_daily_time or is_manual_run:
        send_daily_links()

    is_amazon_time = (hour == 0) or (minute < 15) or is_manual_run
    is_retailer_time = (hour == 0 and minute < 15) or (hour % 4 == 0 and minute < 15) or is_manual_run

    price_history = load_price_history()

    for item_config in WATCH_ITEMS:
        if is_amazon_time:
            check_amazon(item_config, price_history)
            
        if is_retailer_time:
            check_amiami(item_config, price_history)
            check_biccamera(item_config, price_history)
            check_sofmap(item_config, price_history)

    save_price_history(price_history)

    if is_manual_run:
        send_price_list_text(price_history, target_url=DISCORD_LOG_URL)

if __name__ == "__main__":
    main()
