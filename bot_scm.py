import time
import requests
import json
import os
import io
import sys
import traceback

from github import Github
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from openpyxl import load_workbook


def upload_to_github(data, filename="data_scm.json"):
    """
    Upload data JSON ke repository GitHub.
    Jika file sudah ada, akan di-update. Jika belum, akan dibuat baru.
    """
    token = os.environ.get('GITHUB_TOKEN')
    if not token:
        print("[ERROR] GITHUB_TOKEN tidak ditemukan di environment variables!")
        return False

    try:
        g = Github(token)
        # Menuju repository tujuan sesuai spesifikasi Anda
        repo = g.get_repo("upkasbu-dotcom/data-spk")
        file_content = json.dumps(data, indent=4, ensure_ascii=False)

        try:
            contents = repo.get_contents(filename)
            repo.update_file(
                path=contents.path,
                message="Update data SCM otomatis via GitHub Actions",
                content=file_content,
                sha=contents.sha
            )
            print(f"[OK] File {filename} berhasil diperbarui di GitHub.")
        except Exception:
            repo.create_file(
                path=filename,
                message="Commit data SCM pertama",
                content=file_content
            )
            print(f"[OK] File {filename} berhasil dibuat di GitHub.")

        return True

    except Exception as e:
        print(f"[ERROR] Gagal upload ke GitHub: {e}")
        traceback.print_exc()
        return False


def create_chrome_driver():
    """
    Membuat instance Chrome WebDriver yang kompatibel dengan GitHub Actions.
    """
    options = Options()
    options.add_argument('--headless=new')           # Headless mode terbaru
    options.add_argument('--no-sandbox')             # Wajib untuk CI/CD
    options.add_argument('--disable-dev-shm-usage')  # Menghindari crash di container
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--disable-extensions')
    options.add_argument('--disable-software-rasterizer')
    options.add_argument('--remote-allow-origins=*')
    options.add_argument(
        '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    )

    import shutil
    chromedriver_path = shutil.which('chromedriver')
    if chromedriver_path:
        print(f"[INFO] ChromeDriver ditemukan di: {chromedriver_path}")
        service = Service(executable_path=chromedriver_path)
        driver = webdriver.Chrome(service=service, options=options)
    else:
        print("[WARNING] ChromeDriver tidak ditemukan di PATH, menggunakan default...")
        driver = webdriver.Chrome(options=options)

    driver.set_page_load_timeout(60)
    return driver


def jalankan_bot():
    """
    Fungsi utama bot SCM:
    1. Login ke SCM Nusadaya
    2. Download file Excel surat perintah kerja
    3. Ekstrak data dan Upload data ke GitHub berbentuk JSON
    """
    print("=" * 50)
    print("=== [START] Operasi Bot SCM ===")
    print("=" * 50)

    username = os.environ.get('USERNAME')
    password = os.environ.get('PASSWORD')

    if not username or not password:
        print("[ERROR] USERNAME atau PASSWORD tidak ditemukan di environment variables!")
        print("[ERROR] Pastikan secrets sudah dikonfigurasi di repository Settings > Secrets.")
        return False

    driver = create_chrome_driver()

    try:
        # ===== STEP 1: Login =====
        print("[STEP 1] Membuka halaman login...")
        driver.get("https://scm.nusadaya.net/login")
        wait = WebDriverWait(driver, 30)

        # Isi username/email (Perbaikan sintaks pencarian XPATH yang typo sebelumnya)
        print("[STEP 1] Mengisi username...")
        email_input = wait.until(
            EC.presence_of_element_located(
                (By.XPATH, "//input[@type='text' or @placeholder='Email atau NIP']")
            )
        )
        email_input.clear()
        email_input.send_keys(username)

        # Isi password
        print("[STEP 1] Mengisi password...")
        password_input = driver.find_element(By.XPATH, "//input[@type='password']")
        password_input.clear()
        password_input.send_keys(password)

        # Klik tombol login
        print("[STEP 1] Klik tombol Login...")
        login_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Log in')]")
        login_button.click()

        print("[STEP 1] Menunggu redirect setelah login...")
        time.sleep(5) 

        try:
            wait.until(
                EC.any_of(
                    EC.url_contains("dashboard"),
                    EC.url_contains("home"),
                    EC.url_contains("surat-perintah-kerja"),
                    EC.presence_of_element_located((By.XPATH, "//nav | //header | //sidebar"))
                )
            )
            print("[STEP 1] Login berhasil! Halaman berhasil dimuat.")
        except Exception:
            print("[WARNING] Tidak dapat memverifikasi login berhasil, melanjutkan...")
            print(f"[WARNING] URL saat ini: {driver.current_url}")

        # ===== STEP 2: Download Excel =====
        print("[STEP 2] Mengambil session cookies...")
        session_cookies = {c['name']: c['value'] for c in driver.get_cookies()}
        print(f"[STEP 2] Berhasil mengambil {len(session_cookies)} cookies.")

        headers = {
            'Referer': 'https://scm.nusadaya.net/surat-perintah-kerja',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                          'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }

        download_url = "https://scm.nusadaya.net/surat-perintah-kerja/export"
        print(f"[STEP 2] Mendownload dari: {download_url}")

        max_retries = 3
        response_dl = None

        for attempt in range(1, max_retries + 1):
            try:
                response_dl = requests.get(
                    download_url,
                    cookies=session_cookies,
                    headers=headers,
                    timeout=60
                )
                if response_dl.status_code == 200:
                    print(f"[STEP 2] Download berhasil! (Attempt {attempt})")
                    break
                else:
                    print(f"[STEP 2] Status code: {response_dl.status_code} (Attempt {attempt}/{max_retries})")
            except requests.exceptions.RequestException as e:
                print(f"[STEP 2] Request error: {e} (Attempt {attempt}/{max_retries})")

            if attempt < max_retries:
                wait_time = attempt * 5
                print(f"[STEP 2] Menunggu {wait_time} detik sebelum retry...")
                time.sleep(wait_time)

        # ===== STEP 3: Proses & Upload =====
        if response_dl and response_dl.status_code == 200:
            print("[STEP 3] Memproses file Excel...")
            try:
                wb = load_workbook(filename=io.BytesIO(response_dl.content), data_only=True)
                all_data = {}

                for sheet_name in wb.sheetnames:
                    sheet = wb[sheet_name]
                    rows = []
                    for row in sheet.iter_rows(values_only=True):
                        rows.append([cell if cell is not None else "" for cell in row])
                    all_data[sheet_name] = rows

                print(f"[STEP 3] Berhasil membaca {len(all_data)} sheet: {list(all_data.keys())}")

                print("[STEP 3] Mengupload ke GitHub...")
                success = upload_to_github(all_data)

                if success:
                    print("[STEP 3] Data berhasil diupload ke GitHub!")
                else:
                    print("[STEP 3] Gagal mengupload ke GitHub!")

            except Exception as e:
                print(f"[ERROR] Gagal memproses file Excel: {e}")
                traceback.print_exc()
        else:
            status = response_dl.status_code if response_dl else "No response"
            print(f"[ERROR] Gagal download file! Status: {status}")
            return False

        print("=" * 50)
        print("=== [FINISH] Operasi Selesai ===")
        print("=" * 50)
        return True

    except Exception as e:
        print(f"[FATAL ERROR] Terjadi error: {e}")
        traceback.print_exc()
        return False

    finally:
        driver.quit()
        print("[INFO] Browser ditutup.")


if __name__ == "__main__":
    result = jalankan_bot()
    sys.exit(0 if result else 1)
