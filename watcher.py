import os
import json
import urllib.request
import urllib.parse
import re

DISCORD_WEBHOOK_URL = os.environ.get('DISCORD_WEBHOOK_URL')
TARGET_URL = "https://www.digimart.net/search?category1Id=13&keywordAnd=Tak+Matsumoto+DC&sftk=1&sortKey=DISP_DATE_DESC"
STATE_FILE = "notified_links.json"

def load_notified_links():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return []
    return []

def save_notified_links(links):
    # 最大100件まで保持
    if len(links) > 100:
        links = links[-100:]
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(links, f, ensure_ascii=False, indent=2)

def fetch_digimart():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    req = urllib.request.Request(TARGET_URL, headers=headers)
    try:
        with urllib.request.urlopen(req) as response:
            return response.read().decode("utf-8")
    except Exception as e:
        print(f"フェッチエラー: {e}")
        return None

def parse_items(html):
    items = []
    item_blocks = html.split('<div class="itemSearchBlock')
    
    for i in range(1, len(item_blocks)):
        block = item_blocks[i]
        
        title_match = re.search(r'<p class="ttl">\s*<a href="([^"]+)"[^>]*>([\s\S]*?)<\/a>', block)
        price_match = re.search(r'<span[^>]*class="price"[^>]*>([\s\S]*?)<\/span>', block, re.IGNORECASE)
        shop_match = re.search(r'class="itemShopInfo"[\s\S]*?>([\s\S]*?)<\/p>', block, re.IGNORECASE)
        
        if title_match:
            link = "https://www.digimart.net" + title_match.group(1).strip()
            title = re.sub(r'<[^>]+>', '', title_match.group(2)).replace(' ', ' ').strip()
            price = re.sub(r'<[^>]+>', '', price_match.group(1)).strip() if price_match else "価格不明"
            shop = re.sub(r'<[^>]+>', '', shop_match.group(1)).strip() if shop_match else "店舗不明"
            
            if link not in [item['link'] for item in items]:
                items.append({'title': title, 'link': link, 'price': price, 'shop': shop})
                
    return items

def send_discord(new_items):
    content = f"🎸 【デジマート新着情報】 Tak Matsumoto DC が **{len(new_items)}件** 出品されました！\n\n"
    for i, item in enumerate(new_items):
        content += f"{i + 1}. **{item['title']}**\n"
        content += f"💰 価格: {item['price']} | 🏪 店舗: {item['shop']}\n"
        content += f"🔗 {item['link']}\n\n"
        
    payload = json.dumps({"content": content}).encode("utf-8")
    req = urllib.request.Request(
        DISCORD_WEBHOOK_URL,
        data=payload,
        headers={"Content-Type": "application/json"}
    )
    urllib.request.urlopen(req)

def main():
    html = fetch_digimart()
    if not html:
        return
        
    items = parse_items(html)
    if not items:
        print("商品は検出されませんでした。")
        return
        
    print(f"検出された商品数: {len(items)}件")
    
    # notified_links = load_notified_links()
    # reversed_items = list(reversed(items))

    send_discord(items)
    print("テスト通知を送信しました。")
    return
    
    # 初回実行時（ファイルがない場合）は全件既読にして通知しない
    if not os.path.exists(STATE_FILE):
        all_links = [item['link'] for item in reversed_items]
        save_notified_links(all_links)
        print("【初期化完了】現在の出品を既読として登録しました。")
        return
        
    new_items = []
    all_links = notified_links.copy()
    for item in reversed_items:
        if item['link'] not in notified_links:
            new_items.append(item)
            all_links.append(item['link'])
            
    if new_items:
        send_discord(new_items)
        save_notified_links(all_links)
        print(f"新着 {len(new_items)} 件を通知しました。")
    else:
        print("新しい出品はありませんでした。")

if __name__ == "__main__":
    main()
