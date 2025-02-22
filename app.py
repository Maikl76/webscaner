import os
import requests
from flask import Flask, render_template, request
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from tqdm import tqdm
import traceback  # Pro detailní logování chyb

app = Flask(__name__)

# Nastavení složky pro stahování
DOWNLOAD_FOLDER = "stazene_soubory"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# User-Agent pro simulaci běžného prohlížeče (vyhne se blokacím)
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


# Funkce pro stahování souborů
def download_file(url, folder):
    local_filename = os.path.join(folder, os.path.basename(urlparse(url).path))
    
    try:
        response = requests.get(url, headers=HEADERS, stream=True, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"❌ Chyba při stahování {url}: {e}")
        return

    total_size = int(response.headers.get('content-length', 0))
    with open(local_filename, 'wb') as f, tqdm(
        desc=local_filename, total=total_size, unit='B', unit_scale=True
    ) as bar:
        for chunk in response.iter_content(chunk_size=1024):
            if chunk:
                f.write(chunk)
                bar.update(len(chunk))

    print(f"✅ Staženo: {local_filename}")


# Funkce na získání všech odkazů na stránce
def get_all_links(url, visited):
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"❌ Chyba při načítání {url}: {e}")
        return []

    soup = BeautifulSoup(response.text, 'html.parser')
    links = set()

    for link in soup.find_all('a', href=True):
        full_url = urljoin(url, link['href'])
        if urlparse(full_url).netloc == urlparse(url).netloc and full_url not in visited:
            links.add(full_url)

    return links


# Funkce na procházení webu a stahování souborů
def crawl_and_download(start_url, visited=set()):
    if start_url in visited:
        return "Tato stránka už byla navštívena."

    print(f"🔍 Prohledávám: {start_url}")
    visited.add(start_url)

    try:
        response = requests.get(start_url, headers=HEADERS, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"❌ Chyba při načítání {start_url}: {e}")
        return f"Chyba při načítání stránky: {e}"

    try:
        soup = BeautifulSoup(response.text, 'html.parser')
    except Exception as e:
        print(f"❌ Chyba při parsování HTML: {e}")
        print(traceback.format_exc())
        return f"Chyba při parsování HTML: {e}"

    # Stahování souborů
    try:
        for link in soup.find_all('a', href=True):
            file_url = urljoin(start_url, link['href'])
            if file_url.lower().endswith(('.pdf', '.doc', '.docx')):
                download_file(file_url, DOWNLOAD_FOLDER)
    except Exception as e:
        print(f"❌ Chyba při stahování souborů: {e}")
        print(traceback.format_exc())
        return f"Chyba při stahování souborů: {e}"

    # Rekurzivní procházení dalších stránek
    try:
        for next_page in get_all_links(start_url, visited):
            crawl_and_download(next_page, visited)
    except Exception as e:
        print(f"❌ Chyba při procházení dalších odkazů: {e}")
        print(traceback.format_exc())
        return f"Chyba při procházení dalších odkazů: {e}"

    return "✅ Stahování dokončeno!"


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/download", methods=["POST"])
def download():
    url = request.form["url"]
    result = crawl_and_download(url)
    return f"<h2>{result}</h2>"


if __name__ == "__main__":
    PORT = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=PORT)
