import os
import requests
from flask import Flask, render_template, request
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from tqdm import tqdm

app = Flask(__name__)

# Nastavení složky pro stahování
DOWNLOAD_FOLDER = "stazene_soubory"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# Funkce pro stahování souboru
def download_file(url, folder):
    local_filename = os.path.join(folder, os.path.basename(urlparse(url).path))
    response = requests.get(url, stream=True)
    if response.status_code == 200:
        total_size = int(response.headers.get('content-length', 0))
        with open(local_filename, 'wb') as f, tqdm(
            desc=local_filename, total=total_size, unit='B', unit_scale=True
        ) as bar:
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    f.write(chunk)
                    bar.update(len(chunk))
        print(f"Staženo: {local_filename}")
    else:
        print(f"Chyba při stahování: {url}")

# Funkce na získání všech odkazů
def get_all_links(url, visited):
    try:
        response = requests.get(url)
        if response.status_code != 200:
            return []
    except requests.exceptions.RequestException as e:
        print(f"Chyba při načítání {url}: {e}")
        return []
    
    soup = BeautifulSoup(response.text, 'html.parser')
    links = set()
    
    for link in soup.find_all('a', href=True):
        full_url = urljoin(url, link['href'])
        if urlparse(full_url).netloc == urlparse(url).netloc and full_url not in visited:
            links.add(full_url)
    
    return links

# Funkce na procházení webu
def crawl_and_download(start_url, visited=set()):
    if start_url in visited:
        return
    
    print(f"Prohledávám: {start_url}")
    visited.add(start_url)
    
    try:
        response = requests.get(start_url)
        if response.status_code != 200:
            return
    except requests.exceptions.RequestException as e:
        print(f"Chyba při načítání {start_url}: {e}")
        return
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    for link in soup.find_all('a', href=True):
        file_url = urljoin(start_url, link['href'])
        if file_url.lower().endswith(('.pdf', '.doc', '.docx')):
            download_file(file_url, DOWNLOAD_FOLDER)
    
    for next_page in get_all_links(start_url, visited):
        crawl_and_download(next_page, visited)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/download", methods=["POST"])
def download():
    url = request.form["url"]
    crawl_and_download(url)
    return f"Stahování souborů z <b>{url}</b> bylo dokončeno! ✅"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
