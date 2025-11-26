from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time

options = Options()
options.add_argument('--headless=new')
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)

driver.get('https://www.infobae.com/buscador/?query=uia')
time.sleep(5)

soup = BeautifulSoup(driver.page_source, 'html.parser')

# Buscar todos los links de artículos
all_links = soup.find_all('a', href=True)
article_links = [a['href'] for a in all_links if '/economia/' in a['href'] or '/politica/' in a['href']]

print(f'Total links encontrados: {len(all_links)}')
print(f'Links de economía/política: {len(article_links)}')
print('\nPrimeros 10 links:')
for i, link in enumerate(article_links[:10], 1):
    print(f'{i}. {link}')

# Buscar divs con resultados
divs_with_link = soup.find_all('div', class_=True)
print(f'\nTotal divs con class: {len(divs_with_link)}')
if divs_with_link:
    print(f'Ejemplo de clases: {divs_with_link[0].get("class")}')

driver.quit()
