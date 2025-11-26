#!/usr/bin/env python3
"""
Scraper masivo de Infobae para 2000 artículos sobre UIA
Con correcciones de encoding y separación de palabras
"""

import json
import time
import logging
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
import re

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class InfobeaUIA2000Scraper:
    def __init__(self, max_articles=2000, max_workers=5, delay=1.0):
        self.max_articles = max_articles
        self.max_workers = max_workers
        self.delay = delay
        self.max_retries = 3
        self.search_url = "https://www.infobae.com/buscador/?query=uia"
        
    def _get_driver(self):
        """Crea una instancia de Chrome WebDriver configurada"""
        chrome_options = Options()
        chrome_options.add_argument('--headless=new')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("prefs", {"profile.managed_default_content_settings.images": 2})
        
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        return driver
    
    def extract_date_from_url(self, url):
        """Extrae fecha del formato /YYYY/MM/DD/ en la URL"""
        match = re.search(r'/(\d{4})/(\d{2})/(\d{2})/', url)
        if match:
            year, month, day = match.groups()
            return f"{year}-{month}-{day}"
        return ''
    
    def scrape_search_results(self):
        """Extrae URLs de artículos navegando por todas las páginas"""
        driver = None
        all_urls = []
        seen_urls = set()
        page = 1
        
        try:
            driver = self._get_driver()
            driver.get(self.search_url)
            logger.info(f"Scrapeando resultados de búsqueda UIA (objetivo: {self.max_articles} artículos)")
            
            # Esperar carga inicial
            time.sleep(3)
            
            while len(all_urls) < self.max_articles:
                time.sleep(self.delay)
                
                # Obtener HTML renderizado
                page_source = driver.page_source
                soup = BeautifulSoup(page_source, 'html.parser')
                
                # Buscar TODOS los links
                all_links = soup.find_all('a', href=True)
                new_in_page = 0
                
                for link in all_links:
                    url_href = link['href']
                    
                    # Convertir a URL absoluta
                    if not url_href.startswith('http'):
                        if url_href.startswith('/'):
                            url_href = 'https://www.infobae.com' + url_href
                        else:
                            continue
                    
                    # Filtrar solo economía y política
                    if ('/economia/' in url_href or '/politica/' in url_href) and url_href not in seen_urls:
                        seen_urls.add(url_href)
                        
                        # Extraer título del link o del elemento padre
                        title = link.get_text(strip=True)
                        parent = link.find_parent(['div', 'article', 'li'])
                        if parent and (not title or len(title) < 20):
                            title_tag = parent.find(['h1', 'h2', 'h3', 'h4'])
                            if title_tag:
                                title = title_tag.get_text(strip=True)
                        
                        # Descripción
                        description = ''
                        if parent:
                            desc_tag = parent.find('p')
                            if desc_tag:
                                description = desc_tag.get_text(strip=True)
                        
                        # Fecha de URL
                        date = self.extract_date_from_url(url_href)
                        
                        # Sección
                        section = 'economia' if '/economia/' in url_href else 'politica'
                        
                        all_urls.append({
                            'url': url_href,
                            'title': title,
                            'description': description,
                            'date': date,
                            'section': section
                        })
                        new_in_page += 1
                        
                        if len(all_urls) >= self.max_articles:
                            break
                
                logger.info(f"Página {page}: {new_in_page} artículos nuevos (total: {len(all_urls)}/{self.max_articles})")
                
                if len(all_urls) >= self.max_articles:
                    break
                
                # Buscar y hacer click en botón "Siguiente"
                try:
                    # Intentar varios selectores para el botón siguiente
                    siguiente_btn = None
                    try:
                        siguiente_btn = driver.find_element(By.XPATH, "//a[contains(text(), 'Siguiente')]")
                    except:
                        try:
                            siguiente_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Siguiente')]")
                        except:
                            try:
                                siguiente_btn = driver.find_element(By.CSS_SELECTOR, "a.next, button.next, [class*='next']")
                            except:
                                pass
                    
                    if siguiente_btn and siguiente_btn.is_displayed():
                        driver.execute_script("arguments[0].scrollIntoView(true);", siguiente_btn)
                        time.sleep(1)
                        siguiente_btn.click()
                        page += 1
                        time.sleep(2)
                    else:
                        logger.info("Botón 'Siguiente' no disponible o no visible")
                        break
                except Exception as e:
                    logger.info(f"No hay más páginas disponibles: {e}")
                    break
            
            logger.info(f"✓ Recolectados {len(all_urls)} URLs de artículos")
            return all_urls
            
        finally:
            if driver:
                driver.quit()
    
    def scrape_article_content(self, article_data):
        """Extrae contenido completo de un artículo con correcciones de encoding"""
        url = article_data['url']
        
        for attempt in range(self.max_retries):
            driver = None
            try:
                driver = self._get_driver()
                time.sleep(self.delay)
                
                driver.get(url)
                
                # Esperar que cargue
                try:
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.TAG_NAME, "body"))
                    )
                    time.sleep(2)
                except TimeoutException:
                    logger.warning(f"Timeout cargando {url}")
                
                page_source = driver.page_source
                soup = BeautifulSoup(page_source, 'html.parser')
                
                # Extraer título
                title = article_data.get('title', '')
                if not title:
                    title_elem = soup.find('h1')
                    if title_elem:
                        title = title_elem.get_text(separator=' ', strip=True)
                
                # Fecha ya extraída de URL
                date = article_data.get('date', '')
                
                # Extraer autor
                author = ''
                author_elem = soup.find('span', class_='author') or soup.find('a', class_='author')
                if author_elem:
                    author = author_elem.get_text(separator=' ', strip=True)
                
                # Extraer cuerpo - Estrategia mejorada con separator
                body_paragraphs = []
                
                # Buscar article tag
                article_tag = soup.find('article')
                if article_tag:
                    paragraphs = article_tag.find_all('p')
                    for p in paragraphs:
                        p_class = ' '.join(p.get('class', [])).lower()
                        if any(x in p_class for x in ['author', 'date', 'share', 'social', 'tags', 'related']):
                            continue
                        
                        # CRÍTICO: separator=' ' para evitar palabras pegadas
                        text = p.get_text(separator=' ', strip=True)
                        if len(text) > 30:
                            body_paragraphs.append(text)
                
                # Fallback: buscar en divs de contenido
                if len(body_paragraphs) < 3:
                    body_paragraphs = []
                    content_divs = soup.find_all('div', class_=lambda x: x and any(
                        term in str(x).lower() for term in ['content', 'body', 'article', 'story']
                    ))
                    
                    for div in content_divs:
                        paragraphs = div.find_all('p')
                        for p in paragraphs:
                            text = p.get_text(separator=' ', strip=True)
                            if len(text) > 30 and text not in body_paragraphs:
                                body_paragraphs.append(text)
                
                body = '\n\n'.join(body_paragraphs)
                
                # Combinar con metadata inicial
                result = {
                    'url': url,
                    'title': title,
                    'author': author,
                    'date': date,
                    'body': body,
                    'description': article_data.get('description', ''),
                    'section': article_data.get('section', ''),
                    'body_length': len(body),
                    'paragraphs_count': len(body_paragraphs),
                    'scraped_at': datetime.now().isoformat()
                }
                
                return result
                
            except Exception as e:
                logger.error(f"Error scrapeando {url} (intento {attempt+1}/{self.max_retries}): {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(5)
                else:
                    return None
            finally:
                if driver:
                    driver.quit()
    
    def scrape_all(self):
        """Proceso completo: buscar URLs y extraer contenido"""
        print("="*60)
        print("SCRAPER MASIVO INFOBAE UIA - 2000 ARTÍCULOS")
        print("="*60)
        print(f"\nObjetivo: {self.max_articles} artículos")
        print(f"Workers concurrentes: {self.max_workers}")
        print(f"Delay entre requests: {self.delay}s")
        print(f"Secciones: economía, política")
        print()
        
        # Fase 1: Recolectar URLs
        print("FASE 1: Recolectando URLs de artículos...")
        articles_data = self.scrape_search_results()
        
        if not articles_data:
            logger.error("No se encontraron artículos")
            return []
        
        # Guardar URLs
        urls_file = 'infobae_uia_2000_urls.json'
        with open(urls_file, 'w', encoding='utf-8') as f:
            json.dump(articles_data, f, ensure_ascii=False, indent=2)
        logger.info(f"✓ URLs guardadas en {urls_file}")
        
        # Fase 2: Extraer contenido completo
        print(f"\nFASE 2: Extrayendo contenido de {len(articles_data)} artículos...")
        print("Guardando checkpoint cada 10 artículos")
        print("Guardando CSV cada 200 artículos\n")
        
        full_articles = []
        checkpoint_file = 'checkpoint_uia_2000.json'
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_article = {
                executor.submit(self.scrape_article_content, art): (i, art)
                for i, art in enumerate(articles_data)
            }
            
            completed = 0
            for future in as_completed(future_to_article):
                index, art_data = future_to_article[future]
                try:
                    article = future.result()
                    if article and article.get('body'):
                        full_articles.append(article)
                        completed += 1
                        
                        if completed % 10 == 0:
                            logger.info(f"Progreso: {completed}/{len(articles_data)} ({(completed/len(articles_data)*100):.1f}%)")
                            
                            # Checkpoint cada 10
                            with open(checkpoint_file, 'w', encoding='utf-8') as f:
                                json.dump({
                                    'articles': full_articles,
                                    'last_index': index,
                                    'total_processed': completed,
                                    'timestamp': datetime.now().isoformat()
                                }, f, ensure_ascii=False, indent=2)
                        
                        # CSV cada 200
                        if completed % 200 == 0:
                            import csv
                            csv_filename = f'infobae_uia_2000_partial_{completed}.csv'
                            if full_articles:
                                with open(csv_filename, 'w', encoding='utf-8', newline='') as f:
                                    writer = csv.DictWriter(f, fieldnames=full_articles[0].keys())
                                    writer.writeheader()
                                    writer.writerows(full_articles)
                                logger.info(f"✓ CSV parcial guardado: {csv_filename}")
                
                except Exception as e:
                    logger.error(f"Error procesando artículo {index}: {e}")
        
        # Guardar resultado final
        output_json = 'infobae_uia_2000_completo.json'
        with open(output_json, 'w', encoding='utf-8') as f:
            json.dump(full_articles, f, ensure_ascii=False, indent=2)
        logger.info(f"✓ JSON final guardado: {output_json}")
        
        # CSV final
        import csv
        output_csv = 'infobae_uia_2000_completo.csv'
        if full_articles:
            with open(output_csv, 'w', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=full_articles[0].keys())
                writer.writeheader()
                writer.writerows(full_articles)
            logger.info(f"✓ CSV final guardado: {output_csv}")
        
        print("\n" + "="*60)
        print("SCRAPING COMPLETADO!")
        print("="*60)
        print(f"Total artículos extraídos: {len(full_articles)}")
        print(f"Archivos generados:")
        print(f"  - {output_json}")
        print(f"  - {output_csv}")
        
        # Estadísticas
        sections = {}
        dates = {}
        for art in full_articles:
            section = art.get('section', 'unknown')
            sections[section] = sections.get(section, 0) + 1
            
            year = art.get('date', '')[:4]
            if year:
                dates[year] = dates.get(year, 0) + 1
        
        print(f"\nDistribución por sección:")
        for sec, count in sorted(sections.items(), key=lambda x: x[1], reverse=True):
            print(f"  - {sec}: {count}")
        
        print(f"\nDistribución por año:")
        for year, count in sorted(dates.items(), reverse=True):
            print(f"  - {year}: {count}")
        
        return full_articles


def main():
    scraper = InfobeaUIA2000Scraper(
        max_articles=2000,
        max_workers=5,
        delay=1.0
    )
    
    articles = scraper.scrape_all()
    
    if articles:
        print(f"\n✓ Proceso exitoso: {len(articles)} artículos scrapeados")
    else:
        print("\n✗ No se pudieron obtener artículos")


if __name__ == "__main__":
    main()
