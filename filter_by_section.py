#!/usr/bin/env python3
"""
Script para filtrar artículos solo de secciones economia y politica
"""

import json
import csv

def filter_articles(articles, sections=['economia', 'politica']):
    """Filtra artículos por secciones específicas"""
    filtered = []
    for article in articles:
        url = article.get('url', '')
        parts = url.split('/')
        if len(parts) > 3:
            section = parts[3]
            if section in sections:
                filtered.append(article)
    return filtered

def main():
    print("="*60)
    print("FILTRANDO ARTÍCULOS POR SECCIÓN")
    print("="*60)
    
    # Cargar JSON
    input_file = 'infobae_uia_completo_fixed.json'
    print(f"\nCargando {input_file}...")
    
    with open(input_file, 'r', encoding='utf-8') as f:
        articles = json.load(f)
    
    print(f"Total artículos originales: {len(articles)}")
    
    # Filtrar solo economia y politica
    filtered = filter_articles(articles, sections=['economia', 'politica'])
    print(f"Artículos filtrados (economia + politica): {len(filtered)}")
    
    # Estadísticas por sección
    sections_count = {}
    for article in filtered:
        section = article['url'].split('/')[3]
        sections_count[section] = sections_count.get(section, 0) + 1
    
    print("\nDistribución:")
    for section, count in sorted(sections_count.items(), key=lambda x: x[1], reverse=True):
        print(f"  - {section}: {count} ({(count/len(filtered)*100):.1f}%)")
    
    # Guardar JSON filtrado
    output_json = 'infobae_uia_economia_politica.json'
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(filtered, f, ensure_ascii=False, indent=2)
    print(f"\n✓ JSON guardado: {output_json}")
    
    # Guardar CSV filtrado
    output_csv = 'infobae_uia_economia_politica.csv'
    if filtered:
        with open(output_csv, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=filtered[0].keys())
            writer.writeheader()
            writer.writerows(filtered)
        print(f"✓ CSV guardado: {output_csv}")
    
    # Mostrar ejemplos
    print("\n" + "="*60)
    print("PRIMEROS 5 ARTÍCULOS FILTRADOS:")
    print("="*60)
    for i, article in enumerate(filtered[:5], 1):
        url = article.get('url', '')
        section = url.split('/')[3] if len(url.split('/')) > 3 else 'N/A'
        print(f"\n{i}. [{section.upper()}] {article.get('title', 'Sin título')[:70]}")
        print(f"   Fecha: {article.get('date', 'N/A')}")
        print(f"   Body: {len(article.get('body', ''))} caracteres")

if __name__ == "__main__":
    main()
