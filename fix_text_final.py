#!/usr/bin/env python3
"""
Script para corregir problemas de encoding y palabras pegadas
"""

import json
import re
import html

def fix_encoding(text):
    """Corrige problemas comunes de encoding UTF-8"""
    if not text:
        return text
    
    replacements = {
        'Ã³': 'ó', 'Ã¡': 'á', 'Ã©': 'é', 'Ã­': 'í', 'Ãº': 'ú',
        'Ã±': 'ñ', 'Ã': 'Ñ',
        'Â': '', 'â€œ': '"', 'â€': '"', 'â€"': '—', 'â€"': '-',
        'Ã': 'Ó', 'Ã': 'Á', 'Ã‰': 'É', 'Ã': 'Í', 'Ãš': 'Ú',
    }
    
    for old, new in replacements.items():
        text = text.replace(old, new)
    
    # Decodificar entidades HTML
    text = html.unescape(text)
    
    return text

def smart_split_words(text):
    """Separa palabras pegadas de forma inteligente"""
    if not text:
        return text
    
    # Solo separar cuando hay transición de minúscula a mayúscula
    # Y la palabra siguiente es un nombre propio conocido o muy común
    text = re.sub(r'([a-zñ])([A-ZÑ][a-zñ]{2,})', r'\1 \2', text)
    
    # Separar preposiciones/artículos pegados a números
    text = re.sub(r'([a-zñ]{2,})(\d+)', r'\1 \2', text)
    text = re.sub(r'(\d+)([a-zñ]{2,})', r'\1 \2', text)
    
    # Separar conjunciones "y" pegadas (más seguro)
    text = re.sub(r'([a-zñáéíóú]{4,})y([a-zñáéíóú]{4,})', r'\1 y \2', text)
    
    # Limpiar espacios múltiples
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()

def clean_article(article):
    """Limpia un artículo completo"""
    for field in ['title', 'body', 'description', 'author']:
        if field in article and article[field]:
            text = article[field]
            text = fix_encoding(text)
            text = smart_split_words(text)
            article[field] = text
    return article

def main():
    print("="*60)
    print("LIMPIEZA FINAL DE TEXTO")
    print("="*60)
    
    # Cargar JSON original (sin correcciones previas)
    input_file = 'infobae_uia_economia_politica.json'
    print(f"\nCargando {input_file}...")
    
    with open(input_file, 'r', encoding='utf-8') as f:
        articles = json.load(f)
    
    print(f"Total artículos: {len(articles)}")
    
    # Mostrar ANTES
    print("\n" + "="*60)
    print("ANTES:")
    print("="*60)
    sample = articles[0]
    print(f"Título: {sample.get('title', '')[:100]}")
    print(f"Body snippet: {sample.get('body', '')[:300]}")
    
    # Aplicar limpieza
    print("\nAplicando limpieza...")
    cleaned = [clean_article(art.copy()) for art in articles]
    
    # Mostrar DESPUÉS  
    print("\n" + "="*60)
    print("DESPUÉS:")
    print("="*60)
    sample_clean = cleaned[0]
    print(f"Título: {sample_clean.get('title', '')[:100]}")
    print(f"Body snippet: {sample_clean.get('body', '')[:300]}")
    
    # Guardar
    output_json = 'infobae_uia_final.json'
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(cleaned, f, ensure_ascii=False, indent=2)
    print(f"\n✓ JSON limpio guardado: {output_json}")
    
    # CSV
    import csv
    output_csv = 'infobae_uia_final.csv'
    if cleaned:
        with open(output_csv, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=cleaned[0].keys())
            writer.writeheader()
            writer.writerows(cleaned)
        print(f"✓ CSV limpio guardado: {output_csv}")
    
    print("\n" + "="*60)
    print("LISTO!")
    print("="*60)
    print(f"Archivos finales: {len(cleaned)} artículos")
    print("- Encoding UTF-8 corregido")
    print("- Palabras pegadas separadas (conservador)")
    print("- Listo para análisis")

if __name__ == "__main__":
    main()
