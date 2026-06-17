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
            with
