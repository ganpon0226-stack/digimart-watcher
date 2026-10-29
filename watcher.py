from curl_cffi import requests
from bs4 import BeautifulSoup
import json
import os

TARGET_URL = "https://www.digimart.net/search?keyword=Tak+Matsumoto"
STATE_FILE = "notified_links.json"
WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

def fetch_digimart():
    try:
        # curl_cffiでChromeブラウザになりすましてCloudflareのブロックを突破する
        response = requests.get(TARGET_URL, impersonate="chrome", timeout=15)
        if response.status_code == 200:
            return response.text
        else:
            print(f"フェッチエラー: ステータスコード {response.status_code}")
            return None
    except Exception as e:
        print(f"フェッチエラー: {e}")
        return None

def parse_items(html):
    soup = BeautifulSoup(html, "html.parser")
    items = []
    
    blocks = soup.find_all("div", class_="itemSearchBlock")
    for block in blocks:
        title_tag = block.find("a", class_="itemTitle")
        if title_tag:
            title = title_tag.get_text(strip=True)
            link = title_tag.get("href")
            if link and not link.startswith("http"):
                link = "https://www.digimart.net" + link
            
            price_tag = block.find("p", class_="itemPrice")
            price = price_tag.get_text(strip=True) if price_tag else "価格不明"
            
            items.append({
                "title": title,
                "link": link,
                "price": price
            })
    return items

def load_notified_links():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []
    return []

def save_notified_links(links):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(links, f, ensure_ascii=False, indent=2)

def send_discord(new_items):
    if not WEBHOOK_URL:
        print("DISCORD_WEBHOOK_URLが設定されていません。")
        return
    
    for item in new_items:
        content = {
            "content": f"🎸 **【デジマート新着】Tak Matsumoto DC 関連**\n**商品名:** {item['title']}\n**価格:** {item['price']}\n🔗 {item['link']}"
        }
        data = json.dumps(content).encode("utf-8")
        req = requests.post(WEBHOOK_URL, json=content)
        if req.status_code != 204 and req.status_code != 200:
            print(f"Discord送信エラー: {req.status_code}")

def main():
    html = fetch_digimart()
    if not html:
        return
    
    items = parse_items(html)
    print(f"検出された商品数: {len(items)}件")
    
    if not items:
        print("商品は検出されませんでした。")
        return

    reversed_items = list(reversed(items))
    
    # 初回実行時（ファイルがない場合）は全件既読にして終了
    if not os.path.exists(STATE_FILE):
        all_links = [item['link'] for item in reversed_items]
        save_notified_links(all_links)
        print("【初期完了】現在の出品を既読として登録しました。次回から新着を通知します。")
        return

    notified_links = load_notified_links()
    new_items = []
    all_links = notified_links.copy()
    
    for item in reversed_items:
        if item['link'] not in notified_links:
            new_items.append(item)
            all_links.append(item['link'])
            
    if new_items:
        print(f"新着商品 {len(new_items)}件を検知しました！")
        send_discord(new_items)
        save_notified_links(all_links)
    else:
        print("新しい出品はありませんでした。")

if __name__ == "__main__":
    main()
