import time
import threading
import urllib.request
import urllib.parse
import json
import os
from datetime import datetime, date



# Manually load env variables from backend/.env
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
if os.path.exists(env_path):
    with open(env_path, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ[k.strip()] = v.strip()

from datetime import datetime, date


# Parse Supabase credentials from frontend/.env
def get_supabase_credentials():
    url = os.environ.get("VITE_SUPABASE_URL")
    key = os.environ.get("VITE_SUPABASE_PUBLISHABLE_KEY")
    if url and key:
        return url, key
        
    try:
        env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend", ".env")
        if os.path.exists(env_path):
            with open(env_path, "r") as f:
                for line in f:
                    if line.startswith("VITE_SUPABASE_URL="):
                        url = line.strip().split("=")[1].strip()
                    elif line.startswith("VITE_SUPABASE_PUBLISHABLE_KEY="):
                        key = line.strip().split("=")[1].strip()
    except Exception as e:
        print(f"Error reading frontend .env inside bot: {e}")
    return url, key

# Call Supabase REST API
def query_supabase(endpoint: str, method: str = "GET", body: dict = None) -> list:
    url, key = get_supabase_credentials()
    if not url or not key:
        return []
    
    full_url = f"{url.rstrip('/')}/rest/v1/{endpoint}"
    data = None
    if body:
        data = json.dumps(body).encode("utf-8")
        
    req = urllib.request.Request(
        full_url,
        data=data,
        headers={
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation" if method == "POST" else ""
        },
        method=method
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as res:
            res_content = res.read().decode("utf-8")
            if res_content:
                return json.loads(res_content)
            return []
    except Exception as e:
        print(f"Failed to query Supabase REST API ({method} {endpoint}): {e}")
        return []

# Configure Bot Commands Menu in Telegram
def set_bot_commands(bot_token: str):
    url = f"https://api.telegram.org/bot{bot_token}/setMyCommands"
    payload = {
        "commands": [
            {"command": "start", "description": "Panduan bot & memulai"},
            {"command": "status", "description": "Cek jadwal rutinitas Pagi (AM) & Malam (PM)"},
            {"command": "exp", "description": "Cek kedaluwarsa PAO seluruh produk"},
            {"command": "safety", "description": "Cek apakah 2 produk spesifik aman dipakai bersamaan"},
            {"command": "safety_all", "description": "Analisis SEMUA produk: cari konflik & rekomendasikan AM/PM"},
            {"command": "terapkan_rekomendasi", "description": "Terapkan rekomendasi rutinitas AI ke jadwal Anda"},
            {"command": "tambah_produk", "description": "Tambah produk baru (AI auto-detect bahan aktif)"},
            {"command": "daftar_produk", "description": "Tampilkan semua produk di inventaris"},
            {"command": "cancel", "description": "Batal proses saat ini"}
        ]
    }
    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            res = json.loads(response.read().decode("utf-8"))
            if res.get("ok"):
                print("[Skindaily Bot] Commands menu configured successfully.")
    except Exception as e:
        print(f"Failed to configure bot commands: {e}")

# Call Gemini API to automatically detect ingredients for a product
def call_gemini_to_find_ingredients(brand: str, name: str) -> str:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return ""
        
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite:generateContent?key={api_key}"
    prompt = f"""
    Sebutkan bahan aktif utama (active ingredients) yang terdapat pada produk skincare berikut:
    Brand/Merek: {brand}
    Nama Produk: {name}
    
    Kembalikan HANYA daftar bahan aktif utama dipisahkan dengan koma (contoh: "Salicylic Acid, Niacinamide, Centella Asiatica"). 
    Jika tidak tahu atau tidak yakin, kembalikan "Tidak diketahui".
    Jangan berikan kalimat penjelasan apa pun. Hanya nama bahan aktif saja.
    """
    
    payload = {
        "contents": [{"parts": [{"text": prompt}]}]
    }
    
    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=15) as response:
            res_body = json.loads(response.read().decode("utf-8"))
            text_response = res_body["candidates"][0]["content"]["parts"][0]["text"]
            ans = text_response.strip()
            if "tidak diketahui" in ans.lower():
                return ""
            return ans
    except Exception as e:
        print(f"Gemini auto-ingredients fetch failed: {e}")
        return ""

# Call Gemini API directly for image analysis
def call_gemini_api_for_image(prompt: str, image_bytes: bytes, mime_type: str) -> dict:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return {"status": "ERROR", "reason": "Gemini API Key is not configured."}
        
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite:generateContent?key={api_key}"
    import base64
    base64_image = base64.b64encode(image_bytes).decode("utf-8")
    
    parts = [
        {"text": prompt},
        {
            "inlineData": {
                "mimeType": mime_type,
                "data": base64_image
            }
        }
    ]
    
    payload = {
        "contents": [{"parts": parts}],
        "generationConfig": {
            "responseMimeType": "application/json"
        }
    }
    
    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            res_body = json.loads(response.read().decode("utf-8"))
            text_response = res_body["candidates"][0]["content"]["parts"][0]["text"]
            return json.loads(text_response.strip())
    except Exception as e:
        return {"status": "ERROR", "reason": f"Gagal memanggil Gemini API: {str(e)}"}

# Call Gemini API to analyze ALL products at once
def call_gemini_for_safety_all(products: list) -> dict:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return {"conflicts": [], "recommendation": "Kunci API Gemini belum dikonfigurasi di file .env."}

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite:generateContent?key={api_key}"

    prod_list_str = ""
    for idx, p in enumerate(products, 1):
        ing = p.get("ingredients") or "Tidak diketahui"
        prod_list_str += f"{idx}. Merek: {p['brand']}, Nama: {p['name']}, Bahan Aktif: {ing}\n"

    prompt = f"""Analisis keamanan layering (penggabungan penggunaan bersamaan) untuk semua produk skincare berikut:

{prod_list_str}

Tentukan apakah ada kombinasi produk yang saling berbenturan (bahaya/hati-hati), dan berikan rekomendasi pembagian rutinitas penggunaan yang aman.

Kembalikan respon hanya dalam bentuk JSON dengan format berikut:
{{
  "conflicts": [
    {{
      "product_a": "Nama lengkap Produk A",
      "product_b": "Nama lengkap Produk B",
      "status": "BAHAYA" atau "HATI-HATI",
      "reason": "Penjelasan singkat dalam Bahasa Indonesia."
    }}
  ],
  "recommendation": "Rekomendasi detail pembagian rutinitas harian (AM/PM) dalam Bahasa Indonesia."
}}

Kembalikan HANYA JSON."""

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json"}
    }

    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url, data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            res_body = json.loads(response.read().decode("utf-8"))
            text_response = res_body["candidates"][0]["content"]["parts"][0]["text"]
            return json.loads(text_response.strip())
    except Exception as e:
        return {"conflicts": [], "recommendation": f"Gagal terhubung dengan Gemini API: {str(e)}"}

# Call Gemini API directly for safety analysis
def call_gemini_for_safety(ing_a: str, ing_b: str) -> dict:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return {"status": "ERROR", "reason": "Kunci API Gemini belum dikonfigurasi di file .env."}
        
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite:generateContent?key={api_key}"
    prompt = f"""
    Analisis keamanan layering (penggabungan penggunaan bersamaan) antara kedua bahan skincare ini:
    Bahan A: {ing_a}
    Bahan B: {ing_b}
    
    Berikan kesimpulan dan penjelasan singkat dalam Bahasa Indonesia.
    Kembalikan respon hanya dalam bentuk JSON dengan format berikut:
    {{
      "status": "AMAN" atau "BAHAYA" atau "HATI-HATI",
      "reason": "Penjelasan singkat (maksimal 3 kalimat) mengapa aman/bahaya/perlu hati-hati."
    }}
    
    Kembalikan HANYA JSON.
    """
    
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseMimeType": "application/json"
        }
    }
    
    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=20) as response:
            res_body = json.loads(response.read().decode("utf-8"))
            text_response = res_body["candidates"][0]["content"]["parts"][0]["text"]
            return json.loads(text_response.strip())
    except Exception as e:
        return {"status": "ERROR", "reason": f"Gagal terhubung dengan Gemini API: {str(e)}"}

# Send reply message to Telegram user
def send_telegram_reply(bot_token: str, chat_id: int, text: str):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }
    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            pass
    except Exception as e:
        print(f"Failed to send bot reply: {e}")

# Dictionary to hold user states for interactive commands
user_states = {}

def handle_photo_message(bot_token: str, chat_id: int, photo: list):
    send_telegram_reply(bot_token, chat_id, "📸 <i>Menerima foto produk. Mengunduh dan menganalisis label/kemasan menggunakan Gemini AI...</i>")
    
    try:
        # Get largest photo size
        largest_photo = photo[-1]
        file_id = largest_photo["file_id"]
        
        # Get file path from Telegram
        get_file_url = f"https://api.telegram.org/bot{bot_token}/getFile?file_id={file_id}"
        req = urllib.request.Request(get_file_url)
        with urllib.request.urlopen(req, timeout=15) as res:
            res_body = json.loads(res.read().decode("utf-8"))
            if not res_body.get("ok"):
                send_telegram_reply(bot_token, chat_id, "❌ Gagal mendapatkan informasi file dari Telegram.")
                return
            file_path = res_body["result"]["file_path"]
            
        # Download the file
        download_url = f"https://api.telegram.org/file/bot{bot_token}/{file_path}"
        req_download = urllib.request.Request(download_url)
        with urllib.request.urlopen(req_download, timeout=30) as res_img:
            image_bytes = res_img.read()
            
        # Call Gemini
        prompt = """
        Analisis gambar skincare ini. Ekstrak informasi berikut dan kembalikan hanya dalam format JSON terstruktur:
        {
          "brand": "Nama Brand/Merek produk (contoh: 'Hada Labo', 'Facetology', 'The Ordinary')",
          "name": "Nama lengkap produk (contoh: 'Gokujyun Premium Lotion', 'Triple Care Sunscreen')",
          "active_ingredients": ["Daftar bahan aktif utama yang tertera, contoh: 'Niacinamide', 'Hyaluronic Acid', 'Retinol', 'Salicylic Acid'"]
        }
        
        PENTING:
        - Jika tulisan tidak jelas, berikan tebakan terbaik Anda.
        - Kembalikan HANYA JSON object. Jangan tambahkan penjelasan lain.
        """
        
        # Determine mime type from file path extension
        mime_type = "image/jpeg"
        if file_path.lower().endswith(".png"):
            mime_type = "image/png"
        elif file_path.lower().endswith(".webp"):
            mime_type = "image/webp"
            
        scan_result = call_gemini_api_for_image(prompt, image_bytes, mime_type)
        
        if "status" in scan_result and scan_result["status"] == "ERROR":
            send_telegram_reply(bot_token, chat_id, f"❌ Gagal menganalisis gambar: {scan_result.get('reason')}")
            return
            
        brand = scan_result.get("brand", "Unknown")
        name = scan_result.get("name", "Unknown")
        active_ingredients = scan_result.get("active_ingredients", [])
        ingredients_str = ", ".join(active_ingredients) if isinstance(active_ingredients, list) else str(active_ingredients)
        
        # Save state to continue WAITING_EXPIRY
        user_states[chat_id] = {
            "state": "WAITING_EXPIRY",
            "data": {
                "brand": brand,
                "name": name,
                "ingredients": ingredients_str
            }
        }
        
        reply_msg = (
            "✨ <b>Hasil Deteksi Label Produk oleh Gemini AI:</b>\n\n"
            f"Brand: <b>{brand}</b>\n"
            f"Nama: <b>{name}</b>\n"
            f"Bahan Aktif: <code>{ingredients_str}</code>\n\n"
            "Lanjut! Masukkan <b>Bulan & Tahun Kedaluwarsa (Expired)</b> produk ini dengan format <code>MM-YYYY</code> (contoh: ketik <code>08-2027</code> jika kadaluarsa Agustus 2027):"
        )
        send_telegram_reply(bot_token, chat_id, reply_msg)
        
    except Exception as e:
        send_telegram_reply(bot_token, chat_id, f"❌ Terjadi kesalahan saat memproses gambar: {str(e)}")

# Process incoming bot command
def handle_bot_message(bot_token: str, message: dict):
    chat = message.get("chat", {})
    chat_id = chat.get("id")
    text = message.get("text", "").strip()
    
    if not chat_id:
        return

    # Check for photo messages first to support product scanning
    photo = message.get("photo")
    if photo:
        handle_photo_message(bot_token, chat_id, photo)
        return
        
    if not text:
        return

    # Check for cancel command at any time
    if text.startswith("/cancel"):
        if chat_id in user_states:
            del user_states[chat_id]
        send_telegram_reply(bot_token, chat_id, "❌ <b>Proses pengisian data dibatalkan.</b>")
        return

    # If user is in an active conversational state, handle that first!
    if chat_id in user_states:
        state_info = user_states[chat_id]
        current_state = state_info.get("state")
        state_data = state_info.get("data", {})

        # --- FLOW TAMBAH PRODUK ---
        if current_state == "WAITING_BRAND":
            state_data["brand"] = text
            state_info["state"] = "WAITING_NAME"
            send_telegram_reply(
                bot_token, 
                chat_id, 
                "👍 Merek disimpan!\n\nSekarang, masukkan <b>Nama Varian Produk</b> Anda (contoh: <code>Gokujyun Lotion</code>, <code>Triple Care Sunscreen</code>):"
            )
            return

        elif current_state == "WAITING_NAME":
            state_data["name"] = text
            brand = state_data["brand"]
            name = text
            
            send_telegram_reply(
                bot_token, 
                chat_id, 
                f"🔍 <i>Menganalisis bahan aktif untuk <b>{brand} - {name}</b> secara otomatis menggunakan Gemini AI...</i>"
            )
            
            # Detect ingredients using Gemini
            detected_ingredients = call_gemini_to_find_ingredients(brand, name)
            
            if detected_ingredients:
                state_data["ingredients"] = detected_ingredients
                state_info["state"] = "WAITING_EXPIRY"
                send_telegram_reply(
                    bot_token, 
                    chat_id, 
                    f"✨ <b>Bahan Aktif dideteksi Gemini AI:</b>\n<code>{detected_ingredients}</code>\n\n"
                    "Lanjut! Masukkan <b>Bulan & Tahun Kedaluwarsa (Expired)</b> produk ini dengan format <code>MM-YYYY</code> (contoh: ketik <code>08-2027</code> jika kadaluarsa Agustus 2027):"
                )
            else:
                # Gemini could not detect it, fallback to manual input
                state_info["state"] = "WAITING_INGREDIENTS"
                send_telegram_reply(
                    bot_token, 
                    chat_id, 
                    "⚠️ <i>Gemini tidak yakin dengan bahan aktif produk ini.</i>\n\n"
                    "Silakan masukkan <b>Bahan Aktif utama</b> secara manual (pisahkan koma jika lebih dari satu, contoh: <code>Salicylic Acid</code>), atau ketik <b>tidak ada</b> jika tidak tahu:"
                )
            return

        elif current_state == "WAITING_INGREDIENTS":
            state_data["ingredients"] = "" if text.lower() == "tidak ada" else text
            state_info["state"] = "WAITING_EXPIRY"
            send_telegram_reply(
                bot_token, 
                chat_id, 
                "👍 Bahan aktif disimpan!\n\nMasukkan <b>Bulan & Tahun Kedaluwarsa (Expired)</b> produk ini dengan format <code>MM-YYYY</code> (contoh: ketik <code>08-2027</code> jika kadaluarsa Agustus 2027):"
            )
            return

        elif current_state == "WAITING_EXPIRY":
            try:
                today = date.today()
                # Parse Month & Year
                clean_text = text.replace("/", "-").strip()
                parts = clean_text.split("-")
                if len(parts) != 2:
                    raise ValueError()
                
                exp_month = int(parts[0])
                exp_year = int(parts[1])
                
                # Support simple 2-digit years (e.g. 27 -> 2027)
                if exp_year < 100:
                    exp_year += 2000
                    
                if not (1 <= exp_month <= 12) or exp_year < 2000:
                    raise ValueError()
                
                # Expiry date target
                expiry_dt = date(exp_year, exp_month, 1)
                
                # Calculate difference in months between today and expiry
                diff_months = (exp_year - today.year) * 12 + (exp_month - today.month)
                if diff_months < 0:
                    diff_months = 0  # Already expired
                
                # We save opened_at as today, and pao_months as the difference in months
                opened_at_str = today.strftime("%Y-%m-%d")
                
                # Save to Supabase
                brand = state_data["brand"]
                name = state_data["name"]
                ingredients = state_data["ingredients"]
                
                payload = {
                    "brand": brand,
                    "name": name,
                    "ingredients": ingredients,
                    "opened_at": opened_at_str,
                    "pao_months": diff_months
                }
                
                query_supabase("products", method="POST", body=payload)
                del user_states[chat_id]
                
                success_msg = (
                    "🎉 <b>Produk Berhasil Disimpan ke Supabase Cloud!</b>\n\n"
                    f"Brand: <b>{brand}</b>\n"
                    f"Nama: <b>{name}</b>\n"
                    f"Bahan Aktif: <b>{ingredients or 'Tidak ada'}</b>\n"
                    f"Kadaluarsa: <b>{exp_month:02d}-{exp_year}</b> (Sisa sekitar {diff_months} Bulan)\n\n"
                    "Produk sekarang aktif terdaftar di menu /exp dan jadwal website!"
                )
                send_telegram_reply(bot_token, chat_id, success_msg)
                return
            except Exception as e:
                send_telegram_reply(
                    bot_token, 
                    chat_id, 
                    "❌ Format tanggal salah! Harap masukkan Bulan & Tahun dengan format <code>MM-YYYY</code> (contoh: ketik <code>08-2027</code>):"
                )
                return

        # --- FLOW SAFETY CHECK ---
        elif current_state == "WAITING_SAFETY_A":
            selected_ingredients = ""
            selected_name = ""
            
            # Check if user entered a number selecting from the list
            try:
                prod_idx = int(text) - 1
                products_list = state_data.get("products_list", [])
                if 0 <= prod_idx < len(products_list):
                    prod = products_list[prod_idx]
                    selected_name = f"{prod['brand']} {prod['name']}"
                    selected_ingredients = prod.get("ingredients") or ""
                    
                    if not selected_ingredients:
                        send_telegram_reply(
                            bot_token,
                            chat_id,
                            f"🔍 <i>Mendeteksi bahan aktif untuk <b>{selected_name}</b> via Gemini AI...</i>"
                        )
                        detected = call_gemini_to_find_ingredients(prod['brand'], prod['name'])
                        if detected:
                            selected_ingredients = detected
                            query_supabase(f"products?id=eq.{prod['id']}", method="PATCH", body={"ingredients": detected})
                        else:
                            selected_ingredients = "Tidak diketahui"
                else:
                    raise ValueError()
            except ValueError:
                # Treat as manual input of ingredients
                selected_ingredients = text
                selected_name = text

            state_data["safety_a_name"] = selected_name
            state_data["safety_a_ing"] = selected_ingredients
            state_info["state"] = "WAITING_SAFETY_B"
            
            # Print the list of products for selection B
            products_list = state_data.get("products_list", [])
            msg = f"👍 <b>Bahan Pertama (A):</b> {selected_name} ({selected_ingredients or 'manual'})\n\n"
            msg += "Sekarang pilih <b>Bahan / Produk Kedua (B)</b>:\n"
            for idx, p in enumerate(products_list, 1):
                msg += f"{idx}. {p['brand']} - {p['name']}\n"
            msg += "\nAtau ketik nama bahan aktif secara manual (contoh: <code>Vitamin C</code>):"
            
            send_telegram_reply(bot_token, chat_id, msg)
            return

        elif current_state == "WAITING_SAFETY_A_MANUAL":
            state_data["safety_a_name"] = text
            state_data["safety_a_ing"] = text
            state_info["state"] = "WAITING_SAFETY_B"
            
            products_list = state_data.get("products_list", [])
            msg = f"👍 <b>Bahan Pertama (A):</b> {text}\n\n"
            msg += "Sekarang pilih <b>Bahan / Produk Kedua (B)</b>:\n"
            for idx, p in enumerate(products_list, 1):
                msg += f"{idx}. {p['brand']} - {p['name']}\n"
            msg += "\nAtau ketik nama bahan aktif secara manual (contoh: <code>Vitamin C</code>):"
            
            send_telegram_reply(bot_token, chat_id, msg)
            return

        elif current_state == "WAITING_SAFETY_B":
            selected_ingredients = ""
            selected_name = ""
            
            # Check if user entered a number selecting from the list
            try:
                prod_idx = int(text) - 1
                products_list = state_data.get("products_list", [])
                if 0 <= prod_idx < len(products_list):
                    prod = products_list[prod_idx]
                    selected_name = f"{prod['brand']} {prod['name']}"
                    selected_ingredients = prod.get("ingredients") or ""
                    
                    if not selected_ingredients:
                        send_telegram_reply(
                            bot_token,
                            chat_id,
                            f"🔍 <i>Mendeteksi bahan aktif untuk <b>{selected_name}</b> via Gemini AI...</i>"
                        )
                        detected = call_gemini_to_find_ingredients(prod['brand'], prod['name'])
                        if detected:
                            selected_ingredients = detected
                            query_supabase(f"products?id=eq.{prod['id']}", method="PATCH", body={"ingredients": detected})
                        else:
                            selected_ingredients = "Tidak diketahui"
                else:
                    raise ValueError()
            except ValueError:
                # Treat as manual input of ingredients
                selected_ingredients = text
                selected_name = text

            ing_a = state_data["safety_a_ing"]
            ing_b = selected_ingredients
            name_a = state_data["safety_a_name"]
            name_b = selected_name
            
            # Reset state
            del user_states[chat_id]
            
            send_telegram_reply(
                bot_token, 
                chat_id, 
                f"🧪 <i>Mengevaluasi layering:\n1. <b>{name_a}</b> ({ing_a})\n2. <b>{name_b}</b> ({ing_b})\n\nMenganalisis via Gemini AI...</i>"
            )
            
            res = call_gemini_for_safety(ing_a, ing_b)
            
            status = res.get("status", "ERROR")
            reason = res.get("reason", "Gagal menganalisis.")
            
            badge = "✅ AMAN"
            if status == "BAHAYA":
                badge = "💥 BAHAYA"
            elif status == "HATI-HATI":
                badge = "⚠️ HATI-HATI"
                
            msg = (
                f"<b>🔬 Laporan Layering AI Skindaily</b>\n\n"
                f"Produk A: <b>{name_a}</b> ({ing_a})\n"
                f"Produk B: <b>{name_b}</b> ({ing_b})\n\n"
                f"Status Keamanan: <b>{badge}</b>\n"
                f"Analisis: {reason}"
            )
            send_telegram_reply(bot_token, chat_id, msg)
            return

        elif current_state == "WAITING_SAFETY_B_MANUAL":
            ing_a = state_data["safety_a_ing"]
            ing_b = text
            name_a = state_data["safety_a_name"]
            name_b = text
            
            # Reset state
            del user_states[chat_id]
            
            send_telegram_reply(
                bot_token, 
                chat_id, 
                f"🧪 <i>Mengevaluasi layering:\n1. <b>{name_a}</b> ({ing_a})\n2. <b>{name_b}</b> ({ing_b})\n\nMenganalisis via Gemini AI...</i>"
            )
            
            res = call_gemini_for_safety(ing_a, ing_b)
            
            status = res.get("status", "ERROR")
            reason = res.get("reason", "Gagal menganalisis.")
            
            badge = "✅ AMAN"
            if status == "BAHAYA":
                badge = "💥 BAHAYA"
            elif status == "HATI-HATI":
                badge = "⚠️ HATI-HATI"
                
            msg = (
                f"<b>🔬 Laporan Layering AI Skindaily</b>\n\n"
                f"Produk A: <b>{name_a}</b> ({ing_a})\n"
                f"Produk B: <b>{name_b}</b> ({ing_b})\n\n"
                f"Status Keamanan: <b>{badge}</b>\n"
                f"Analisis: {reason}"
            )
            send_telegram_reply(bot_token, chat_id, msg)
            return

    # Normal Command Handlers (No Active State)
    if text.startswith("/start"):
        welcome_msg = (
            "🤖 <b>Halo! Selamat datang di Skindaily Bot!</b>\n\n"
            "Saya adalah asisten skincare pribadi Anda. Klik tombol Menu [/] atau ketik:\n"
            "🗓️ /status - Cek jadwal rutinitas Pagi (AM) & Malam (PM)\n"
            "⚠️ /exp - Cek sisa umur kedalwarsa (PAO) produk Anda\n"
            "🛡️ /safety - Cek keamanan layering 2 produk secara interaktif\n"
            "🔬 /safety_all - Analisis keamanan SEMUA produk sekaligus (AI)\n"
            "➕ /tambah_produk - Tambah produk baru secara interaktif (AI Auto-detect bahan aktif)\n"
            "📋 /daftar_produk - Tampilkan seluruh produk Anda\n\n"
            "📸 <b>Kirim Foto Produk</b> - Anda juga dapat langsung mengirimkan foto kemasan/label produk Anda ke bot untuk dideteksi oleh Gemini AI secara otomatis!\n\n"
            "<i>Ketik /cancel kapan saja jika ingin membatalkan pengisian data.</i>"
        )
        send_telegram_reply(bot_token, chat_id, welcome_msg)
        
    elif text.startswith("/status"):
        steps_am = query_supabase("routine_steps?select=*,products(*)&routine_type=eq.AM&order=step_order")
        steps_pm = query_supabase("routine_steps?select=*,products(*)&routine_type=eq.PM&order=step_order")
        
        msg = "<b>🗓️ Jadwal Rutinitas Skincare Hari Ini</b>\n\n"
        
        msg += "☀️ <b>PAGI (AM ROUTINE):</b>\n"
        steps_am_filtered = [s for s in steps_am if s.get("products")]
        if not steps_am_filtered:
            msg += "   - Belum ada jadwal\n"
        else:
            for s in steps_am_filtered:
                msg += f"   {s['step_order']}. {s['products']['brand']} - {s['products']['name']}\n"
                
        msg += "\n🌙 <b>MALAM (PM ROUTINE):</b>\n"
        steps_pm_filtered = [s for s in steps_pm if s.get("products")]
        if not steps_pm_filtered:
            msg += "   - Belum ada jadwal\n"
        else:
            for s in steps_pm_filtered:
                msg += f"   {s['step_order']}. {s['products']['brand']} - {s['products']['name']}\n"
                
        send_telegram_reply(bot_token, chat_id, msg)
        
    elif text.startswith("/exp"):
        products = query_supabase("products?select=*")
        
        if not products:
            send_telegram_reply(bot_token, chat_id, "ℹ️ Belum ada produk terdaftar di inventaris cloud.")
            return
            
        current_date = date.today()
        msg = "<b>⚠️ Status Kedaluwarsa Produk (PAO)</b>\n\n"
        
        expiring = []
        safe = []
        
        for prod in products:
            opened_at_str = prod.get("opened_at")
            pao_months = prod.get("pao_months")
            prod_name = f"<b>{prod['brand']} {prod['name']}</b>"
            
            if opened_at_str and pao_months:
                try:
                    opened_date = datetime.strptime(opened_at_str, "%Y-%m-%d").date()
                    
                    # Calculate expiry date
                    month = opened_date.month + pao_months
                    year = opened_date.year + (month - 1) // 12
                    month = ((month - 1) % 12) + 1
                    expiry_date = opened_date.replace(year=year, month=month)
                    expiry_label = expiry_date.strftime('%d %b %Y')
                    
                    days_remaining = (expiry_date - current_date).days
                    
                    if days_remaining < 0:
                        expiring.append(f"❌ {prod_name}: <b>EXPIRED!</b> ({expiry_label})")
                    elif days_remaining <= 30:
                        expiring.append(f"⚠️ {prod_name}: Sisa <b>{days_remaining} hari</b> (Exp: {expiry_label})")
                    else:
                        safe.append(f"✅ {prod_name}: Sisa {days_remaining} hari (Exp: {expiry_label})")
                except (ValueError, AttributeError):
                    safe.append(f"❓ {prod_name}: Format tanggal salah")
            else:
                safe.append(f"❓ {prod_name}: Data PAO/dibuka tidak lengkap")
                
        full_report = ""
        if expiring:
            full_report += "🚨 <b>EXPIRED / SEBENTAR LAGI:</b>\n" + "\n".join(expiring) + "\n\n"
        if safe:
            full_report += "👍 <b>KONDISI AMAN:</b>\n" + "\n".join(safe)
            
        send_telegram_reply(bot_token, chat_id, full_report)
        
    elif text.startswith("/safety") and not text.startswith("/safety_all"):
        products = query_supabase("products?select=*")
        
        # Initialize state
        user_states[chat_id] = {
            "state": "WAITING_SAFETY_A",
            "data": {
                "products_list": products
            }
        }
        
        msg = "🛡️ <b>Mulai Cek Layering Interaktif</b>\n\n"
        if products:
            msg += "Silakan pilih <b>Bahan / Produk Pertama (A)</b> dengan mengetikkan nomor urutnya:\n"
            for idx, p in enumerate(products, 1):
                msg += f"{idx}. {p['brand']} - {p['name']}\n"
            msg += "\nAtau ketik nama bahan aktif secara manual (contoh: <code>Retinol</code>):"
        else:
            msg += "Silakan masukkan nama <b>Bahan Aktif Pertama (A)</b> secara manual (contoh: <code>Retinol</code>):"
            
        send_telegram_reply(bot_token, chat_id, msg)
        
    elif text.startswith("/tambah_produk"):
        user_states[chat_id] = {
            "state": "WAITING_BRAND",
            "data": {}
        }
        send_telegram_reply(
            bot_token, 
            chat_id, 
            "➕ <b>Mulai Tambah Produk Baru ke Supabase</b>\n\n"
            "Masukkan <b>Merek / Brand</b> produk skincare Anda (contoh: <code>Cerave</code>, <code>Hada Labo</code>, <code>Wardah</code>):\n\n"
            "<i>Ketik /cancel kapan saja untuk membatalkan.</i>"
        )
        
    elif text.startswith("/safety_all"):
        products = query_supabase("products?select=*")
        if not products:
            send_telegram_reply(bot_token, chat_id, "ℹ️ Belum ada produk terdaftar di gudang cloud. Tambahkan produk dulu dengan /tambah_produk.")
            return

        send_telegram_reply(
            bot_token, chat_id,
            f"🔬 <i>Menganalisis keamanan layering untuk <b>{len(products)} produk</b> Anda...\n\nMohon tunggu, Gemini AI sedang memproses seluruh inventaris. Ini mungkin memakan beberapa saat.</i>"
        )

        # Self-healing: auto-detect missing ingredients
        for prod in products:
            if not prod.get("ingredients"):
                detected = call_gemini_to_find_ingredients(prod['brand'], prod['name'])
                if detected:
                    query_supabase(f"products?id=eq.{prod['id']}", method="PATCH", body={"ingredients": detected})
                    prod["ingredients"] = detected

        res = call_gemini_for_safety_all(products)
        conflicts = res.get("conflicts", [])
        recommendation = res.get("recommendation", "Tidak ada rekomendasi.")

        msg = "<b>🔬 Laporan Analisis Lengkap Inventaris Skindaily</b>\n\n"

        if conflicts:
            msg += "<b>⚠️ Konflik Kandungan Ditemukan:</b>\n"
            for c in conflicts:
                badge = "💥" if c.get("status") == "BAHAYA" else "⚠️"
                msg += f"\n{badge} <b>{c.get('product_a', '?')} ⚡ {c.get('product_b', '?')}</b>\n"
                msg += f"   Status: <b>{c.get('status', '?')}</b>\n"
                msg += f"   {c.get('reason', '')}\n"
        else:
            msg += "✅ <b>Tidak ada konflik parah</b> antara produk Anda!\n"

        msg += f"\n💡 <b>Rekomendasi Rutinitas:</b>\n{recommendation}"
        msg += "\n\n👉 <i>Ketik /terapkan_rekomendasi untuk menerapkan rekomendasi rutinitas ini secara otomatis ke jadwal Anda.</i>"

        # Telegram has 4096 char limit; split if needed
        if len(msg) > 4000:
            send_telegram_reply(bot_token, chat_id, msg[:4000] + "...")
        else:
            send_telegram_reply(bot_token, chat_id, msg)

    elif text.startswith("/terapkan_rekomendasi"):
        products = query_supabase("products?select=*")
        if not products or len(products) < 2:
            send_telegram_reply(bot_token, chat_id, "⚠️ Minimal harus ada 2 produk terdaftar untuk dapat mengatur rutinitas otomatis.")
            return

        send_telegram_reply(bot_token, chat_id, "🔄 <i>Sedang menganalisis & menerapkan rekomendasi rutinitas AI ke jadwal Anda...</i>")

        # Get AI safety recommendation
        res = call_gemini_for_safety_all(products)
        recommendation = res.get("recommendation", "")

        if not recommendation:
            send_telegram_reply(bot_token, chat_id, "❌ Gagal mendapatkan rekomendasi rutinitas dari Gemini AI.")
            return

        # Parse recommendation via Gemini
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            send_telegram_reply(bot_token, chat_id, "❌ Kunci API Gemini belum dikonfigurasi.")
            return

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite:generateContent?key={api_key}"
        
        parse_prompt = f"""
        Berdasarkan rekomendasi skincare berikut, buatkan mapping produk ke rutinitas AM/PM dengan frequency.
        
        REKOMENDASI:
        {recommendation}
        
        DAFTAR PRODUK:
        {json.dumps([{"id": p['id'], "brand": p['brand'], "name": p['name']} for p in products])}
        
        Kembalikan JSON dengan format:
        {{
          "am_routine": [
            {{"id": 1, "frequency_notes": "setiap pagi"}},
            {{"id": 2, "frequency_notes": "setiap pagi"}}
          ],
          "pm_routine": [
            {{"id": 3, "frequency_notes": "2-3x per minggu"}},
            {{"id": 4, "frequency_notes": "setiap malam non-eksfoliasi"}}
          ]
        }}
        
        PENTING:
        - Match nama produk dari rekomendasi dengan ID produk di daftar
        - Sertakan frequency_notes yang ada di rekomendasi (misal: "2-3x per minggu", "setiap hari", dll)
        - Jika produk tidak disebutkan di rekomendasi, asumsikan bisa AM dan PM
        - Kembalikan HANYA JSON object
        """
        
        payload = {
            "contents": [{"parts": [{"text": parse_prompt}]}],
            "generationConfig": {"responseMimeType": "application/json"}
        }

        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                url, data=data,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=30) as response:
                res_body = json.loads(response.read().decode("utf-8"))
                text_response = res_body["candidates"][0]["content"]["parts"][0]["text"]
                parse_result = json.loads(text_response.strip())
                
            am_products = parse_result.get("am_routine", [])
            pm_products = parse_result.get("pm_routine", [])
            
            # Build routine steps for Supabase
            am_steps = []
            for i, p in enumerate(am_products):
                step = {
                    "product_id": int(p['id']) if isinstance(p, dict) else int(p),
                    "routine_type": "AM",
                    "step_order": i+1
                }
                am_steps.append(step)
                
            pm_steps = []
            for i, p in enumerate(pm_products):
                step = {
                    "product_id": int(p['id']) if isinstance(p, dict) else int(p),
                    "routine_type": "PM",
                    "step_order": i+1
                }
                pm_steps.append(step)
            
            all_steps = am_steps + pm_steps
            
            # Delete existing routines and insert new ones in Supabase
            try:
                query_supabase("routine_steps?routine_type=eq.AM", "DELETE")
                query_supabase("routine_steps?routine_type=eq.PM", "DELETE")
            except Exception as e:
                print(f"Delete error: {e}")
            
            if all_steps:
                try:
                    query_supabase("routine_steps", "POST", all_steps)
                except Exception as e:
                    print(f"Supabase POST error: {e}")
            
            # No-op for SQLite, everything is cloud-based in Supabase now
            pass
            
            send_telegram_reply(
                bot_token,
                chat_id,
                f"✅ <b>Jadwal Rutinitas Anda Berhasil Diperbarui via AI!</b>\n\n"
                f"☀️ Pagi (AM): {len(am_products)} produk\n"
                f"🌙 Malam (PM): {len(pm_products)} produk\n\n"
                f"Ketik /status untuk melihat jadwal ter-update."
            )
        except Exception as e:
            send_telegram_reply(bot_token, chat_id, f"❌ Gagal menerapkan rekomendasi: {str(e)}")


    elif text.startswith("/daftar_produk"):
        products = query_supabase("products?select=*")
        if not products:
            send_telegram_reply(bot_token, chat_id, "ℹ️ Belum ada produk terdaftar di gudang cloud.")
            return
            
        msg = "<b>📋 Daftar Produk di Gudang Skindaily:</b>\n\n"
        current_date = date.today()
        
        for idx, prod in enumerate(products, 1):
            msg += f"{idx}. <b>{prod['brand']}</b> - {prod['name']}\n"
            
            # Show ingredients if available
            if prod.get('ingredients'):
                msg += f"   Bahan: <i>{prod['ingredients']}</i>\n"
            
            # Show expiry date if available
            opened_at_str = prod.get("opened_at")
            pao_months = prod.get("pao_months")
            if opened_at_str and pao_months:
                try:
                    opened_date = datetime.strptime(opened_at_str, "%Y-%m-%d").date()
                    month = opened_date.month + pao_months
                    year = opened_date.year + (month - 1) // 12
                    month = ((month - 1) % 12) + 1
                    expiry_date = opened_date.replace(year=year, month=month)
                    expiry_label = expiry_date.strftime('%d %b %Y')
                    days_left = (expiry_date - current_date).days
                    
                    if days_left < 0:
                        msg += f"   ❌ Exp: <b>{expiry_label}</b> (EXPIRED!)\n"
                    elif days_left <= 30:
                        msg += f"   ⚠️ Exp: <b>{expiry_label}</b> ({days_left} hari)\n"
                    else:
                        msg += f"   ✅ Exp: {expiry_label} ({days_left} hari)\n"
                except:
                    pass
            
            msg += "\n"
            
        send_telegram_reply(bot_token, chat_id, msg)
        
    else:
        send_telegram_reply(bot_token, chat_id, "❓ Perintah tidak dikenal. Ketik /start untuk melihat panduan asisten.")

# Main bot loop
def bot_polling_loop():
    offset = 0
    print("[Skindaily Bot] Polling daemon started.")
    
    # Configure commands menu once on startup
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if bot_token:
        set_bot_commands(bot_token)
    
    while True:
        bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
        
        if not bot_token:
            time.sleep(10)
            continue
            
        url = f"https://api.telegram.org/bot{bot_token}/getUpdates?offset={offset}&timeout=5"
        
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=10) as response:
                res_body = json.loads(response.read().decode("utf-8"))
                
                if res_body.get("ok"):
                    updates = res_body.get("result", [])
                    for update in updates:
                        offset = update["update_id"] + 1
                        message = update.get("message")
                        if message:
                            handle_bot_message(bot_token, message)
                            
        except Exception as e:
            if "timeout" not in str(e).lower():
                print(f"[Skindaily Bot] Polling error: {e}")
                
        time.sleep(1)

def start_bot_thread():
    thread = threading.Thread(target=bot_polling_loop, daemon=True)
    thread.start()
