import requests
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
from selenium.common.exceptions import TimeoutException
import re

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
    print("Cookies geaccepteerd!")


def scraper(url):
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
    driver.get(url)

    # Accepteer cookies
    accept_cookies(driver)

    # Wacht tot de feed div is geladen
    try:
        feed_div = WebDriverWait(driver, 2).until(
            EC.presence_of_element_located((By.XPATH, "//div[@role='feed']"))
        )
    except TimeoutException:
        print("Kon de feed div niet vinden")
        driver.quit()
        return None

    # Scroll binnen de feed div
    last_height = driver.execute_script("return arguments[0].scrollHeight;", feed_div)
    while True:
        # Scroll naar beneden binnen de feed div
        driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight;", feed_div)

        time.sleep(1)

        new_height = driver.execute_script("return arguments[0].scrollHeight;", feed_div)
        if new_height == last_height:
            break
        last_height = new_height

    html = driver.page_source
    driver.quit()
    return html


def extract_body_content(html):
    soup = BeautifulSoup(html, "html.parser")
    body_content = soup.body
    if body_content:
        return str(body_content)
    return ""


def extract_place_ids(html):
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

    return place_ids


def get_place_details(place_id):
    google_api = os.getenv('GOOGLE_API_KEY')
    url = f'https://maps.googleapis.com/maps/api/place/details/json?place_id={place_id}&fields=name,formatted_address,formatted_phone_number,website,rating,user_ratings_total,address_component,type&key={google_api}'
    response = requests.get(url)
    if response.status_code == 200:
        return response.json().get('result')
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
