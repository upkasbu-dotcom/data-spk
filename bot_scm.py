import os
import sys
import json
import time
import glob
import csv
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from github import Github
from openpyxl import load_workbook

def push_json_ke_github(nama_file, path_lokal, commit_msg="Auto update data SCM Izin Prinsip"):
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
            existing = repo.get_contents(nama_file)
            repo.update_file(nama_file, commit_msg, content, existing.sha, branch="main")
            print(f"✅ File '{nama_file}' berhasil diupdate di GitHub!")
        except Exception:
            repo.create_file(nama_file, commit_msg, content, branch="main")
            print(f"✅ File '{nama_file}' berhasil dibuat di GitHub!")
    except Exception as e:
        print(f"❌ Terjadi error saat push ke GitHub: {e}")

def parse_downloaded_file(filepath):
    """Membaca file yang terunduh (xlsx, csv) menjadi list of dictionary"""
    data = []
    try:
        if filepath.endswith('.csv'):
            with open(filepath, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    data.append(dict(row))
        elif filepath.endswith('.xlsx') or filepath.endswith('.xls'):
            wb = load_workbook(filename=filepath)
            sheet = wb.active
            rows = list(sheet.iter_rows(values_only=True))
            if len(rows) > 1:
                headers = [str(h).strip() if h else f"col_{i}" for i, h in enumerate(rows[0])]
                for row in rows[1:]:
                    row_data = {}
                    for i, val in enumerate(row):
                        if i < len(headers):
                            if isinstance(val, datetime):
                                val = val.strftime("%Y-%m-%d %H:%M:%S")
                            row_data[headers[i]] = val
                    data.append(row_data)
    except Exception as e:
        print(f"Error parsing file: {e}")
    return data

def scrape_table_to_json(driver):
    """Jika tidak ada file terunduh, scrap tabel HTML di halaman tersebut"""
    data = []
    try:
        table = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "table"))
        )
        rows = table.find_elements(By.TAG_NAME, "tr")
        headers = []
        
        for row in rows:
            ths = row.find_elements(By.TAG_NAME, "th")
            if ths and not headers:
                headers = [th.text.strip() for th in ths]
                continue
            
            tds = row.find_elements(By.TAG_NAME, "td")
            if tds:
                row_data = {}
                for i, td in enumerate(tds):
                    header_name = headers[i] if i < len(headers) else f"col_{i}"
                    row_data[header_name] = td.text.strip()
                data.append(row_data)
    except Exception as e:
        print(f"Tidak ada tabel ditemukan untuk di-scrape: {e}")
        
    return data

def main():
    print("==================================================")
    print("=== [START] Operasi Bot SCM Nusadaya ===")
    print("==================================================")

    username = os.environ.get("SCM_USERNAME")
    password = os.environ.get("SCM_PASSWORD")

    if not username or not password:
        print("Error: USERNAME atau PASSWORD tidak ditemukan!")
        sys.exit(1)

    print("[*] Kredensial berhasil dimuat.")

    download_dir = os.getcwd()
    chrome_options = Options()
    chrome_options.add_argument('--headless=new')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    
    prefs = {
        "download.default_directory": download_dir,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True
    }
    chrome_options.add_experimental_option("prefs", prefs)

    driver = None
    data_hasil_scraping = []
    status_eksekusi = "GAGAL" 

    try:
        print("[*] Memulai Google Chrome...")
        driver = webdriver.Chrome(options=chrome_options)
        wait = WebDriverWait(driver, 20)

        # =========================================================
        # 1. PROSES LOGIN
        # =========================================================
        print("[*] Membuka halaman login SCM Nusadaya...")
        driver.get("https://scm.nusadaya.net/login")
        time.sleep(5)

        try:
            # Deteksi form login yang lebih akurat
            user_field = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='text'], input[type='email']")))
            pass_field = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
            
            user_field.clear()
            user_field.send_keys(username)
            pass_field.clear()
            pass_field.send_keys(password)
            
            # Cari tombol submit
            login_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit'], button.btn-primary")
            login_btn.click()
            
            print("[*] Berhasil submit login. Menunggu halaman dashboard...")
            time.sleep(7) 
        except Exception as e:
            print(f"⚠️ Gagal menemukan form login: {e}")

        # =========================================================
        # 2. BUKA HALAMAN EXPORT
        # =========================================================
        print("[*] Membuka halaman Izin Prinsip Export...")
        driver.get("https://scm.nusadaya.net/izin-prinsip/export")
        time.sleep(5)

        # =========================================================
        # 3. CEK HASIL EXPORT (TUNGGU DOWNLOAD / BACA JSON / SCRAPE TABEL)
        # =========================================================
        
        # Cek apakah halaman langsung menampilkan JSON mentah
        try:
            body_text = driver.find_element(By.TAG_NAME, "body").text
            if body_text.strip().startswith('[') or body_text.strip().startswith('{'):
                print("[*] Halaman langsung mengembalikan format JSON.")
                data_hasil_scraping = json.loads(body_text)
        except:
            pass

        # Jika bukan JSON mentah, cek apakah ada file yang terunduh
        if not data_hasil_scraping:
            list_files = glob.glob(os.path.join(download_dir, "*.*"))
            export_files = [f for f in list_files if f.endswith(('.xlsx', '.xls', '.csv'))]
            
            if export_files:
                latest_file = max(export_files, key=os.path.getctime)
                print(f"[*] File terdeteksi terunduh: {os.path.basename(latest_file)}")
                time.sleep(2) # Pastikan file selesai diunduh
                data_hasil_scraping = parse_downloaded_file(latest_file)
                try:
                    os.remove(latest_file)
                except:
                    pass

        # Jika masih kosong, coba scrape tabel HTML
        if not data_hasil_scraping:
            print("[*] Tidak ada JSON/File unduhan. Mencoba scrape tabel HTML...")
            data_hasil_scraping = scrape_table_to_json(driver)

        if data_hasil_scraping:
            status_eksekusi = "BERHASIL"
            print(f"[*] Berhasil mengambil {len(data_hasil_scraping)} baris data.")
            for row in data_hasil_scraping:
                row["tanggal_bot_eksekusi"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        else:
            print("❌ Tidak ada data yang berhasil diambil dari halaman export.")
            # Buat data error agar memaksa menimpa file JSON lama (dummy Beras/Gula hilang)
            data_hasil_scraping = [{
                "status": "GAGAL_SCRAPING", 
                "pesan": "Bot berhasil login tapi tidak menemukan data di halaman export. Periksa struktur halaman / screenshot error.",
                "tanggal_bot_eksekusi": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }]
            driver.save_screenshot("error_scm.png")
            push_json_ke_github("error_scm.png", "error_scm.png", commit_msg="Add error screenshot")

    except Exception as e:
        print(f"❌ Error fatal saat menjalankan bot: {e}")
        data_hasil_scraping = [{
            "status": "ERROR_SCRIPT", 
            "pesan": str(e),
            "tanggal_bot_eksekusi": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }]
        if driver:
            driver.save_screenshot("error_scm.png")
            push_json_ke_github("error_scm.png", "error_scm.png", commit_msg="Add error screenshot")
    finally:
        # =========================================================
        # 4. SIMPAN & PUSH HASIL JSON (SELALU DIEKSEKUSI)
        # =========================================================
        nama_file_json = "data_scm.json"
        try:
            with open(nama_file_json, "w", encoding="utf-8") as f:
                json.dump(data_hasil_scraping, f, indent=4, ensure_ascii=False)
            print(f"[*] Data {status_eksekusi} disimpan ke file lokal: {nama_file_json}")
            
            print("[*] Mengirim file JSON ke repository GitHub...")
            push_json_ke_github(nama_file_json, nama_file_json)
        except Exception as e:
            print(f"Gagal menyimpan JSON: {e}")
            
        if driver:
            driver.quit()
            print("[*] Browser ditutup.")

if __name__ == "__main__":
    main()
