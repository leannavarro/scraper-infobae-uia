"""
Convertir archivos JSON de Infobae a CSV
"""
import json
import csv
import sys

def json_to_csv(json_file, csv_file=None):
    """Convierte un archivo JSON a CSV"""
    
    if csv_file is None:
        csv_file = json_file.replace('.json', '.csv')
    
    # Leer JSON
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    if not data:
        print(f"⚠️ El archivo {json_file} está vacío")
        return
    
    # Obtener todas las claves posibles
    all_keys = set()
    for item in data:
        all_keys.update(item.keys())
    
    fieldnames = sorted(all_keys)
    
    # Escribir CSV
    with open(csv_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)
    
    print(f"✓ Convertido: {json_file} -> {csv_file}")
    print(f"  Registros: {len(data)}")
    print(f"  Columnas: {len(fieldnames)}")
    return csv_file


if __name__ == "__main__":
    if len(sys.argv) > 1:
        json_file = sys.argv[1]
        csv_file = sys.argv[2] if len(sys.argv) > 2 else None
        json_to_csv(json_file, csv_file)
    else:
        # Convertir todos los archivos JSON disponibles
        print("Convirtiendo todos los archivos JSON a CSV...\n")
        
        import os
        json_files = [f for f in os.listdir('.') if f.endswith('.json') and 'checkpoint' not in f]
        
        for json_file in json_files:
            json_to_csv(json_file)
            print()
