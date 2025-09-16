#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Shodan .env MAIL_USERNAME Hunter
- Rotasi API key dari api.txt saat error/rate limit (lanjut page yang sama)
- Deep idle setiap 10 page
- Jika semua API key error, deep idle 10 menit lalu lanjut lagi (tanpa exit)
- Dedup (in-memory + load dari output jika ada)
- Resume-friendly
- Progress bar & banner
"""

import time
import random
import shodan
import sys
import os
from datetime import datetime
from colorama import Fore, Style, init

init(autoreset=True)

# ======= KONFIGURASI =======
QUERY = 'asn:"as16509" http.status:200 port:80'   # ubah sesuai kebutuhan
API_LIST_FILE = "api.txt"                          # satu API key per baris
OUTPUT_FILE = f"shodan_resukts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

# Jeda request (pelan-pelan)
BASE_DELAY = 1.8
JITTER = 1.4

# Deep idle per X halaman
DEEP_IDLE_EVERY_PAGES = 10               # <- sesuai permintaan: setiap 10 page
DEEP_IDLE_BASE = 8.0
DEEP_IDLE_JITTER = 6.0

# Cooldown global ketika SEMUA API key error
GLOBAL_DEEP_IDLE_SECONDS = 600           # 10 menit

# Retry/backoff per key sebelum ganti key
MAX_RETRIES_PER_KEY = 2
BACKOFF_BASE = 4.0
BACKOFF_FACTOR = 2.0

# ======= UI Helpers =======
def type_effect(text, delay=0.01, color=Fore.GREEN):
    for ch in text:
        sys.stdout.write(color + ch)
        sys.stdout.flush()
        time.sleep(delay)
    print(Style.RESET_ALL, end="")

def progress_bar(label="scanning", seconds=1.6, width=28, color=Fore.GREEN):
    start = time.time()
    sys.stdout.write(color + f"{label}: [" + " " * width + "] 0%")
    sys.stdout.flush()
    while True:
        elapsed = time.time() - start
        ratio = min(1.0, elapsed / seconds)
        filled = int(ratio * width)
        bar = "#" * filled + " " * (width - filled)
        percent = int(ratio * 100)
        sys.stdout.write("\r" + color + f"{label}: [{bar}] {percent}%")
        sys.stdout.flush()
        if ratio >= 1.0:
            break
        time.sleep(0.05)
    print(Style.RESET_ALL)

def banner():
    print(Fore.GREEN + Style.BRIGHT + r"""
███████╗ █████╗ ██╗███╗   ██╗     ██████╗ ███████╗██╗    ██╗
╚══███╔╝██╔══██╗██║████╗  ██║    ██╔══██╗██╔════╝██║    ██║
  ███╔╝ ███████║██║██╔██╗ ██║    ██████╔╝█████╗  ██║ █╗ ██║
 ███╔╝  ██╔══██║██║██║╚██╗██║    ██╔═══╝ ██╔══╝  ██║███╗██║
███████╗██║  ██║██║██║ ╚████║    ██║     ███████╗╚███╔███╔╝
╚══════╝╚═╝  ╚═╝╚═╝╚═╝  ╚═══╝    ╚══════╝ ╚══╝╚══╝
""")

# ======= UTIL =======
def load_api_keys(path):
    if not os.path.exists(path):
        print(Fore.RED + f"[ERROR] File {path} tidak ditemukan. Buat file berisi daftar API key (satu per baris)." + Style.RESET_ALL)
        sys.exit(1)
    keys = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            keys.append(s)
    if not keys:
        print(Fore.RED + f"[ERROR] Tidak ada API key valid di {path}." + Style.RESET_ALL)
        sys.exit(1)
    return keys

def polite_sleep_short():
    time.sleep(BASE_DELAY + random.uniform(0, JITTER))

# ======= CORE =======
def run():
    banner()
    type_effect("=== SHODAN .ENV MAIL_USERNAME HUNTER (Auto-rotate API + Deep Idle) ===\n", 0.008)

    api_keys = load_api_keys(API_LIST_FILE)
    key_idx = 0
    api = shodan.Shodan(api_keys[key_idx])

    # dedup: load data lama jika rerun
    seen = set()
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            for line in f:
                ip = line.strip()
                if ip:
                    seen.add(ip)

    f_out = open(OUTPUT_FILE, "a", encoding="utf-8")

    page = 1
    empty_pages_in_a_row = 0
    total_new = 0

    while True:
        # Melacak berapa banyak API key yang sudah dicoba untuk PAGE saat ini
        tried_keys_this_page = set()
        retries = 0

        while True:
            try:
                type_effect(f"\n[KEY {key_idx+1}/{len(api_keys)}] [INFO] Page {page} → {QUERY}\n", 0.003, Fore.CYAN)
                progress_bar(label="scanning", seconds=random.uniform(1.2, 2.1))
                results = api.search(QUERY, page=page)
                break  # sukses dapat results
            except shodan.APIError as e:
                emsg = str(e).lower()
                is_rate = any(k in emsg for k in ["rate limit", "too many requests", "429", "temporarily unavailable", "service unavailable"])
                is_auth = any(k in emsg for k in ["invalid key", "unauthorized", "forbidden"])

                if is_rate and retries < MAX_RETRIES_PER_KEY:
                    delay = BACKOFF_BASE * (BACKOFF_FACTOR ** retries) + random.uniform(0, 1.5)
                    type_effect(f"[WARN] API error: {e}. Backoff {delay:.1f}s lalu retry (#{retries+1}) ...\n", 0.003, Fore.YELLOW)
                    progress_bar(label="cooldown", seconds=delay, width=32, color=Fore.YELLOW)
                    retries += 1
                    continue

                # tandai key sekarang sudah dicoba untuk page ini
                tried_keys_this_page.add(api_keys[key_idx])

                # Jika SEMUA key sudah dicoba & gagal → deep idle 10 menit lalu reset percobaan key pada page ini
                if len(tried_keys_this_page) >= len(api_keys):
                    type_effect(f"[GLOBAL-COOLDOWN] Semua API key error pada Page {page}. Deep idle {GLOBAL_DEEP_IDLE_SECONDS//60} menit...\n", 0.004, Fore.MAGENTA)
                    progress_bar(label="deep idle (global)", seconds=GLOBAL_DEEP_IDLE_SECONDS, width=40, color=Fore.CYAN)
                    # reset siklus key & percobaan untuk page ini
                    tried_keys_this_page = set()
                    retries = 0
                    # mulai lagi dari key saat ini atau putar ke key berikutnya agar distribusi merata
                    key_idx = (key_idx + 1) % len(api_keys)
                    api = shodan.Shodan(api_keys[key_idx])
                    continue

                # ganti key & ulangi request page yang sama
                type_effect(f"[SWITCH] Ganti API key karena error: {e}\n", 0.003, Fore.MAGENTA)
                key_idx = (key_idx + 1) % len(api_keys)
                api = shodan.Shodan(api_keys[key_idx])
                retries = 0
                time.sleep(0.8)
                continue

        matches = results.get("matches", [])
        if not matches:
            empty_pages_in_a_row += 1
            type_effect(f"[INFO] Page {page} kosong ({empty_pages_in_a_row}x berturut-turut).\n", 0.003, Fore.WHITE)
            # Dua page kosong berturut-turut → anggap habis
            if empty_pages_in_a_row >= 2:
                type_effect("[DONE] Tidak ada hasil lagi. Mengakhiri.\n", 0.004, Fore.CYAN)
                break
        else:
            empty_pages_in_a_row = 0

        if matches:
            progress_bar(label="parsing", seconds=random.uniform(0.5, 1.0), width=20)
            added_this_page = 0
            for r in matches:
                ip = r.get("ip_str")
                if not ip or ip in seen:
                    continue
                seen.add(ip)
                f_out.write(ip + "\n")
                type_effect(ip + "\n", 0.0018, Fore.GREEN)
                total_new += 1
                added_this_page += 1

            type_effect(f"[PAGE {page}] IP baru: {added_this_page}\n", 0.003, Fore.CYAN)

        # next page
        page += 1

        # deep idle tiap 10 page
        if (page - 1) % DEEP_IDLE_EVERY_PAGES == 0:
            seconds = DEEP_IDLE_BASE + random.uniform(0, DEEP_IDLE_JITTER)
            type_effect(f"[IDLE] Deep idle setiap {DEEP_IDLE_EVERY_PAGES} page: {seconds:.1f}s\n", 0.003, Fore.CYAN)
            progress_bar(label="deep idle", seconds=seconds, width=26, color=Fore.CYAN)
        else:
            # jeda antar page biasa
            polite_sleep_short()

    f_out.close()
    type_effect(f"\n[SELESAI] Total IP baru ditambahkan: {total_new}\n", 0.008, Fore.CYAN)
    type_effect(f"[FILE] Output: {OUTPUT_FILE}\n", 0.008, Fore.CYAN)

if __name__ == "__main__":
    run()
