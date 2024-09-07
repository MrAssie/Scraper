import requests
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from dotenv import load_dotenv
import os
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.chromium.remote_connection import ChromiumRemoteConnection
from selenium.common.exceptions import TimeoutException, WebDriverException
import re
from selenium.webdriver import Remote, ChromeOptions
import streamlit as st
load_dotenv()


def accept_cookies(driver):
    try:
        # Probeer eerst op tekst te zoeken
        accept_button = WebDriverWait(driver, 3).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Alles accepteren')]"))
        )
    except TimeoutException:
        try:
            # Als dat niet lukt, probeer dan op aria-label te zoeken
            accept_button = WebDriverWait(driver, 3).until(
                EC.element_to_be_clickable((By.XPATH, "//button[@aria-label='Alles accepteren']"))
            )
        except TimeoutException:
            # Als laatste optie, zoek naar een knop in een form met 'accept' in de action URL
            accept_button = WebDriverWait(driver, 3).until(
                EC.element_to_be_clickable((By.XPATH, "//form[contains(@action, 'accept')]//button"))
            )

    accept_button.click()



def scraper(url):
    SBR_WEBDRIVER = os.getenv('SBR_WEBDRIVER')
    sbr_connection = ChromiumRemoteConnection(SBR_WEBDRIVER, 'goog', 'chrome')

    driver = None
    try:
        driver = Remote(sbr_connection, options=ChromeOptions())

        wait = WebDriverWait(driver, 3)

        driver.get(url)

        accept_cookies(driver)

        feed_div = wait.until(EC.presence_of_element_located((By.XPATH, "//div[@role='feed']")))

        for i in range(7):
            driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight;", feed_div)
            time.sleep(1)
            new_height = driver.execute_script("return arguments[0].scrollHeight;", feed_div)
            print(f"Scroll poging {i + 1} voltooid")

        html = driver.page_source
        return html
    except Exception as e:
        print(f"Fout tijdens scrapen: {e}")
        return None
    finally:
        if driver:
            try:
                driver.quit()
            except Exception as e:
                print(f"Fout bij het afsluiten van de driver: {e}")


def extract_body_content(html):
    soup = BeautifulSoup(html, "html.parser")
    body_content = soup.body
    if body_content:
        return str(body_content)
    return ""


def extract_place_ids(html):
    if not html:
        st.warning("Geen zoekresultaten gevonden. Controleer je zoekopdracht en probeer het opnieuw.")
        return []

    soup = BeautifulSoup(html, 'html.parser')
    place_ids = []

    # Zoek alle <a> tags die links naar Google Place pagina's bevatten
    for link in soup.find_all('a', href=lambda href: href and '/maps/place/' in href):
        place_url = link['href']

        # Extraheer de place_id uit de URL
        match = re.search(r'!19s([\w-]+)', place_url)
        if match:
            place_id = match.group(1)
            place_ids.append(place_id)

    if not place_ids:
        st.warning("Geen locaties gevonden. Probeer een andere zoekopdracht.")

    return place_ids


def get_place_details(place_id):
    google_api = os.getenv('GOOGLE_API_KEY')
    if not google_api:
        st.error("Google API-sleutel ontbreekt. Controleer je configuratie.")
        return None

    url = f'https://maps.googleapis.com/maps/api/place/details/json?place_id={place_id}&fields=name,formatted_address,formatted_phone_number,website,rating,user_ratings_total,address_component,type&key={google_api}'

    try:
        response = requests.get(url, timeout=10)  # Voeg een timeout toe
        response.raise_for_status()  # Raise een uitzondering voor HTTP-fouten
        result = response.json().get('result')
        if not result:
            st.warning(f"Geen details gevonden voor een locatie (ID: {place_id})")
        return result
    except requests.exceptions.RequestException as e:
        st.error(f"Er is een fout opgetreden bij het ophalen van locatiegegevens. Probeer het later opnieuw.")
        return None


if __name__ == "__main__":
    url = "https://www.google.nl/maps/search/timmerman/"
    html = scraper(url)
    place_ids = extract_place_ids(html)

    for place_id in place_ids:
        print(f"Place ID: {place_id}")
        details = get_place_details(place_id)
        # if details:
        #     print(f"Name: {details.get('name')}")
        #     print(f"Address: {details.get('formatted_address')}")
        #     print(f"Phone: {details.get('formatted_phone_number')}")
        #     print(f"Website: {details.get('website')}")
        #     print(f"Rating: {details.get('rating')}")
        #     print(f"Total Ratings: {details.get('user_ratings_total')}")
        #     print(f"Types: {', '.join(details.get('types', []))}")
        #     print("-" * 50)
        # else:
        #     print(f"Could not fetch details for place ID: {place_id}")
        # print("\n")
        print(details)
