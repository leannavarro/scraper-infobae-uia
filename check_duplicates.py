"""
Script para verificar artículos duplicados
"""
import json

# Cargar los artículos
with open('infobae_uia_titulos.json', 'r', encoding='utf-8') as f:
    articles = json.load(f)

print(f"Total de artículos: {len(articles)}")

# Verificar por URL
urls = [article['url'] for article in articles]
unique_urls = set(urls)

print(f"URLs únicas: {len(unique_urls)}")
print(f"Duplicados: {len(urls) - len(unique_urls)}")

# Encontrar duplicados
if len(urls) != len(unique_urls):
    print("\n" + "="*60)
    print("ARTÍCULOS DUPLICADOS:")
    print("="*60)
    
    url_counts = {}
    for url in urls:
        url_counts[url] = url_counts.get(url, 0) + 1
    
    duplicates = {url: count for url, count in url_counts.items() if count > 1}
    
    for url, count in duplicates.items():
        print(f"\nURL repetida {count} veces:")
        print(f"  {url}")
        
        # Mostrar los títulos de los duplicados
        dup_articles = [a for a in articles if a['url'] == url]
        for i, art in enumerate(dup_articles, 1):
            print(f"  [{i}] Página: {art['page']}, Título: {art['title'][:80]}")

# Verificar por título
print("\n" + "="*60)
print("VERIFICACIÓN POR TÍTULO:")
print("="*60)

titles = [article['title'] for article in articles]
unique_titles = set(titles)

print(f"Títulos únicos: {len(unique_titles)}")
print(f"Títulos duplicados: {len(titles) - len(unique_titles)}")

# Estadísticas por página
print("\n" + "="*60)
print("ESTADÍSTICAS POR PÁGINA:")
print("="*60)

page_stats = {}
for article in articles:
    page = article['page']
    page_stats[page] = page_stats.get(page, 0) + 1

for page in sorted(page_stats.keys()):
    print(f"Página {page}: {page_stats[page]} artículos")
