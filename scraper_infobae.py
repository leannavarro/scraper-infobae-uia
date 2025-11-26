"""
Scraper masivo de Infobae - Búsqueda de UIA
Extrae noticias relacionadas con UIA (Unión Industrial Argentina)
Usa Selenium para manejar contenido JavaScript dinámico
"""

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
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


class InfobaeScraper:
    """Scraper para extraer noticias de Infobae mediante búsqueda con Selenium"""
    
    def __init__(self, max_workers=3, delay=1.0, headless=True):
        """
        Args:
            max_workers: Número de hilos concurrentes para scraping profundo
            delay: Delay entre requests (en segundos)
            headless: Si True, ejecuta Chrome sin interfaz gráfica
        """
        self.base_url = "https://www.infobae.com"
        self.search_url = "https://www.infobae.com/buscador/"
        self.max_workers = max_workers
        self.delay = delay
        self.headless = headless
        self.articles = []
        
    def _get_driver(self):
        """Crea y configura un driver de Selenium"""
        chrome_options = Options()
        
        if self.headless:
            chrome_options.add_argument('--headless')
        
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        
        # Deshabilitar imágenes para acelerar la carga
        prefs = {'profile.managed_default_content_settings.images': 2}
        chrome_options.add_experimental_option('prefs', prefs)
        
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.set_page_load_timeout(30)
        
        return driver
    
    def save_checkpoint(self, articles, page):
        """Guarda el progreso actual"""
        checkpoint = {
            'page': page,
            'articles': articles,
            'timestamp': datetime.now().isoformat()
        }
        with open(self.checkpoint_file, 'w', encoding='utf-8') as f:
            json.dump(checkpoint, f, ensure_ascii=False, indent=2)
        logger.info(f"✓ Checkpoint guardado: página {page}, {len(articles)} artículos")
    
    def load_checkpoint(self):
        """Carga el progreso guardado si existe"""
        if os.path.exists(self.checkpoint_file):
            try:
                with open(self.checkpoint_file, 'r', encoding='utf-8') as f:
                    checkpoint = json.load(f)
                logger.info(f"✓ Checkpoint cargado: página {checkpoint['page']}, {len(checkpoint['articles'])} artículos")
                return checkpoint
            except Exception as e:
                logger.error(f"Error cargando checkpoint: {e}")
        return None
    
    def scrape_search_results(self, query, max_pages=5):resume=True):
        """
        Scrape resultados de búsqueda de Infobae usando Selenium
        Navega usando el botón "Siguiente" en lugar de URLs de paginación
        
        Args:
            query: Término de búsqueda (ej: "uia")
            max_pages: Número máximo de páginas a scrapear
            resume: Si True, intenta reanudar desde checkpoint guardado
        
        Returns:
            Lista de diccionarios con información de artículos
        """
        all_articles = []
        seen_urls = set()  # Para rastrear URLs únicas globalmente
        start_page = 1
        driver = None
        
        # Intentar cargar checkpoint si resume=True
        if resume:
            checkpoint = self.load_checkpoint()
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
            
            # Esperar a que se cargue el contenido
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                time.sleep(2)
            except Exception as e:
                logger.warning(f"Timeout esperando contenido inicial")
            
            for page in range(start_page, max_pages + 1):
                retry_count = 0
                page_success = False
                
                while retry_count < self.max_retries and not page_success:
                    try:
                        time.sleep(self.delay)
                        
                        logger.info(f"Scrapeando página {page}")
                    
                    # Obtener el HTML renderizado
                    page_source = driver.page_source
                    soup = BeautifulSoup(page_source, 'html.parser')
                    
                    # Buscar artículos - probar diferentes selectores
                    article_elements = []
                    
                    # Buscar links que apunten a artículos de Infobae
                    all_links = soup.find_all('a', href=True)
                    page_seen_urls = set()  # URLs vistas solo en esta página
                    
                    for link in all_links:
                        url_href = link['href']
                        if not url_href.startswith('http'):
                            url_href = urljoin(self.base_url, url_href)
                        
                        # Filtrar: solo artículos válidos de Infobae y no duplicados
                        if (url_href.startswith('https://www.infobae.com/') and 
                            any(section in url_href for section in ['/economia/', '/politica/', '/sociedad/', '/america/', '/deportes/', '/tecno/', '/cultura/', '/salud/', '/el-mundo/']) and
                            url_href not in seen_urls and  # No visto globalmente
                            url_href not in page_seen_urls and  # No visto en esta página
                            '/fotos/' not in url_href and
                            '/buscador/' not in url_href):
                            
                            # Buscar el contenedor padre
                            parent = link.find_parent(['article', 'div', 'li'])
                            if parent:
                                article_elements.append({
                                    'parent': parent,
                                    'link': link,
                                    'url': url_href
                                })
                                page_seen_urls.add(url_href)
                    
                    if not article_elements:
                        logger.warning(f"No se encontraron artículos en página {page}")
                        if page == 1:
                            # Guardar HTML para debug
                            with open('debug_page_1.html', 'w', encoding='utf-8') as f:
                                f.write(page_source)
                            logger.info("HTML de página 1 guardado en debug_page_1.html para inspección")
                        break
                    
                    logger.info(f"Página {page}: {len(article_elements)} artículos encontrados")
                    
                    page_articles = 0
                    for article_data in article_elements:
                        try:
                            parent = article_data['parent']
                            link = article_data['link']
                            url = article_data['url']
                            
                            # Extraer título
                            title = ''
                            title_tag = parent.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'span'])
                            if title_tag:
                                title = title_tag.get_text(strip=True)
                            
                            # Si no hay título en el parent, usar el texto del link
                            if not title or len(title) < 20:
                                title = link.get_text(strip=True)
                            
                            # Filtrar títulos muy cortos
                            if not title or len(title) < 20:
                                continue
                            
                            # Extraer descripción/resumen
                            description = ''
                            desc_tag = parent.find(['p', 'div'], class_=re.compile(r'(description|summary|deck|excerpt)', re.I))
                            if desc_tag:
                                description = desc_tag.get_text(strip=True)
                            
                            # Extraer fecha si está disponible
                            date = ''
                            date_tag = parent.find('time')
                            if date_tag:
                                date = date_tag.get('datetime', date_tag.get_text(strip=True))
                            
                            article_info = {
                                'title': title,
                                'url': url,
                                'description': description,
                                'date': date,
                                'search_query': query,
                                'page': page,
                                'scraped_at': datetime.now().isoformat()
                            }
                            
                            all_articles.append(article_info)
                            seen_urls.add(url)  # Agregar a URLs vistas globalmente
                            page_articles += 1
                            
                        except Exception as e:
                            logger.warning(f"Error procesando artículo: {e}")
                            continue
                    
                        logger.info(f"✓ Página {page} completada: {page_articles} artículos únicos extraídos")
                        page_success = True
                        
                        # Guardar checkpoint cada 5 páginas
                        if page % 5 == 0:
                            self.save_checkpoint(all_articles, page)
                        
                        if page_articles == 0:
                            logger.info(f"No se encontraron artículos nuevos. Deteniendo en página {page}")
                            break
                    
                    except Exception as e:
                        retry_count += 1
                        logger.error(f"Error scrapeando página {page} (intento {retry_count}/{self.max_retries}): {e}")
                        if retry_count < self.max_retries:
                            logger.info(f"Reintentando en 10 segundos...")
                            if driver:
                                try:
                                    driver.quit()
                                except:
                                    pass
                            time.sleep(10)
                            driver = self._get_driver()
                            # Recargar la página de búsqueda
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
                            logger.error(f"Máximo de reintentos alcanzado para página {page}. Guardando progreso...")
                            self.save_checkpoint(all_articles, page - 1)
                            break
                
                if not page_success:
                    logger.error(f"No se pudo completar la página {page} después de {self.max_retries} intentos")
                    break
                
                # Intentar hacer click en el botón "Siguiente" para la próxima iteración
                if page < max_pages and page_success:
                        try:
                            # Buscar el botón "Siguiente" - puede tener diferentes textos
                            next_button = None
                            
                            # Intentar encontrar por texto
                            try:
                                next_button = driver.find_element(By.XPATH, "//a[contains(text(), 'Siguiente') or contains(text(), 'siguiente') or contains(text(), 'SIGUIENTE')]")
                            except:
                                pass
                            
                            # Alternativa: buscar por clase o atributo común de paginación
                            if not next_button:
                                try:
                                    next_button = driver.find_element(By.CSS_SELECTOR, "a[rel='next']")
                                except:
                                    pass
                            
                            if not next_button:
                                try:
                                    # Buscar elementos con clase que contenga "next" o "siguiente"
                                    next_button = driver.find_element(By.XPATH, "//a[contains(@class, 'next') or contains(@class, 'siguiente')]")
                                except:
                                    pass
                            
                            if next_button:
                                logger.info(f"Haciendo click en botón 'Siguiente' para cargar página {page + 1}")
                                # Scroll hasta el botón
                                driver.execute_script("arguments[0].scrollIntoView();", next_button)
                                time.sleep(1)
                                next_button.click()
                                time.sleep(2)  # Esperar a que cargue la siguiente página
                            else:
                                logger.warning(f"No se encontró el botón 'Siguiente' después de página {page}")
                                break
                                
                        except Exception as e:
                                logger.error(f"Error al hacer click en 'Siguiente': {e}")
                                break            self.articles = all_articles
            logger.info(f"✓ Total de artículos extraídos: {len(all_articles)}")
            
            # Guardar checkpoint final
            if all_articles:
                self.save_checkpoint(all_articles, page if 'page' in locals() else max_pages)
            
            return all_articles
            
        finally:
            if driver:
                driver.quit()
                logger.info("Driver de Selenium cerrado")
    
    def scrape_article_body(self, article_url):
        """
        Extrae el cuerpo completo de un artículo individual usando Selenium
        
        Args:
            article_url: URL del artículo
        
        Returns:
            Diccionario con título, cuerpo, fecha, autor
        """
        driver = None
        
        for attempt in range(self.max_retries):
            try:
                driver = self._get_driver()
                time.sleep(self.delay)
            
            driver.get(article_url)
            
            # Esperar a que se cargue el contenido
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "article"))
                )
            except:
                pass
            
            time.sleep(1)
            page_source = driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # Título
            title_tag = soup.find(['h1'])
            title = title_tag.get_text(strip=True) if title_tag else ''
            
            # Fecha
            date_tag = soup.find('time')
            date = date_tag.get('datetime', '') if date_tag else ''
            
            # Autor
            author_tag = soup.find(['span', 'a'], class_=re.compile(r'(author|autor)', re.I))
            author = author_tag.get_text(strip=True) if author_tag else ''
            
            # Cuerpo del artículo
            body_paragraphs = []
            
            # Intentar diferentes selectores comunes
            content_div = soup.find(['div', 'article'], class_=re.compile(r'(article-content|story-content|body|content)', re.I))
            
            if content_div:
                paragraphs = content_div.find_all('p')
            else:
                # Fallback: buscar todos los <p> dentro de article
                article_tag = soup.find('article')
                if article_tag:
                    paragraphs = article_tag.find_all('p')
                else:
                    paragraphs = soup.find_all('p')
            
            for p in paragraphs:
                text = p.get_text(strip=True)
                if len(text) > 20:  # Filtrar párrafos muy cortos
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
                if driver:
                    try:
                        driver.quit()
                    except:
                        pass
                    driver = None
                
                if attempt < self.max_retries - 1:
                    time.sleep(5)
                else:
                    return None
            finally:
                if driver:
                    try:
                        driver.quit()
                    except:
                        pass
        
        return None
    
    def scrape_full_articles(self, article_urls):
        """
        Scrape el contenido completo de múltiples artículos de forma concurrente
        
        Args:
            article_urls: Lista de URLs de artículos
        
        Returns:
            Lista de artículos con cuerpo completo
        """
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
                except Exception as e:
                    logger.error(f"Error scrapeando {url}: {e}")
        
        logger.info(f"Total de artículos completos extraídos: {len(full_articles)}")
        return full_articles
    
    def save_to_json(self, filename='infobae_articles.json'):
        """Guarda los artículos en formato JSON"""
        filepath = f"{filename}"
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.articles, f, ensure_ascii=False, indent=2)
        logger.info(f"Artículos guardados en {filepath}")
        return filepath
    
    def save_to_csv(self, filename='infobae_articles.csv'):
        """Guarda los artículos en formato CSV"""
        if not self.articles:
            logger.warning("No hay artículos para guardar")
            return
        
        filepath = f"{filename}"
        keys = self.articles[0].keys()
        
        with open(filepath, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(self.articles)
        
        logger.info(f"Artículos guardados en {filepath}")
        return filepath


def main():
    """Función principal - Scraping de búsqueda de UIA"""
    
    # Scraping de búsqueda de UIA
    print("=" * 60)
    print("SCRAPER DE INFOBAE - BÚSQUEDA: UIA (con Selenium)")
    print("Objetivo: 2000 artículos con contenido completo")
    print("=" * 60)
    
    scraper = InfobaeScraper(
        max_workers=5, 
        delay=1.0, 
        headless=True,
        max_retries=3,
        checkpoint_file='checkpoint_uia.json'
    )
    
    # 1. Extraer artículos sobre UIA - calcular páginas necesarias
    # ~19-20 artículos por página, necesitamos ~105 páginas para 2000 artículos
    query = "uia"
    max_pages = 110  # Un poco más para asegurar
    
    print(f"\nFase 1: Extrayendo títulos y links (hasta {max_pages} páginas)")
    print("El scraper guardará progreso cada 5 páginas y reintentará automáticamente en caso de errores.")
    articles = scraper.scrape_search_results(query, max_pages=max_pages, resume=True)
    
    if not articles:
        print("\n⚠️ No se encontraron artículos. Verifica la conectividad o la estructura del sitio.")
        return
    
    # Limitar a 2000 si obtuvimos más
    if len(articles) > 2000:
        print(f"\n⚠️ Se encontraron {len(articles)} artículos, limitando a 2000")
        articles = articles[:2000]
        scraper.articles = articles
    
    # Guardar resultados básicos (títulos y links)
    scraper.save_to_json('infobae_uia_titulos.json')
    scraper.save_to_csv('infobae_uia_titulos.csv')
    
    print(f"\n✓ Fase 1 completada: {len(articles)} artículos extraídos")
    print(f"✓ Archivos guardados: infobae_uia_titulos.json y infobae_uia_titulos.csv")
    
    # 2. Scraping profundo de contenido completo
    print("\n" + "=" * 60)
    print(f"Fase 2: Extrayendo contenido completo de {len(articles)} artículos")
    print("Esto puede tomar un tiempo considerable...")
    print("=" * 60)
    
    # Extraer todos los artículos con contenido completo
    urls_to_scrape = [article['url'] for article in articles]
    
    full_articles = scraper.scrape_full_articles(urls_to_scrape)
    
    # Guardar artículos completos
    with open('infobae_uia_completo.json', 'w', encoding='utf-8') as f:
        json.dump(full_articles, f, ensure_ascii=False, indent=2)
    
    print(f"\n✓ Fase 2 completada: {len(full_articles)} artículos con contenido completo")
    print(f"✓ Archivo guardado: infobae_uia_completo.json")
    
    print("\n" + "=" * 60)
    print(f"✅ SCRAPING COMPLETADO EXITOSAMENTE")
    print("=" * 60)
    print(f"Total de artículos: {len(articles)}")
    print(f"Artículos con contenido completo: {len(full_articles)}")
    print(f"\nArchivos generados:")
    print(f"  - infobae_uia_titulos.json (títulos, links, fechas)")
    print(f"  - infobae_uia_titulos.csv (títulos, links, fechas)")
    print(f"  - infobae_uia_completo.json (contenido completo con cuerpo)")
    print("=" * 60)


if __name__ == "__main__":
    main()
