
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.keys import Keys
import json
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from dotenv import load_dotenv
import os
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.chromium.remote_connection import ChromiumRemoteConnection
from selenium.common.exceptions import TimeoutException, WebDriverException

from selenium.webdriver import Remote, ChromeOptions

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
    SBR_WEBDRIVER = os.getenv('SBR_WEBDRIVER')
    sbr_connection = ChromiumRemoteConnection(SBR_WEBDRIVER, 'goog', 'chrome')

    chrome_options = ChromeOptions()
    # Voeg hier eventuele extra opties toe die u nodig heeft

    try:
        with Remote(sbr_connection, options=chrome_options) as driver:
            driver.get(url)

            # Handel cookies af
            handle_cookies(driver)

            # Wacht tot het zoekveld aanwezig is
            search_box = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[placeholder='Zoek in kvk.nl']"))
            )

            search_box.clear()

            search_box.send_keys(search_term)

            search_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR,
                                            "button[class*='Button-module_generic-button'][class*='Button-module_primary']"))
            )

            driver.execute_script("arguments[0].click();", search_button)



            # Wacht even om zeker te zijn dat alles is geladen
            time.sleep(2)

            html = driver.page_source
            return html

    except TimeoutException:
        print("Timeout while waiting for element")
    except WebDriverException as e:
        print(f"WebDriver error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

    return None


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
