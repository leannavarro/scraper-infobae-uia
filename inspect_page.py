"""
Script de inspección para ver la estructura HTML de Infobae
"""
import requests
from bs4 import BeautifulSoup

url = "https://www.infobae.com/buscador/?query=uia"
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

response = requests.get(url, headers=headers)
soup = BeautifulSoup(response.content, 'html.parser')

# Guardar el HTML para inspección
with open('infobae_search_page.html', 'w', encoding='utf-8') as f:
    f.write(soup.prettify())

print("HTML guardado en infobae_search_page.html")

# Buscar patrones comunes
print("\n=== Artículos (article tags) ===")
articles = soup.find_all('article')
print(f"Encontrados: {len(articles)}")
for i, art in enumerate(articles[:3], 1):
    print(f"\n{i}. Clases: {art.get('class')}")
    links = art.find_all('a', href=True)
    if links:
        print(f"   Link: {links[0]['href'][:100]}")
    titles = art.find_all(['h1', 'h2', 'h3'])
    if titles:
        print(f"   Título: {titles[0].get_text(strip=True)[:100]}")

print("\n=== Divs con clases relacionadas ===")
divs = soup.find_all('div', class_=True)
relevant_divs = [d for d in divs if any(keyword in ' '.join(d.get('class', [])).lower() 
                                         for keyword in ['story', 'card', 'result', 'article', 'item', 'search'])]
print(f"Encontrados: {len(relevant_divs)}")
for i, div in enumerate(relevant_divs[:5], 1):
    print(f"\n{i}. Clases: {div.get('class')}")
    links = div.find_all('a', href=True)
    if links:
        print(f"   Link: {links[0]['href'][:100]}")

print("\n=== Links que contienen /economia/ ===")
economia_links = soup.find_all('a', href=lambda x: x and '/economia/' in x)
print(f"Encontrados: {len(economia_links)}")
for i, link in enumerate(economia_links[:10], 1):
    print(f"\n{i}. URL: {link['href']}")
    print(f"   Texto: {link.get_text(strip=True)[:100]}")
