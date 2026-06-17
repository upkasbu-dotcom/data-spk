import os
import sys
import json
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from github import Github

def push_json_ke_github(nama_file, path_lokal, commit_msg="Auto update data SCM"):
    """Fungsi untuk push file JSON kembali ke repository GitHub"""
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("⚠️ GITHUB_TOKEN tidak ditemukan, file JSON tidak bisa di-push ke repo.")
        return

    try:
        g = Github(token)
        repo = g.get_repo(os.environ.get("GITHUB_REPOSITORY"))

        with open(path_lokal, "r", encoding="utf-8") as f:
            content = f.read()

        try:
            # Cek apakah file sudah ada (untuk ambil SHA nya)
            existing = repo.get_contents(nama_file)
            repo.update_file(nama_file, commit_msg, content, existing.sha, branch="main")
            print(f"✅ File '{nama_file}' berhasil diupdate di GitHub!")
        except Exception:
            # Jika file belum ada, buat file baru
            repo.create_file(nama_file, commit_msg, content, branch="main")
            print(f"✅ File '{nama_file}' berhasil dibuat di GitHub!")
    except Exception as e:
        print(f"❌ Terjadi error saat push ke GitHub: {e}")

def main():
    print("==================================================")
    print("=== [START] Operasi Bot SCM ===")
    print("==================================================")

    # 1. Ambil Kredensial
    username = os.environ.get("SCM_USERNAME")
    password = os.environ.get("SCM_PASSWORD")

    if not username or not password:
        print("Error: USERNAME atau PASSWORD tidak ditemukan!")
        sys.exit(1)

    print("[*] Kredensial berhasil dimuat.")

    # 2. Setup Chrome Headless untuk GitHub Actions
    chrome_options = Options()
    chrome_options.add_argument('--headless=new')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    
    driver = None
    try:
        print("[*] Memulai Google Chrome...")
        driver = webdriver.Chrome(options=chrome_options)
        wait = WebDriverWait(driver, 20)

        # =========================================================
        # MASUKKAN LOGIKA SCRAPING SCM ANDA DI BAWAH INI
        # =========================================================
        
        # Contoh dummy data scraping:
        # driver.get("https://website-scm-anda.com/login")
        # username_field = wait.until(EC.presence_of_element_located((By.ID, "username")))
        # password_field = driver.find_element(By.ID, "password")
        # username_field.send_keys(username)
        # password_field.send_keys(password)
        # driver.find_element(By.XPATH, "//button[@type='submit']").click()
        
        # Misalkan Anda berhasil scraping data dan menyimpannya dalam list of dictionary:
        data_hasil_scraping = [
            {
                "id": 1,
                "produk": "Beras Premium",
                "stok": "150 karung",
                "harga": "Rp 65.000",
                "tanggal_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            },
            {
                "id": 2,
                "produk": "Gula Pasir",
                "stok": "200 karung",
                "harga": "Rp 16.000",
                "tanggal_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        ]
        
        print(f"[*] Berhasil scrape {len(data_hasil_scraping)} data.")

        # =========================================================
        # BUAT DAN SIMPAN FILE JSON
        # =========================================================
        
        nama_file_json = "data_scm.json"
        
        with open(nama_file_json, "w", encoding="utf-8") as f:
            # indent=4 agar json rapi dan mudah dibaca
            json.dump(data_hasil_scraping, f, indent=4, ensure_ascii=False)
        
        print(f"[*] Data berhasil disimpan ke file lokal: {nama_file_json}")

        # =========================================================
        # PUSH FILE JSON KE REPOSITORY GITHUB
        # =========================================================
        
        print("[*] Mengirim file JSON ke repository GitHub...")
        push_json_ke_github(nama_file_json, nama_file_json)

        # =========================================================
        # AKHIR DARI LOGIKA
        # =========================================================

    except Exception as e:
        print(f"Error saat menjalankan bot: {e}")
        sys.exit(1)
    finally:
        if driver:
            driver.quit()
            print("[*] Browser ditutup.")

if __name__ == "__main__":
    main()
