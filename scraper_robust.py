"""
Scraper masivo de Infobae - Versión Robusta con Reintentos
Extrae noticias relacionadas con UIA (Unión Industrial Argentina)
Incluye: reintentos automáticos, guardado incremental, recuperación de errores
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
import csv
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from urllib.parse import urljoin, urlencode
import logging
import re
import os

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RobustInfobaeScraper:
    """Scraper robusto para Infobae con manejo de errores y reintentos"""
    
    def __init__(self, max_workers=3, delay=1.0, headless=True, max_retries=3):
        """
        Args:
            max_workers: Número de hilos concurrentes
            delay: Delay entre requests (en segundos)
            headless: Si True, ejecuta Chrome sin interfaz gráfica
            max_retries: Número máximo de reintentos ante errores
        """
        self.base_url = "https://www.infobae.com"
        self.search_url = "https://www.infobae.com/buscador/"
        self.max_workers = max_workers
        self.delay = delay
        self.headless = headless
        self.max_retries = max_retries
        self.articles = []
        
    def _get_driver(self):
        """Crea y configura un driver de Selenium con reintentos"""
        for attempt in range(self.max_retries):
            try:
                chrome_options = Options()
                
                if self.headless:
                    chrome_options.add_argument('--headless=new')
                
                chrome_options.add_argument('--no-sandbox')
                chrome_options.add_argument('--disable-dev-shm-usage')
                chrome_options.add_argument('--disable-gpu')
                chrome_options.add_argument('--window-size=1920,1080')
                chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
                
                # Deshabilitar imágenes para acelerar
                prefs = {'profile.managed_default_content_settings.images': 2}
                chrome_options.add_experimental_option('prefs', prefs)
                
                service = Service(ChromeDriverManager().install())
                driver = webdriver.Chrome(service=service, options=chrome_options)
                driver.set_page_load_timeout(30)
                
                return driver
            except Exception as e:
                logger.warning(f"Intento {attempt + 1}/{self.max_retries} de crear driver falló: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(5)
                else:
                    raise
    
    def save_checkpoint(self, articles, page, filename='checkpoint.json'):
        """Guarda el progreso actual"""
        checkpoint = {
            'page': page,
            'articles': articles,
            'timestamp': datetime.now().isoformat(),
            'total': len(articles)
        }
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(checkpoint, f, ensure_ascii=False, indent=2)
        logger.info(f"✓ Checkpoint guardado: página {page}, {len(articles)} artículos")
    
    def load_checkpoint(self, filename='checkpoint.json'):
        """Carga el progreso guardado si existe"""
        if os.path.exists(filename):
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    checkpoint = json.load(f)
                logger.info(f"✓ Checkpoint cargado: página {checkpoint['page']}, {len(checkpoint['articles'])} artículos")
                return checkpoint
            except Exception as e:
                logger.error(f"Error cargando checkpoint: {e}")
        return None
    
    def scrape_search_results(self, query, max_pages=5, resume=True, checkpoint_file='checkpoint.json'):
        """
        Scrape resultados de búsqueda con soporte de reintentos y recuperación
        
        Args:
            query: Término de búsqueda
            max_pages: Número máximo de páginas a scrapear
            resume: Si True, intenta reanudar desde checkpoint
            checkpoint_file: Archivo para guardar progreso
            
        Returns:
            Lista de artículos
        """
        all_articles = []
        seen_urls = set()
        start_page = 1
        driver = None
        
        # Cargar checkpoint si existe
        if resume:
            checkpoint = self.load_checkpoint(checkpoint_file)
            if checkpoint:
                all_articles = checkpoint['articles']
                start_page = checkpoint['page'] + 1
                seen_urls = {art['url'] for art in all_articles}
                logger.info(f"Reanudando desde página {start_page} con {len(all_articles)} artículos previos")
        
        try:
            logger.info(f"Iniciando búsqueda de '{query}' - máximo {max_pages} páginas")
            driver = self._get_driver()
            
            # Cargar la primera página
            params = {'query': query}
            url = f"{self.search_url}?{urlencode(params)}"
            logger.info(f"Cargando página inicial: {url}")
            driver.get(url)
            
            # Esperar a que se cargue
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                time.sleep(2)
            except TimeoutException:
                logger.warning("Timeout esperando contenido inicial")
            
            # Si estamos reanudando, navegar hasta la página correcta
            if start_page > 1:
                logger.info(f"Navegando hasta página {start_page}...")
                for _ in range(1, start_page):
                    try:
                        next_button = driver.find_element(By.XPATH, "//a[contains(text(), 'Siguiente')]")
                        next_button.click()
                        time.sleep(2)
                    except:
                        logger.error("No se pudo navegar a la página de inicio")
                        break
            
            # Bucle principal de scraping
            for page in range(start_page, max_pages + 1):
                retry_count = 0
                page_success = False
                
                while retry_count < self.max_retries and not page_success:
                    try:
                        time.sleep(self.delay)
                        logger.info(f"Scrapeando página {page}")
                        
                        # Obtener HTML renderizado
                        page_source = driver.page_source
                        soup = BeautifulSoup(page_source, 'html.parser')
                        
                        # Buscar links de artículos
                        all_links = soup.find_all('a', href=True)
                        page_articles = []
                        page_seen_urls = set()
                        
                        for link in all_links:
                            url_href = link['href']
                            if not url_href.startswith('http'):
                                url_href = urljoin(self.base_url, url_href)
                            
                            # Filtrar artículos válidos
                            if (url_href.startswith('https://www.infobae.com/') and 
                                any(section in url_href for section in ['/economia/', '/politica/', '/sociedad/', '/america/', '/deportes/', '/tecno/', '/cultura/', '/salud/', '/el-mundo/']) and
                                url_href not in seen_urls and
                                url_href not in page_seen_urls and
                                '/fotos/' not in url_href and
                                '/buscador/' not in url_href):
                                
                                # Buscar contenedor padre
                                parent = link.find_parent(['article', 'div', 'li'])
                                if parent:
                                    # Extraer título
                                    title = ''
                                    title_tag = parent.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'span'])
                                    if title_tag:
                                        title = title_tag.get_text(strip=True)
                                    
                                    if not title or len(title) < 20:
                                        title = link.get_text(strip=True)
                                    
                                    if not title or len(title) < 20:
                                        continue
                                    
                                    # Extraer descripción
                                    description = ''
                                    desc_tag = parent.find(['p', 'div'], class_=re.compile(r'(description|summary|deck|excerpt)', re.I))
                                    if desc_tag:
                                        description = desc_tag.get_text(strip=True)
                                    
                                    # Extraer fecha
                                    date = ''
                                    date_tag = parent.find('time')
                                    if date_tag:
                                        date = date_tag.get('datetime', date_tag.get_text(strip=True))
                                    
                                    article_info = {
                                        'title': title,
                                        'url': url_href,
                                        'description': description,
                                        'date': date,
                                        'search_query': query,
                                        'page': page,
                                        'scraped_at': datetime.now().isoformat()
                                    }
                                    
                                    page_articles.append(article_info)
                                    page_seen_urls.add(url_href)
                        
                        # Agregar artículos de esta página
                        all_articles.extend(page_articles)
                        seen_urls.update(page_seen_urls)
                        
                        logger.info(f"✓ Página {page} completada: {len(page_articles)} artículos únicos extraídos")
                        page_success = True
                        
                        # Guardar checkpoint cada 5 páginas
                        if page % 5 == 0:
                            self.save_checkpoint(all_articles, page, checkpoint_file)
                        
                        if len(page_articles) == 0:
                            logger.info(f"No se encontraron artículos nuevos. Deteniendo en página {page}")
                            break
                        
                    except Exception as e:
                        retry_count += 1
                        logger.error(f"Error en página {page} (intento {retry_count}/{self.max_retries}): {e}")
                        
                        if retry_count < self.max_retries:
                            logger.info("Reintentando en 10 segundos...")
                            if driver:
                                try:
                                    driver.quit()
                                except:
                                    pass
                            time.sleep(10)
                            
                            # Recrear driver y recargar
                            driver = self._get_driver()
                            params = {'query': query}
                            url = f"{self.search_url}?{urlencode(params)}"
                            driver.get(url)
                            time.sleep(2)
                            
                            # Navegar hasta la página actual
                            for _ in range(1, page):
                                try:
                                    next_button = driver.find_element(By.XPATH, "//a[contains(text(), 'Siguiente')]")
                                    next_button.click()
                                    time.sleep(2)
                                except:
                                    break
                        else:
                            logger.error(f"Máximo de reintentos alcanzado para página {page}")
                            self.save_checkpoint(all_articles, page - 1, checkpoint_file)
                            break
                
                if not page_success:
                    logger.error(f"No se pudo completar página {page}")
                    break
                
                # Intentar ir a la siguiente página
                if page < max_pages:
                    next_success = False
                    for nav_attempt in range(self.max_retries):
                        try:
                            # Verificar que el driver sigue activo
                            driver.current_url  # Test de conexión
                            
                            next_button = driver.find_element(By.XPATH, "//a[contains(text(), 'Siguiente') or contains(text(), 'siguiente')]")
                            driver.execute_script("arguments[0].scrollIntoView();", next_button)
                            time.sleep(1)
                            next_button.click()
                            logger.info(f"Navegando a página {page + 1}")
                            time.sleep(2)
                            next_success = True
                            break
                        except (WebDriverException, ConnectionResetError, ConnectionError) as e:
                            logger.warning(f"Error de conexión navegando a página {page + 1} (intento {nav_attempt + 1}/{self.max_retries}): {e}")
                            if nav_attempt < self.max_retries - 1:
                                logger.info("Recreando driver...")
                                try:
                                    driver.quit()
                                except:
                                    pass
                                time.sleep(5)
                                driver = self._get_driver()
                                # Recargar y navegar hasta la página actual
                                params = {'query': query}
                                url = f"{self.search_url}?{urlencode(params)}"
                                driver.get(url)
                                time.sleep(2)
                                for _ in range(page):
                                    try:
                                        nb = driver.find_element(By.XPATH, "//a[contains(text(), 'Siguiente')]")
                                        nb.click()
                                        time.sleep(2)
                                    except:
                                        pass
                            else:
                                logger.error(f"No se pudo navegar a página {page + 1}")
                        except Exception as e:
                            logger.error(f"Error haciendo click en 'Siguiente': {e}")
                            break
                    
                    if not next_success:
                        break
            
            self.articles = all_articles
            logger.info(f"✓ Total de artículos extraídos: {len(all_articles)}")
            
            # Guardar checkpoint final
            if all_articles:
                self.save_checkpoint(all_articles, page, checkpoint_file)
            
            return all_articles
            
        finally:
            if driver:
                driver.quit()
                logger.info("Driver de Selenium cerrado")
    
    def scrape_article_body(self, article_url):
        """Extrae el cuerpo completo de un artículo con reintentos"""
        for attempt in range(self.max_retries):
            driver = None
            try:
                driver = self._get_driver()
                time.sleep(self.delay)
                
                driver.get(article_url)
                
                try:
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.TAG_NAME, "article"))
                    )
                except TimeoutException:
                    pass
                
                time.sleep(1)
                page_source = driver.page_source
                soup = BeautifulSoup(page_source, 'html.parser')
                
                # Título
                title_tag = soup.find('h1')
                title = title_tag.get_text(strip=True) if title_tag else ''
                
                # Fecha
                date_tag = soup.find('time')
                date = date_tag.get('datetime', '') if date_tag else ''
                
                # Autor
                author_tag = soup.find(['span', 'a'], class_=re.compile(r'(author|autor)', re.I))
                author = author_tag.get_text(strip=True) if author_tag else ''
                
                # Cuerpo
                body_paragraphs = []
                content_div = soup.find(['div', 'article'], class_=re.compile(r'(article-content|story-content|body|content)', re.I))
                
                if content_div:
                    paragraphs = content_div.find_all('p')
                else:
                    article_tag = soup.find('article')
                    if article_tag:
                        paragraphs = article_tag.find_all('p')
                    else:
                        paragraphs = soup.find_all('p')
                
                for p in paragraphs:
                    text = p.get_text(strip=True)
                    if len(text) > 20:
                        body_paragraphs.append(text)
                
                body = '\n\n'.join(body_paragraphs)
                
                return {
                    'url': article_url,
                    'title': title,
                    'author': author,
                    'date': date,
                    'body': body,
                    'scraped_at': datetime.now().isoformat()
                }
                
            except Exception as e:
                logger.error(f"Error scrapeando artículo '{article_url}' (intento {attempt + 1}/{self.max_retries}): {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(5)
            finally:
                if driver:
                    try:
                        driver.quit()
                    except:
                        pass
        
        return None
    
    def scrape_full_articles(self, article_urls):
        """Scrape contenido completo con procesamiento concurrente"""
        full_articles = []
        
        logger.info(f"Scrapeando contenido completo de {len(article_urls)} artículos")
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_url = {
                executor.submit(self.scrape_article_body, url): url 
                for url in article_urls
            }
            
            for future in as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    article = future.result()
                    if article:
                        full_articles.append(article)
                        if len(full_articles) % 10 == 0:
                            logger.info(f"Progreso: {len(full_articles)}/{len(article_urls)} artículos completos")
                except Exception as e:
                    logger.error(f"Error scrapeando {url}: {e}")
        
        logger.info(f"Total de artículos completos: {len(full_articles)}")
        return full_articles
    
    def save_to_json(self, filename='infobae_articles.json'):
        """Guarda artículos en JSON"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.articles, f, ensure_ascii=False, indent=2)
        logger.info(f"Artículos guardados en {filename}")
        return filename
    
    def save_to_csv(self, filename='infobae_articles.csv'):
        """Guarda artículos en CSV"""
        if not self.articles:
            logger.warning("No hay artículos para guardar")
            return
        
        keys = self.articles[0].keys()
        with open(filename, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(self.articles)
        
        logger.info(f"Artículos guardados en {filename}")
        return filename


def main():
    """Función principal - Scraping robusto de UIA"""
    
    print("=" * 60)
    print("SCRAPER ROBUSTO DE INFOBAE - BÚSQUEDA: UIA")
    print("Objetivo: 2000 artículos con contenido completo")
    print("Con reintentos automáticos y guardado incremental")
    print("=" * 60)
    
    scraper = RobustInfobaeScraper(
        max_workers=5,
        delay=1.0,
        headless=True,
        max_retries=3
    )
    
    # Fase 1: Extraer títulos y links
    query = "uia"
    max_pages = 110
    
    print(f"\nFase 1: Extrayendo títulos y links (hasta {max_pages} páginas)")
    print("El scraper guardará progreso cada 5 páginas")
    print("Puede interrumpir con Ctrl+C y reanudar después\n")
    
    articles = scraper.scrape_search_results(
        query, 
        max_pages=max_pages, 
        resume=True,
        checkpoint_file='checkpoint_uia.json'
    )
    
    if not articles:
        print("\n⚠️ No se encontraron artículos")
        return
    
    # Limitar a 2000
    if len(articles) > 2000:
        print(f"\n⚠️ Se encontraron {len(articles)} artículos, limitando a 2000")
        articles = articles[:2000]
        scraper.articles = articles
    
    # Guardar resultados básicos
    scraper.save_to_json('infobae_uia_titulos.json')
    scraper.save_to_csv('infobae_uia_titulos.csv')
    
    print(f"\n✓ Fase 1 completada: {len(articles)} artículos extraídos")
    print(f"✓ Archivos guardados: infobae_uia_titulos.json y .csv")
    
    # Fase 2: Scraping profundo
    print("\n" + "=" * 60)
    print(f"Fase 2: Extrayendo contenido completo de {len(articles)} artículos")
    print("Esto puede tomar varias horas...")
    print("=" * 60)
    
    urls_to_scrape = [article['url'] for article in articles]
    full_articles = scraper.scrape_full_articles(urls_to_scrape)
    
    # Guardar artículos completos
    with open('infobae_uia_completo.json', 'w', encoding='utf-8') as f:
        json.dump(full_articles, f, ensure_ascii=False, indent=2)
    
    print(f"\n✓ Fase 2 completada: {len(full_articles)} artículos con contenido completo")
    print(f"✓ Archivo guardado: infobae_uia_completo.json")
    
    print("\n" + "=" * 60)
    print("✅ SCRAPING COMPLETADO EXITOSAMENTE")
    print("=" * 60)
    print(f"Total de artículos: {len(articles)}")
    print(f"Artículos con contenido completo: {len(full_articles)}")
    print(f"\nArchivos generados:")
    print(f"  - infobae_uia_titulos.json (títulos, links, fechas)")
    print(f"  - infobae_uia_titulos.csv (títulos, links, fechas)")
    print(f"  - infobae_uia_completo.json (contenido completo con cuerpo)")
    print(f"  - checkpoint_uia.json (progreso guardado)")
    print("=" * 60)


if __name__ == "__main__":
    main()
