import streamlit as st
import psycopg2
from psycopg2 import sql
from google_places_scraper import scraper as google_scraper, extract_place_ids, get_place_details
from kvk_scraper import scraper as kvk_scraper, extract_company_data
import pandas as pd
import os
from urllib.parse import urlparse

# Database connection
DATABASE_URL = os.environ.get('DATABASE_URL')


def get_connection():
    url = urlparse(DATABASE_URL)
    connection = psycopg2.connect(
        database=url.path[1:],
        user=url.username,
        password=url.password,
        host=url.hostname,
        port=url.port
    )
    return connection


def create_table():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS companies (
            id SERIAL PRIMARY KEY,
            place_id TEXT UNIQUE,
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
            kvk_trade_name TEXT
        )
    ''')
    conn.commit()
    cur.close()
    conn.close()


def insert_or_update_company_data(google_data, kvk_data):
    conn = get_connection()
    cur = conn.cursor()

    # Check if the place_id already exists
    cur.execute("SELECT * FROM companies WHERE place_id = %s", (google_data.get('place_id'),))
    existing_record = cur.fetchone()

    if existing_record:
        # Update existing record
        cur.execute('''
            UPDATE companies SET 
            google_name = %s, google_address = %s, google_phone = %s, 
            google_website = %s, google_rating = %s, google_total_ratings = %s,
            kvk_number = %s, kvk_name = %s, kvk_activity = %s,
            kvk_establishment_number = %s, kvk_company_type = %s,
            kvk_establishment_type = %s, kvk_address = %s, kvk_trade_name = %s
            WHERE place_id = %s
        ''', (
            google_data.get('name'), google_data.get('formatted_address'),
            google_data.get('formatted_phone_number'), google_data.get('website'),
            google_data.get('rating'), google_data.get('user_ratings_total'),
            kvk_data.get('kvk_number'), kvk_data.get('name'), kvk_data.get('activity'),
            kvk_data.get('establishment_number'), kvk_data.get('company_type'),
            kvk_data.get('establishment_type'), kvk_data.get('address'),
            kvk_data.get('trade_name'), google_data.get('place_id')
        ))
    else:
        # Insert new record
        cur.execute('''
            INSERT INTO companies 
            (place_id, google_name, google_address, google_phone, google_website, 
            google_rating, google_total_ratings, kvk_number, kvk_name, 
            kvk_activity, kvk_establishment_number, kvk_company_type, 
            kvk_establishment_type, kvk_address, kvk_trade_name) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', (
            google_data.get('place_id'), google_data.get('name'),
            google_data.get('formatted_address'), google_data.get('formatted_phone_number'),
            google_data.get('website'), google_data.get('rating'),
            google_data.get('user_ratings_total'), kvk_data.get('kvk_number'),
            kvk_data.get('name'), kvk_data.get('activity'),
            kvk_data.get('establishment_number'), kvk_data.get('company_type'),
            kvk_data.get('establishment_type'), kvk_data.get('address'),
            kvk_data.get('trade_name')
        ))

    conn.commit()
    cur.close()
    conn.close()


def run_scraper(search_term):
    create_table()

    # Google Places scraping
    google_url = f"https://www.google.nl/maps/search/{search_term}/"
    html = google_scraper(google_url)
    place_ids = extract_place_ids(html)

    progress_bar = st.progress(0)
    for i, place_id in enumerate(place_ids):
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
                        kvk_data = companies[0]

            # Combine and save the data
            insert_or_update_company_data(google_data, kvk_data)

        # Update progress bar
        progress_bar.progress((i + 1) / len(place_ids))

    st.success("Scraping en opslag voltooid.")


def display_results():
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM companies", conn)
    conn.close()
    st.dataframe(df)


def main():
    st.title("Google Places en KvK Scraper")

    search_term = st.text_input("Voer een zoekterm in voor Google Maps:")

    if st.button("Start Scraping"):
        if search_term:
            run_scraper(search_term)
            display_results()
        else:
            st.warning("Voer eerst een zoekterm in.")

    if st.button("Toon Resultaten"):
        display_results()


if __name__ == "__main__":
    main()