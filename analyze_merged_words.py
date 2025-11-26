#!/usr/bin/env python3
"""
Script para detectar y corregir palabras pegadas en el texto
"""

import json
import re

def find_merged_words(text):
    """Encuentra patrones de palabras pegadas sin espacios"""
    # Buscar palabras muy largas (probablemente pegadas)
    long_words = re.findall(r'\b[a-záéíóúñ]{20,}\b', text.lower())
    
    # Buscar patrones como "palabraPalabra" (minúscula seguida de mayúscula)
    camelcase = re.findall(r'[a-záéíóúñ]+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+', text)
    
    return long_words + camelcase

def analyze_text_issues(articles):
    """Analiza problemas en el texto de los artículos"""
    issues = []
    
    for i, article in enumerate(articles):
        body = article.get('body', '')
        title = article.get('title', '')[:80]
        
        merged = find_merged_words(body)
        if merged:
            issues.append({
                'index': i,
                'title': title,
                'url': article.get('url', ''),
                'merged_words': merged[:5]  # Primeras 5 palabras problemáticas
            })
    
    return issues

def main():
    print("="*60)
    print("ANÁLISIS DE PALABRAS PEGADAS")
    print("="*60)
    
    # Cargar JSON
    input_file = 'infobae_uia_economia_politica.json'
    print(f"\nCargando {input_file}...")
    
    with open(input_file, 'r', encoding='utf-8') as f:
        articles = json.load(f)
    
    print(f"Total artículos: {len(articles)}")
    
    # Analizar problemas
    print("\nBuscando palabras pegadas...")
    issues = analyze_text_issues(articles)
    
    print(f"\nArtículos con palabras pegadas: {len(issues)}/{len(articles)} ({(len(issues)/len(articles)*100):.1f}%)")
    
    if issues:
        print("\n" + "="*60)
        print("PRIMEROS 10 EJEMPLOS:")
        print("="*60)
        
        for i, issue in enumerate(issues[:10], 1):
            print(f"\n{i}. {issue['title']}")
            print(f"   Palabras pegadas encontradas:")
            for word in issue['merged_words']:
                print(f"     - {word}")
    
    # Guardar reporte detallado
    if issues:
        output_file = 'merged_words_report.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(issues, f, ensure_ascii=False, indent=2)
        print(f"\n✓ Reporte completo guardado: {output_file}")
    
    print("\n" + "="*60)
    print("RECOMENDACIÓN:")
    print("="*60)
    print("Este problema es común en el scraping de sitios con JavaScript.")
    print("Posibles causas:")
    print("  1. Elementos HTML sin espacios entre ellos")
    print("  2. Contenido generado dinámicamente mal formateado")
    print("  3. Extracción de texto sin considerar saltos de línea")
    print("\nPara corregir, se necesitaría:")
    print("  - Ajustar el parser para agregar espacios entre elementos HTML")
    print("  - Procesar el texto extraído con reglas de separación")

if __name__ == "__main__":
    main()
