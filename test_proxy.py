import requests
import os
from dotenv import load_dotenv
load_dotenv()


url = 'https://ip.smartproxy.com/json'
username = os.getenv('PROXY_USER')
password = os.getenv('PROXY_PASS')
host = os.getenv('PROXY_HOST')
port = os.getenv('PROXY_PORT')
print(username)
print(password)
proxy = f"http://{username}:{password}@{host}:{port}"
result = requests.get(url, proxies = {
    'http': proxy,
    'https': proxy
})
print(result.text)