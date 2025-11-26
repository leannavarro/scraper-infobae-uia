"""
Script para monitorear el progreso del scraping
"""
import json
import os
import time
from datetime import datetime

def monitor_progress():
    """Monitorea el progreso del scraping"""
    print("=" * 60)
    print("MONITOR DE PROGRESO - SCRAPER INFOBAE")
    print("=" * 60)
    print("\nPresiona Ctrl+C para detener el monitoreo\n")
    
    last_count_titulos = 0
    last_count_completo = 0
    start_time = datetime.now()
    
    try:
        while True:
            os.system('cls' if os.name == 'nt' else 'clear')
            
            print("=" * 60)
            print("MONITOR DE PROGRESO - SCRAPER INFOBAE")
            print("=" * 60)
            
            # Tiempo transcurrido
            elapsed = datetime.now() - start_time
            hours, remainder = divmod(elapsed.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            print(f"\nTiempo transcurrido: {hours:02d}:{minutes:02d}:{seconds:02d}")
            
            # Verificar archivo de títulos
            if os.path.exists('infobae_uia_titulos.json'):
                try:
                    with open('infobae_uia_titulos.json', 'r', encoding='utf-8') as f:
                        titulos = json.load(f)
                        count_titulos = len(titulos)
                        
                        if count_titulos != last_count_titulos:
                            last_count_titulos = count_titulos
                        
                        print(f"\n📰 FASE 1 - Títulos y Links:")
                        print(f"   Artículos extraídos: {count_titulos}")
                        print(f"   Objetivo: 2000")
                        
                        if count_titulos > 0:
                            progress = (count_titulos / 2000) * 100
                            bar_length = 40
                            filled = int(bar_length * count_titulos / 2000)
                            bar = '█' * filled + '░' * (bar_length - filled)
                            print(f"   Progreso: [{bar}] {progress:.1f}%")
                        
                        # Páginas scrapeadas
                        if titulos:
                            pages = set(a.get('page', 0) for a in titulos)
                            print(f"   Páginas scrapeadas: {max(pages) if pages else 0}")
                except:
                    pass
            else:
                print(f"\n📰 FASE 1 - Títulos y Links:")
                print(f"   Esperando inicio...")
            
            # Verificar archivo completo
            if os.path.exists('infobae_uia_completo.json'):
                try:
                    with open('infobae_uia_completo.json', 'r', encoding='utf-8') as f:
                        completo = json.load(f)
                        count_completo = len(completo)
                        
                        if count_completo != last_count_completo:
                            last_count_completo = count_completo
                        
                        print(f"\n📄 FASE 2 - Contenido Completo:")
                        print(f"   Artículos con cuerpo: {count_completo}")
                        
                        if last_count_titulos > 0:
                            objetivo = last_count_titulos
                            progress = (count_completo / objetivo) * 100
                            bar_length = 40
                            filled = int(bar_length * count_completo / objetivo)
                            bar = '█' * filled + '░' * (bar_length - filled)
                            print(f"   Progreso: [{bar}] {progress:.1f}%")
                            
                            # Estimar tiempo restante
                            if count_completo > 0 and elapsed.seconds > 0:
                                rate = count_completo / elapsed.seconds  # artículos por segundo
                                remaining = objetivo - count_completo
                                eta_seconds = remaining / rate if rate > 0 else 0
                                eta_hours, eta_remainder = divmod(int(eta_seconds), 3600)
                                eta_minutes, eta_seconds = divmod(eta_remainder, 60)
                                print(f"   Tiempo estimado restante: {eta_hours:02d}:{eta_minutes:02d}:{eta_seconds:02d}")
                except:
                    pass
            else:
                print(f"\n📄 FASE 2 - Contenido Completo:")
                print(f"   Esperando inicio...")
            
            print("\n" + "=" * 60)
            print("Actualizando cada 5 segundos... (Ctrl+C para salir)")
            
            time.sleep(5)
            
    except KeyboardInterrupt:
        print("\n\n✓ Monitoreo detenido")
        print(f"Última actualización:")
        print(f"  - Títulos: {last_count_titulos}")
        print(f"  - Contenido completo: {last_count_completo}")

if __name__ == "__main__":
    monitor_progress()
