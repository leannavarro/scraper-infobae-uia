#!/usr/bin/env python3
"""
Script para extraer fechas de las URLs y actualizar el JSON existente
"""

import json
import re
from datetime import datetime

def extract_date_from_url(url):
    """Extrae la fecha desde el patrón /YYYY/MM/DD/ en la URL"""
    match = re.search(r'/(\d{4})/(\d{2})/(\d{2})/', url)
    if match:
        year, month, day = match.groups()
        return f"{year}-{month}-{day}"
    return ''

def main():
    print("="*60)
    print("EXTRAYENDO FECHAS DESDE URLs")
    print("="*60)
    
    # Cargar JSON existente
    input_file = 'infobae_uia_completo_fixed.json'
    print(f"\nCargando {input_file}...")
    
    with open(input_file, 'r', encoding='utf-8') as f:
        articles = json.load(f)
    
    print(f"Total artículos: {len(articles)}")
    
    # Actualizar fechas
    updated_count = 0
    for article in articles:
        url = article.get('url', '')
        current_date = article.get('date', '')
        
        # Solo actualizar si no tiene fecha o está vacía
        if not current_date or current_date.strip() == '':
            extracted_date = extract_date_from_url(url)
            if extracted_date:
                article['date'] = extracted_date
                updated_count += 1
    
    print(f"\nFechas actualizadas: {updated_count}")
    
    # Guardar archivo actualizado
    output_file = 'infobae_uia_completo_fixed.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)
    
    print(f"✓ Archivo guardado: {output_file}")
    
    # Mostrar ejemplos
    print("\n" + "="*60)
    print("PRIMEROS 5 ARTÍCULOS CON FECHAS:")
    print("="*60)
    for i, article in enumerate(articles[:5], 1):
        print(f"\n{i}. {article.get('title', 'Sin título')[:80]}")
        print(f"   URL: {article.get('url', '')[:80]}...")
        print(f"   Fecha: {article.get('date', 'N/A')}")
        print(f"   Body length: {len(article.get('body', ''))} caracteres")
    
    # Estadísticas
    with_date = sum(1 for a in articles if a.get('date') and a.get('date').strip())
    without_date = len(articles) - with_date
    
    print("\n" + "="*60)
    print("ESTADÍSTICAS:")
    print("="*60)
    print(f"Con fecha: {with_date} ({(with_date/len(articles)*100):.1f}%)")
    print(f"Sin fecha: {without_date} ({(without_date/len(articles)*100):.1f}%)")

if __name__ == "__main__":
    main()
