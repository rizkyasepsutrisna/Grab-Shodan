# 🔎 Shodan Scanner  

A lightweight Python tool to **search Shodan with style** 🚀.  
Features built-in **API key rotation**, **deduplication**, and **auto-resume output**. Perfect for **defensive security research**, **asset inventory**, and **compliance audits**.  

> ⚠️ Ethical Use Only — Run this on assets you **own** or have **permission** to test.  

---

## ✨ Features

- 🔁 Auto **API Key rotation** when rate-limited  
- 🧹 **Duplicate-free** results (memory + file-based)  
- ⏯️ **Resume-friendly** output (safe to rerun)  
- ⏱️ Built-in **backoff & jitter** for smooth Shodan usage  
- 🎨 Fancy terminal banner + progress bar  

---

## ⚡ Quick Start

```bash
git clone https://github.com/yourname/shodan-scanner
cd shodan-scanner
pip install shodan colorama
python3 grabshodan.py
```

- Put your Shodan API keys in `api.txt` (one per line).  
- Edit the `QUERY` variable inside the script to match your search.  
- Results are saved in `shodan_results_TIMESTAMP.txt`.  

---

## 🛠 Example Query

```python
QUERY = 'net:203.0.113.0/24 port:443'
```

Output (example):

```
198.51.100.42
203.0.113.10
```

---

## 🧩 Use Cases

- ✅ Internal asset inventory  
- ✅ Compliance/security audits  
- ✅ Prioritizing patch management  

---

## ☕ Support

If you find this useful, consider buying me a coffee 💙  

👉 [Saweria Donations](https://saweria.co/zainpewpewpew)  
