"""
Re-scraper de contenido completo para artículos de Infobae
Extrae body y fecha de artículos ya recopilados
"""

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import json
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
import csv

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BodyRescraper:
    """Re-scraper enfocado en extraer body y metadata"""
    
    def __init__(self, max_workers=3, delay=1.0, max_retries=3):
        self.max_workers = max_workers
        self.delay = delay
        self.max_retries = max_retries
        
    def _get_driver(self):
        """Crea driver de Selenium"""
        for attempt in range(self.max_retries):
            try:
                chrome_options = Options()
                chrome_options.add_argument('--headless=new')
                chrome_options.add_argument('--no-sandbox')
                chrome_options.add_argument('--disable-dev-shm-usage')
                chrome_options.add_argument('--disable-gpu')
                chrome_options.add_argument('--window-size=1920,1080')
                chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
                
                # Deshabilitar imágenes
                prefs = {'profile.managed_default_content_settings.images': 2}
                chrome_options.add_experimental_option('prefs', prefs)
                
                service = Service(ChromeDriverManager().install())
                driver = webdriver.Chrome(service=service, options=chrome_options)
                driver.set_page_load_timeout(30)
                
                return driver
            except Exception as e:
                logger.warning(f"Intento {attempt + 1}/{self.max_retries} falló: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(5)
                else:
                    raise
    
    def scrape_article_content(self, article_url):
        """Extrae contenido completo de un artículo con mejor parsing"""
        import re
        
        for attempt in range(self.max_retries):
            driver = None
            try:
                driver = self._get_driver()
                time.sleep(self.delay)
                
                driver.get(article_url)
                
                # Esperar a que cargue el contenido
                try:
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.TAG_NAME, "body"))
                    )
                    time.sleep(2)  # Tiempo adicional para JS
                except TimeoutException:
                    logger.warning(f"Timeout cargando {article_url}")
                
                page_source = driver.page_source
                soup = BeautifulSoup(page_source, 'html.parser')
                
                # Extraer título
                title = ''
                title_selectors = [
                    soup.find('h1'),
                    soup.find('h1', class_='article-title'),
                    soup.find('h1', {'itemprop': 'headline'}),
                ]
                for selector in title_selectors:
                    if selector:
                        title = selector.get_text(strip=True)
                        break
                
                # Extraer fecha - primero intentar desde la URL
                date = ''
                url_date_match = re.search(r'/(\d{4})/(\d{2})/(\d{2})/', article_url)
                if url_date_match:
                    year, month, day = url_date_match.groups()
                    date = f"{year}-{month}-{day}"
                else:
                    # Fallback: probar múltiples selectores en HTML
                    date_selectors = [
                        soup.find('time', {'datetime': True}),
                        soup.find('time'),
                        soup.find('span', class_='date'),
                        soup.find('div', class_='date'),
                        soup.find(attrs={'itemprop': 'datePublished'}),
                    ]
                    for selector in date_selectors:
                        if selector:
                            date = selector.get('datetime', selector.get_text(strip=True))
                            if date:
                                break
                
                # Extraer autor
                author = ''
                author_selectors = [
                    soup.find('span', class_='author'),
                    soup.find('a', class_='author'),
                    soup.find(attrs={'itemprop': 'author'}),
                    soup.find('div', class_='author'),
                ]
                for selector in author_selectors:
                    if selector:
                        author = selector.get_text(strip=True)
                        break
                
                # Extraer cuerpo del artículo - estrategia mejorada
                body_paragraphs = []
                
                # Estrategia 1: Buscar article tag
                article_tag = soup.find('article')
                if article_tag:
                    paragraphs = article_tag.find_all('p')
                    for p in paragraphs:
                        # Filtrar párrafos que no sean del artículo
                        p_class = ' '.join(p.get('class', [])).lower()
                        if any(x in p_class for x in ['author', 'date', 'share', 'social', 'tags', 'related']):
                            continue
                        
                        # CORRECCIÓN: usar separator=' ' para agregar espacios entre elementos
                        text = p.get_text(separator=' ', strip=True)
                        if len(text) > 30:  # Mínimo 30 caracteres
                            body_paragraphs.append(text)
                
                # Estrategia 2: Si no hay suficiente contenido, buscar en divs de contenido
                if len(body_paragraphs) < 3:
                    body_paragraphs = []
                    content_divs = soup.find_all('div', class_=lambda x: x and any(
                        term in str(x).lower() for term in ['content', 'body', 'article', 'story', 'texto']
                    ))
                    
                    for div in content_divs:
                        paragraphs = div.find_all('p')
                        for p in paragraphs:
                            p_class = ' '.join(p.get('class', [])).lower()
                            if any(x in p_class for x in ['author', 'date', 'share', 'social', 'tags', 'related']):
                                continue
                            
                            # CORRECCIÓN: usar separator=' ' para agregar espacios
                            text = p.get_text(separator=' ', strip=True)
                            if len(text) > 30:
                                if text not in body_paragraphs:  # Evitar duplicados
                                    body_paragraphs.append(text)
                
                # Estrategia 3: Si aún no hay contenido, buscar todos los <p>
                if len(body_paragraphs) < 3:
                    body_paragraphs = []
                    all_paragraphs = soup.find_all('p')
                    
                    for p in all_paragraphs:
                        # Filtrar por clase
                        p_class = ' '.join(p.get('class', [])).lower()
                        if any(x in p_class for x in ['author', 'date', 'share', 'social', 'tags', 'related', 'caption']):
                            continue
                        
                        # CORRECCIÓN: usar separator=' ' para agregar espacios
                        text = p.get_text(separator=' ', strip=True)
                        
                        # Saltar párrafos muy cortos o que parecen metadata
                        if len(text) < 30:
                            continue
                        
                        # Saltar si es solo una fecha o similar
                        if text.count(',') <= 1 and len(text) < 50 and any(c.isdigit() for c in text):
                            continue
                        
                        if text not in body_paragraphs:
                            body_paragraphs.append(text)
                
                body = '\n\n'.join(body_paragraphs)
                
                # Si no encontramos body, guardar HTML para debug
                if not body or len(body) < 100:
                    logger.warning(f"Poco contenido extraído de {article_url} ({len(body)} chars)")
                
                return {
                    'url': article_url,
                    'title': title,
                    'author': author,
                    'date': date,
                    'body': body,
                    'body_length': len(body),
                    'paragraphs_count': len(body_paragraphs),
                    'scraped_at': datetime.now().isoformat()
                }
                
            except Exception as e:
                logger.error(f"Error scrapeando '{article_url}' (intento {attempt + 1}/{self.max_retries}): {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(5)
            finally:
                if driver:
                    try:
                        driver.quit()
                    except:
                        pass
        
        return None
    
    def rescrape_articles(self, articles, start_index=0, checkpoint_file='rescrape_checkpoint.json'):
        """Re-scrapea contenido de artículos con progreso guardado"""
        full_articles = []
        
        # Cargar checkpoint si existe
        try:
            with open(checkpoint_file, 'r', encoding='utf-8') as f:
                checkpoint = json.load(f)
                full_articles = checkpoint['articles']
                start_index = checkpoint['last_index'] + 1
                logger.info(f"Reanudando desde artículo {start_index}")
        except:
            pass
        
        urls_to_scrape = [art['url'] for art in articles[start_index:]]
        total = len(urls_to_scrape)
        
        logger.info(f"Re-scrapeando contenido de {total} artículos (desde {start_index})")
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_url = {
                executor.submit(self.scrape_article_content, url): (i + start_index, url) 
                for i, url in enumerate(urls_to_scrape)
            }
            
            completed = 0
            for future in as_completed(future_to_url):
                index, url = future_to_url[future]
                try:
                    article = future.result()
                    if article:
                        full_articles.append(article)
                        completed += 1
                        
                        if completed % 10 == 0:
                            logger.info(f"Progreso: {completed}/{total} artículos ({(completed/total)*100:.1f}%)")
                            # Guardar checkpoint cada 10
                            with open(checkpoint_file, 'w', encoding='utf-8') as f:
                                json.dump({
                                    'articles': full_articles,
                                    'last_index': index,
                                    'timestamp': datetime.now().isoformat()
                                }, f, ensure_ascii=False, indent=2)
                        
                        # Guardar CSV cada 200 artículos
                        if completed % 200 == 0:
                            csv_filename = f'infobea_uia_partial_{completed}.csv'
                            import csv
                            if full_articles:
                                keys = full_articles[0].keys()
                                with open(csv_filename, 'w', encoding='utf-8', newline='') as f:
                                    writer = csv.DictWriter(f, fieldnames=keys)
                                    writer.writeheader()
                                    writer.writerows(full_articles)
                                logger.info(f"✓ CSV parcial guardado: {csv_filename}")
                except Exception as e:
                    logger.error(f"Error procesando {url}: {e}")
        
        logger.info(f"Re-scraping completado: {len(full_articles)} artículos con contenido")
        return full_articles


def main():
    """Re-scrapea el body de los artículos existentes"""
    
    print("=" * 60)
    print("RE-SCRAPER DE CONTENIDO COMPLETO - INFOBAE UIA")
    print("=" * 60)
    
    # Cargar artículos desde infobae_uia_titulos.json
    print("\nCargando artículos existentes...")
    with open('infobae_uia_titulos.json', 'r', encoding='utf-8') as f:
        articles = json.load(f)
    
    print(f"Total de artículos a procesar: {len(articles)}")
    
    # Crear rescraper
    rescraper = BodyRescraper(
        max_workers=5,
        delay=1.0,
        max_retries=3
    )
    
    # Re-scrapear contenido
    print("\nExtrayendo contenido completo...")
    print("Guardando progreso cada 10 artículos en 'rescrape_checkpoint.json'")
    print("Puede interrumpir con Ctrl+C y reanudar después\n")
    
    full_articles = rescraper.rescrape_articles(
        articles,
        checkpoint_file='rescrape_checkpoint.json'
    )
    
    # Guardar resultado final
    with open('infobae_uia_completo_fixed.json', 'w', encoding='utf-8') as f:
        json.dump(full_articles, f, ensure_ascii=False, indent=2)
    
    print(f"\n✓ Contenido completo extraído: {len(full_articles)} artículos")
    print(f"✓ Archivo guardado: infobae_uia_completo_fixed.json")
    
    # Estadísticas
    with_body = sum(1 for a in full_articles if len(a.get('body', '')) > 100)
    with_date = sum(1 for a in full_articles if a.get('date'))
    
    print(f"\nEstadísticas:")
    print(f"  - Artículos con body (>100 chars): {with_body}/{len(full_articles)}")
    print(f"  - Artículos con fecha: {with_date}/{len(full_articles)}")
    print("=" * 60)


if __name__ == "__main__":
    main()
