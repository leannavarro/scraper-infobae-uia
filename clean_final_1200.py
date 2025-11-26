#!/usr/bin/env python3
"""
Script para corregir DEFINITIVAMENTE el encoding del archivo de 1356 artículos
"""

import json
import re
import html
import unicodedata

def fix_encoding_complete(text):
    """Corrección exhaustiva de encoding UTF-8 mal interpretado"""
    if not text:
        return text
    
    # Diccionario completo de reemplazos de encoding mal interpretado
    replacements = {
        # Vocales acentuadas
        'Ã³': 'ó', 'Ã¡': 'á', 'Ã©': 'é', 'Ã­': 'í', 'Ãº': 'ú',
        'Ã"': 'Ó', 'Ã': 'Á', 'Ã‰': 'É', 'Ã': 'Í', 'Ãš': 'Ú',
        
        # Ñ
        'Ã±': 'ñ', 'Ã': 'Ñ',
        
        # Símbolos especiales
        'Â°': '°', 'Â': '', 'Âª': 'ª', 'Âº': 'º',
        
        # Comillas y guiones
        'â€œ': '"', 'â€': '"', 'â€˜': "'", 'â€™': "'",
        'â€"': '—', 'â€"': '-', 'â€¦': '...',
        
        # Otros caracteres
        'Ã¼': 'ü', 'Ã¶': 'ö', 'Ã¤': 'ä',
        'Ã‡': 'Ç', 'Ã§': 'ç',
    }
    
    # Aplicar reemplazos
    for old, new in replacements.items():
        text = text.replace(old, new)
    
    # Decodificar entidades HTML
    text = html.unescape(text)
    
    # Normalizar unicode
    text = unicodedata.normalize('NFC', text)
    
    # Limpiar espacios múltiples
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()

def smart_word_separation(text):
    """Separa palabras pegadas inteligentemente"""
    if not text:
        return text
    
    # Separar minúscula + Mayúscula (nombres propios)
    text = re.sub(r'([a-zñáéíóúü])([A-ZÑÁÉÍÓÚÜ][a-zñáéíóúü]+)', r'\1 \2', text)
    
    # Separar números y letras
    text = re.sub(r'([a-zñáéíóúü])(\d)', r'\1 \2', text)
    text = re.sub(r'(\d)([a-zñáéíóúü])', r'\1 \2', text)
    
    # Separar conjunción "y" pegada (muy común)
    text = re.sub(r'([a-zñáéíóúü]{4,})y([a-zñáéíóúü]{4,})', r'\1 y \2', text)
    
    # Limpiar espacios múltiples
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()

def clean_article_complete(article):
    """Limpia completamente un artículo"""
    fields = ['title', 'body', 'description', 'author']
    
    for field in fields:
        if field in article and article[field]:
            # Paso 1: Corregir encoding
            text = fix_encoding_complete(article[field])
            # Paso 2: Separar palabras pegadas
            text = smart_word_separation(text)
            article[field] = text
    
    return article

def main():
    print("="*60)
    print("CORRECCIÓN DEFINITIVA - 1356 ARTÍCULOS")
    print("="*60)
    
    # Cargar archivo con más artículos
    input_file = 'infobae_uia_completo_fixed.json'
    print(f"\nCargando {input_file}...")
    
    with open(input_file, 'r', encoding='utf-8') as f:
        articles = json.load(f)
    
    print(f"Total artículos: {len(articles)}")
    
    # Filtrar solo economía y política
    filtered = [a for a in articles if a.get('url', '').split('/')[3] in ['economia', 'politica']]
    print(f"Filtrados (economia + politica): {len(filtered)}")
    
    # Mostrar ANTES
    print("\n" + "="*60)
    print("ANTES:")
    print("="*60)
    sample = filtered[0]
    print(f"Título: {sample.get('title', '')[:100]}")
    print(f"Body: {sample.get('body', '')[:300]}")
    
    # Limpiar
    print("\nAplicando corrección profunda...")
    cleaned = [clean_article_complete(art.copy()) for art in filtered]
    
    # Mostrar DESPUÉS
    print("\n" + "="*60)
    print("DESPUÉS:")
    print("="*60)
    sample_clean = cleaned[0]
    print(f"Título: {sample_clean.get('title', '')[:100]}")
    print(f"Body: {sample_clean.get('body', '')[:300]}")
    
    # Guardar JSON
    output_json = 'infobae_uia_1200_limpio.json'
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(cleaned, f, ensure_ascii=False, indent=2)
    print(f"\n✓ JSON guardado: {output_json} ({len(cleaned)} artículos)")
    
    # Guardar CSV
    import csv
    output_csv = 'infobae_uia_1200_limpio.csv'
    if cleaned:
        with open(output_csv, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=cleaned[0].keys())
            writer.writeheader()
            writer.writerows(cleaned)
        print(f"✓ CSV guardado: {output_csv}")
    
    # Estadísticas
    sections = {}
    dates = {}
    for art in cleaned:
        section = art.get('section', art.get('url', '').split('/')[3] if len(art.get('url', '').split('/')) > 3 else 'unknown')
        sections[section] = sections.get(section, 0) + 1
        
        year = art.get('date', '')[:4]
        if year and year.isdigit():
            dates[year] = dates.get(year, 0) + 1
    
    print("\n" + "="*60)
    print("ESTADÍSTICAS:")
    print("="*60)
    print(f"Total: {len(cleaned)} artículos")
    print("\nPor sección:")
    for sec, count in sorted(sections.items(), key=lambda x: x[1], reverse=True):
        print(f"  - {sec}: {count}")
    
    print("\nPor año:")
    for year, count in sorted(dates.items(), reverse=True):
        print(f"  - {year}: {count}")
    
    print("\n" + "="*60)
    print("✓ DATASET FINAL LISTO")
    print("="*60)

if __name__ == "__main__":
    main()
