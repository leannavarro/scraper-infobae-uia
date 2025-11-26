#!/usr/bin/env python3
"""
Script para corregir palabras pegadas en el JSON existente
usando expresiones regulares para separar patrones comunes
"""

import json
import re

def fix_merged_words(text):
    """Corrige palabras pegadas usando patrones comunes"""
    if not text:
        return text
    
    # Patrón 1: minúscula seguida de mayúscula sin espacio
    # Ejemplos: "presidenteJavier" -> "presidente Javier"
    text = re.sub(r'([a-záéíóúñ])([A-ZÁÉÍÓÚÑ])', r'\1 \2', text)
    
    # Patrón 2: letra seguida de número sin espacio
    # Ejemplos: "artículo15" -> "artículo 15"
    text = re.sub(r'([a-záéíóúñA-ZÁÉÍÓÚÑ])(\d)', r'\1 \2', text)
    
    # Patrón 3: número seguido de letra sin espacio
    # Ejemplos: "15artículos" -> "15 artículos"
    text = re.sub(r'(\d)([a-záéíóúñA-ZÁÉÍÓÚÑ])', r'\1 \2', text)
    
    # Patrón 4: preposiciones comunes pegadas (minúsculas)
    # Ejemplos: "investigacionespor" -> "investigaciones por"
    text = re.sub(r'([a-záéíóúñ]{4,})(por|para|con|sin|sobre|entre|desde|hasta|hacia|bajo|ante|tras|durante)([a-záéíóúñ])', r'\1 \2 \3', text)
    
    # Patrón 5: verbos/palabras comunes pegadas al final
    # Ejemplos: "queavanzar" -> "que avanzar", "cualanaliza" -> "cual analiza"
    text = re.sub(r'([a-záéíóúñ]{3,})(que|cual|donde|cuando|como|pero|porque|aunque|mientras|hasta)([a-záéíóúñ]{3,})', r'\1 \2 \3', text)
    
    # Patrón 6: preposiciones con mayúscula siguiente
    # Ejemplos: "aUnión" -> "a Unión", "delConsejo" -> "del Consejo"
    text = re.sub(r'\b(a|de|del|al|con|por|para|entre|sobre|desde|hasta)([A-ZÁÉÍÓÚÑ])', r'\1 \2', text)
    
    # Patrón 7: artículos pegados
    # Ejemplos: "laUnión" -> "la Unión", "elPapa" -> "el Papa"
    text = re.sub(r'\b(el|la|los|las|un|una|unos|unas)([A-ZÁÉÍÓÚÑ])', r'\1 \2', text)
    
    # Patrón 8: conjunciones pegadas
    # Ejemplos: "empresay" -> "empresa y", "importacionesy" -> "importaciones y"
    text = re.sub(r'([a-záéíóúñ]{3,})(y|e|o|u|ni)([a-záéíóúñ]{3,})', r'\1 \2 \3', text)
    
    # Patrón 9: verbos auxiliares pegados
    # Ejemplos: "debeser" -> "debe ser", "puedehaber" -> "puede haber"
    text = re.sub(r'([a-záéíóúñ]{4,})(ser|estar|haber|tener|hacer|poder|deber|ir|venir|dar|ver|saber|decir)([a-záéíóúñ]{3,})', r'\1 \2 \3', text)
    
    # Limpiar espacios múltiples
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()

def fix_articles(articles):
    """Corrige palabras pegadas en todos los artículos"""
    fixed_count = 0
    
    for article in articles:
        # Corregir título
        old_title = article.get('title', '')
        new_title = fix_merged_words(old_title)
        if old_title != new_title:
            article['title'] = new_title
            fixed_count += 1
        
        # Corregir cuerpo
        old_body = article.get('body', '')
        new_body = fix_merged_words(old_body)
        if old_body != new_body:
            article['body'] = new_body
            fixed_count += 1
        
        # Corregir descripción
        old_desc = article.get('description', '')
        new_desc = fix_merged_words(old_desc)
        if old_desc != new_desc:
            article['description'] = new_desc
    
    return articles, fixed_count

def main():
    print("="*60)
    print("CORRECCIÓN DE PALABRAS PEGADAS")
    print("="*60)
    
    # Cargar JSON
    input_file = 'infobae_uia_economia_politica.json'
    print(f"\nCargando {input_file}...")
    
    with open(input_file, 'r', encoding='utf-8') as f:
        articles = json.load(f)
    
    print(f"Total artículos: {len(articles)}")
    
    # Mostrar ejemplos ANTES
    print("\n" + "="*60)
    print("ANTES (primer artículo):")
    print("="*60)
    sample = articles[0]
    body_preview = sample.get('body', '')[:500]
    print(f"Título: {sample.get('title', '')[:100]}")
    print(f"Body (primeros 500 chars):\n{body_preview}")
    
    # Corregir
    print("\nAplicando correcciones...")
    articles, fixed_count = fix_articles(articles)
    print(f"Correcciones aplicadas: {fixed_count}")
    
    # Mostrar ejemplos DESPUÉS
    print("\n" + "="*60)
    print("DESPUÉS (mismo artículo):")
    print("="*60)
    sample_after = articles[0]
    body_preview_after = sample_after.get('body', '')[:500]
    print(f"Título: {sample_after.get('title', '')[:100]}")
    print(f"Body (primeros 500 chars):\n{body_preview_after}")
    
    # Guardar JSON corregido
    output_json = 'infobae_uia_economia_politica_fixed.json'
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)
    print(f"\n✓ JSON corregido guardado: {output_json}")
    
    # Guardar CSV corregido
    import csv
    output_csv = 'infobae_uia_economia_politica_fixed.csv'
    if articles:
        with open(output_csv, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=articles[0].keys())
            writer.writeheader()
            writer.writerows(articles)
        print(f"✓ CSV corregido guardado: {output_csv}")
    
    print("\n" + "="*60)
    print("NOTA:")
    print("="*60)
    print("Las correcciones se basaron en patrones regex comunes.")
    print("Puede haber casos específicos que necesiten ajuste manual.")
    print("El scraper actualizado (rescrape_bodies.py) ya previene")
    print("este problema usando separator=' ' en get_text().")

if __name__ == "__main__":
    main()
