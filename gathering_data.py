from bs4 import BeautifulSoup
import json
import requests

def remove_escape(text):
    return text.replace("\n", " ").replace("\r", " ").replace("\t", " ").strip()

# 블로그 URL
url = "https://d-knowledge.tistory.com/192"

response = requests.get(url)
response.encoding = 'utf-8'
html = response.text

soup = BeautifulSoup(html, "html.parser")

# 다양한 본문 후보
content = (
    soup.select_one("div.entry-content")
    or soup.select_one("div.contents_style")
    or soup.select_one("div.article_view")
    or soup.select_one("article")
)

result = {}

if content:
    tables = content.find_all("table")
    
    for table in tables:
        for row in table.find_all("tr"):
            cells = row.find_all("td")
            if len(cells) >= 2:
                material = cells[0].get_text(strip=True)
                items_text = cells[1].get_text(separator="\n", strip=True)
                items = [item.strip() for item in items_text.split("\n") if item.strip()]
                result[material] = items
    print("✅ 본문 안 table 구조로 데이터 추출 완료!")
else:
    print("❌ 본문을 찾지 못했습니다.")

# JSON 저장
with open("gathering_data.json", "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=4)

print("✅ 데이터 저장 완료: gathering_data.json")
