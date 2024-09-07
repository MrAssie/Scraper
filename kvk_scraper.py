from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from dotenv import load_dotenv
import os
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.keys import Keys
import json

load_dotenv()


def handle_cookies(driver):
    try:
        # Wacht op de aanwezigheid van de cookie-banner
        cookie_banner = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div[aria-labelledby='label-for-cookie-options']"))
        )

        # Zoek de 'Keuze opslaan' knop
        save_choice_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Keuze opslaan')]"))
        )

        # Klik op de knop
        driver.execute_script("arguments[0].click();", save_choice_button)

        # Wacht tot de cookie-banner verdwijnt
        WebDriverWait(driver, 10).until(
            EC.invisibility_of_element_located((By.CSS_SELECTOR, "div[aria-labelledby='label-for-cookie-options']"))
        )

        print("Cookie keuze opgeslagen!")
    except (TimeoutException, NoSuchElementException) as e:
        print(f"Kon de cookie-banner niet vinden of verwerken: {str(e)}")


def scraper(url, search_term):
    chrome_options = Options()

    proxy_host = os.getenv('PROXY_HOST')
    proxy_port = os.getenv('PROXY_PORT')
    proxy_user = os.getenv('PROXY_USER')
    proxy_pass = os.getenv('PROXY_PASS')

    chrome_options.add_argument(f'--proxy-server={f"http://{proxy_user}:{proxy_pass}@{proxy_host}:{proxy_port}"}')

    # Uncomment de volgende regel als u in headless modus wilt draaien
    chrome_options.add_argument("--headless")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

    try:
        driver.get(url)

        # Handel cookies af
        handle_cookies(driver)

        # Wacht tot het zoekveld aanwezig is
        search_box = WebDriverWait(driver, 2).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[placeholder='Zoek in kvk.nl']"))
        )

        # Wis eventuele bestaande tekst in het zoekveld
        search_box.clear()

        # Vul de zoekopdracht in
        search_box.send_keys(search_term)

        # Druk op Enter om de zoekopdracht uit te voeren
        search_box.send_keys(Keys.RETURN)

        # Wacht even om zeker te zijn dat alles is geladen
        time.sleep(1)

        html = driver.page_source
        return html

    except Exception as e:
        print(f"Er is een fout opgetreden: {str(e)}")
        return None

    finally:
        driver.quit()


def extract_body_content(html):
    if html is None:
        return ""
    soup = BeautifulSoup(html, "html.parser")
    body_content = soup.body
    if body_content:
        return str(body_content)
    return ""


def extract_company_data(html):
    soup = BeautifulSoup(html, 'html.parser')
    companies = []

    for li in soup.select('ul.mb-9.mb-12\@size-m > li'):
        company = {}

        # Bedrijfsnaam en link
        name_link = li.select_one('a.TextLink-module_textlink__1SZwI')
        if name_link:
            company['name'] = name_link.text.strip()
            company['link'] = 'https://www.kvk.nl' + name_link['href'] if name_link.has_attr('href') else ''

        # Activiteitomschrijving
        activity = li.select_one(
            'div[data-ui-test-class="activiteitomschrijving"] span[data-ui-test-class="visible-text"]')
        if activity:
            company['activity'] = activity.text.strip()

        # Overige gegevens
        for item in li.select('ul.List-module_generic-list__eILOq > li'):
            text = item.text.strip()
            if 'KVK-nummer:' in text:
                company['kvk_number'] = text.split(':')[-1].strip()
            elif 'Vestigingsnummer:' in text:
                company['establishment_number'] = text.split(':')[-1].strip()
            elif 'Eenmanszaak' in text:
                company['company_type'] = 'Eenmanszaak'
            elif 'Hoofdvestiging' in text:
                company['establishment_type'] = 'Hoofdvestiging'
            elif text.startswith('Van') or text.startswith('Kerk'):  # Adres
                company['address'] = text

        # Handelsnaam
        trade_name = li.select_one('div.mt-2 ul > li')
        if trade_name:
            company['trade_name'] = trade_name.text.strip()

        companies.append(company)

    return companies


if __name__ == "__main__":
    url = "https://www.kvk.nl/zoeken/"
    search_term = "timmerman"
    html = scraper(url, search_term)
    if html:
        companies = extract_company_data(html)
        for company in companies:
            print(json.dumps(company, indent=2, ensure_ascii=False))
    else:
        print("Er kon geen HTML worden opgehaald.")
