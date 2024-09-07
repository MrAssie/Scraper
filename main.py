import sqlite3
from google_places_scraper import scraper as google_scraper, extract_place_ids, get_place_details
from kvk_scraper import scraper as kvk_scraper, extract_company_data


def create_database():
    conn = sqlite3.connect('combined_results.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS companies
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  place_id TEXT,
                  google_name TEXT,
                  google_address TEXT,
                  google_phone TEXT,
                  google_website TEXT,
                  google_rating REAL,
                  google_total_ratings INTEGER,
                  kvk_number TEXT,
                  kvk_name TEXT,
                  kvk_activity TEXT,
                  kvk_establishment_number TEXT,
                  kvk_company_type TEXT,
                  kvk_establishment_type TEXT,
                  kvk_address TEXT,
                  kvk_trade_name TEXT)''')
    conn.commit()
    return conn


def insert_company_data(conn, google_data, kvk_data):
    c = conn.cursor()
    c.execute('''INSERT INTO companies 
                 (place_id, google_name, google_address, google_phone, google_website, 
                  google_rating, google_total_ratings, kvk_number, kvk_name, 
                  kvk_activity, kvk_establishment_number, kvk_company_type, 
                  kvk_establishment_type, kvk_address, kvk_trade_name) 
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
              (google_data.get('place_id'), google_data.get('name'),
               google_data.get('formatted_address'), google_data.get('formatted_phone_number'),
               google_data.get('website'), google_data.get('rating'),
               google_data.get('user_ratings_total'), kvk_data.get('kvk_number'),
               kvk_data.get('name'), kvk_data.get('activity'),
               kvk_data.get('establishment_number'), kvk_data.get('company_type'),
               kvk_data.get('establishment_type'), kvk_data.get('address'),
               kvk_data.get('trade_name')))
    conn.commit()


def main():
    conn = create_database()

    # Google Places scraping
    google_url = "https://www.google.nl/maps/search/timmerman/"
    html = google_scraper(google_url)
    place_ids = extract_place_ids(html)

    for place_id in place_ids:
        google_data = get_place_details(place_id)
        if google_data:
            google_data['place_id'] = place_id

            # KvK scraping for each place
            kvk_data = {}
            if 'name' in google_data:
                kvk_url = "https://www.kvk.nl/zoeken/"
                kvk_html = kvk_scraper(kvk_url, google_data['name'])
                if kvk_html:
                    companies = extract_company_data(kvk_html)
                    if companies:
                        # We nemen aan dat de eerste gevonden KvK-entry de juiste is
                        kvk_data = companies[0]

            # Combineer en sla de gegevens op
            insert_company_data(conn, google_data, kvk_data)

    conn.close()
    print("Scraping en opslag voltooid.")


if __name__ == "__main__":
    main()
