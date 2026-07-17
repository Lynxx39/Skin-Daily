from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import os
import json
import base64
import urllib.request
import urllib.parse
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

from .database import (
    init_db, add_product, get_all_products, get_product,
    update_product, delete_product, get_routine, save_routine_steps,
    add_routine_log, get_recent_logs, get_setting, set_setting
)
from .telegram_service import send_telegram_message
from .telegram_bot import start_bot_thread

# Initialize DB
init_db()

app = FastAPI(title="Skindaily API", description="Personal Skincare Tracker & Layering Analyzer")

@app.on_event("startup")
def startup_event():
    if not os.environ.get("VERCEL"):
        start_bot_thread()

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
        print(f"Error reading frontend .env: {e}")
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
            "Content-Type": "application/json"
        },
        method=method
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as res:
            res_content = res.read().decode("utf-8")
            if res_content:
                return json.loads(res_content)
            return []
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8") if e.fp else ""
        print(f"Failed to query Supabase REST API ({method} {endpoint}): HTTP {e.code} - {err_body}")
        return []
    except Exception as e:
        print(f"Failed to query Supabase REST API ({method} {endpoint}): {e}")
        return []

# Enable CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict this to the frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic schemas
class ProductSchema(BaseModel):
    id: Optional[int] = None
    brand: str
    name: str
    ingredients: Optional[str] = None
    opened_at: Optional[str] = None
    pao_months: Optional[int] = None

class RoutineSaveSchema(BaseModel):
    routine_type: str # AM or PM
    product_ids: List[int]

class RoutineLogSchema(BaseModel):
    product_id: int
    status: str # COMPLETED or SKIPPED

class TelegramSettingsSchema(BaseModel):
    bot_token: str
    chat_id: str

class GeminiSettingsSchema(BaseModel):
    api_key: str

# ----------------- SETTINGS & UTILS -----------------

def get_gemini_api_key() -> str:
    return os.environ.get("GEMINI_API_KEY")

def call_gemini_api(prompt: str, image_data: Optional[bytes] = None, mime_type: Optional[str] = None) -> dict:
    api_key = get_gemini_api_key()
    if not api_key:
        raise HTTPException(status_code=400, detail="Gemini API Key is not configured. Please set it in your backend .env file.")
        
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite:generateContent?key={api_key}"
    
    parts = [{"text": prompt}]
    if image_data and mime_type:
        base64_image = base64.b64encode(image_data).decode("utf-8")
        parts.append({
            "inlineData": {
                "mimeType": mime_type,
                "data": base64_image
            }
        })
        
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
        raise HTTPException(status_code=500, detail=f"Gemini API call failed: {str(e)}")

# ----------------- ENDPOINTS -----------------

@app.get("/api/settings")
def get_settings():
    return {
        "gemini_api_key": os.environ.get("GEMINI_API_KEY", ""),
        "telegram_bot_token": os.environ.get("TELEGRAM_BOT_TOKEN", ""),
        "telegram_chat_id": os.environ.get("TELEGRAM_CHAT_ID", "")
    }

@app.post("/api/settings")
def save_settings(data: dict):
    # No-op as settings are managed via .env
    return {"status": "success", "message": "Settings managed via backend .env"}

@app.get("/api/products/analyze-ingredients")
def analyze_ingredients(brand: str, name: str):
    api_key = get_gemini_api_key()
    if not api_key:
        raise HTTPException(status_code=400, detail="Gemini API Key is not configured in backend .env")
    
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
                return {"ingredients": ""}
            return {"ingredients": ans}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to call Gemini: {str(e)}")

@app.get("/api/products")
def fetch_products():
    return get_all_products()

@app.post("/api/products")
def create_or_update_product(product: ProductSchema):
    if product.id:
        update_product(
            product.id,
            product.brand,
            product.name,
            product.ingredients,
            product.opened_at,
            product.pao_months
        )
        return {"status": "updated", "id": product.id}
    else:
        new_id = add_product(
            product.brand,
            product.name,
            product.ingredients,
            product.opened_at,
            product.pao_months
        )
        return {"status": "created", "id": new_id}

@app.delete("/api/products/{product_id}")
def remove_product(product_id: int):
    delete_product(product_id)
    return {"status": "deleted"}

@app.post("/api/products/scan")
async def scan_product(file: UploadFile = File(...)):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Uploaded file is not an image.")
        
    image_bytes = await file.read()
    
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
    
    result = call_gemini_api(prompt, image_bytes, file.content_type)
    return result

@app.get("/api/products/check-safety")
def check_safety(id_a: int = Query(...), id_b: int = Query(...)):
    res_a = query_supabase(f"products?id=eq.{id_a}")
    res_b = query_supabase(f"products?id=eq.{id_b}")
    
    if not res_a or not res_b:
        raise HTTPException(status_code=404, detail="One or both products not found.")
        
    prod_a = res_a[0]
    prod_b = res_b[0]
    
    ingredients_a = prod_a.get("ingredients") or ""
    ingredients_b = prod_b.get("ingredients") or ""
    
    # Self-healing: if ingredients are empty, detect and update Supabase!
    if not ingredients_a:
        try:
            res = analyze_ingredients(prod_a['brand'], prod_a['name'])
            ingredients_a = res.get("ingredients") or ""
            if ingredients_a:
                query_supabase(f"products?id=eq.{id_a}", method="PATCH", body={"ingredients": ingredients_a})
        except Exception as e:
            print(f"Self-healing failed for product A: {e}")
            
    if not ingredients_b:
        try:
            res = analyze_ingredients(prod_b['brand'], prod_b['name'])
            ingredients_b = res.get("ingredients") or ""
            if ingredients_b:
                query_supabase(f"products?id=eq.{id_b}", method="PATCH", body={"ingredients": ingredients_b})
        except Exception as e:
            print(f"Self-healing failed for product B: {e}")
            
    # Fallback if still empty
    if not ingredients_a:
        ingredients_a = "Tidak diketahui"
    if not ingredients_b:
        ingredients_b = "Tidak diketahui"
    
    prompt = f"""
    Analisis keamanan layering (penggabungan penggunaan bersamaan) antara kedua produk skincare berikut:
    
    Produk A:
    Merek: {prod_a['brand']}
    Nama: {prod_a['name']}
    Bahan Aktif: {ingredients_a}
    
    Produk B:
    Merek: {prod_b['brand']}
    Nama: {prod_b['name']}
    Bahan Aktif: {ingredients_b}
    
    Tentukan apakah aman menggunakan kedua produk ini secara bertumpuk (layering) pada waktu yang sama.
    Kembalikan respon hanya dalam bentuk JSON dengan format berikut:
    {{
      "status": "AMAN" atau "BAHAYA" atau "HATI-HATI",
      "reason": "Penjelasan detail mengapa aman/bahaya/perlu hati-hati dalam Bahasa Indonesia yang ramah pengguna."
    }}
    
    Gunakan kriteria dermatologi standar:
    - AMAN: Bahan-bahan saling menghidrasi atau mendukung (misal: Hyaluronic Acid + Niacinamide, Centella + Sunscreen).
    - BAHAYA: Kombinasi yang memicu over-eksfoliasi atau merusak skin barrier (misal: Retinol + AHA/BHA, Vitamin C + Retinol, AHA + BHA konsentrasi tinggi).
    - HATI-HATI: Dapat digunakan bersama jika kulit terbiasa, atau disarankan diberi jeda waktu penyerapan (misal: Vitamin C + Niacinamide, Salicylic Acid + Niacinamide).
    
    Kembalikan HANYA JSON object. Jangan tambahkan penjelasan di luar JSON.
    """
    
    result = call_gemini_api(prompt)
    
    # Send results to Telegram
    if result:
        status_emoji = "🔴" if result.get("status") == "BAHAYA" else "🟡" if result.get("status") == "HATI-HATI" else "✅"
        msg = f"<b>{status_emoji} Safety Check: 2 Produk</b>\n\n"
        msg += f"<b>Produk A:</b> {prod_a['brand']} — {prod_a['name']}\n"
        msg += f"<b>Produk B:</b> {prod_b['brand']} — {prod_b['name']}\n\n"
        msg += f"<b>Status:</b> {result.get('status', 'TIDAK DIKETAHUI')}\n"
        msg += f"<b>Alasan:</b> {result.get('reason', '')}"
        
        # Send to Telegram
        send_telegram_message(msg)
    
    return result

@app.get("/api/products/check-safety-all")
def check_safety_all():
    products = query_supabase("products?select=*")
    if not products:
        return {"conflicts": [], "recommendation": "Anda belum menambahkan produk ke gudang."}
        
    # Self-healing: if ingredients are empty, detect and update Supabase!
    for prod in products:
        ingredients = prod.get("ingredients") or ""
        if not ingredients:
            try:
                res = analyze_ingredients(prod['brand'], prod['name'])
                detected = res.get("ingredients") or ""
                if detected:
                    query_supabase(f"products?id=eq.{prod['id']}", method="PATCH", body={"ingredients": detected})
                    prod["ingredients"] = detected
            except Exception as e:
                print(f"Self-healing failed for {prod['brand']} {prod['name']}: {e}")
                
    # Format products list for prompt
    prod_list_str = ""
    for idx, p in enumerate(products, 1):
        ing = p.get("ingredients") or "Tidak diketahui"
        prod_list_str += f"{idx}. Merek: {p['brand']}, Nama: {p['name']}, Bahan Aktif: {ing}\n"
        
    prompt = f"""
    Analisis keamanan layering (penggabungan penggunaan bersamaan) untuk semua produk skincare yang dimiliki pengguna berikut:
    
    {prod_list_str}
    
    Tentukan apakah ada kombinasi produk yang saling berbenturan (bahaya/hati-hati jika digunakan pada rutinitas yang sama), dan berikan rekomendasi pembagian rutinitas penggunaan yang aman (misalnya memisahkan produk eksfoliasi ke PM, menyarankan hidrasi setelah bahan aktif tertentu, dll).
    
    Kembalikan respon hanya dalam bentuk JSON dengan format berikut:
    {{
      "conflicts": [
        {{
          "product_a": "Nama lengkap Produk A",
          "product_b": "Nama lengkap Produk B",
          "status": "BAHAYA" atau "HATI-HATI",
          "reason": "Penjelasan detail dalam Bahasa Indonesia mengapa kombinasi ini tidak boleh digabung/perlu hati-hati."
        }}
      ],
      "recommendation": "Rekomendasi detail pembagian rutinitas harian (AM/PM) untuk seluruh produk di atas agar aman dan efektif bagi pengguna (Bahasa Indonesia)."
    }}
    
    Kembalikan HANYA JSON object. Jangan tambahkan penjelasan di luar JSON.
    """
    
    result = call_gemini_api(prompt)
    
    # Send results to Telegram
    if result:
        conflicts = result.get("conflicts", [])
        recommendation = result.get("recommendation", "")
        
        # Format message for Telegram
        msg = "<b>🧬 Safety Analysis: Semua Produk</b>\n\n"
        
        if conflicts:
            msg += f"<b>⚠️ Konflik Ditemukan: {len(conflicts)}</b>\n"
            for i, conflict in enumerate(conflicts, 1):
                status_emoji = "🔴" if conflict.get("status") == "BAHAYA" else "🟡"
                msg += f"\n{status_emoji} <b>{conflict.get('product_a', '')} × {conflict.get('product_b', '')}</b>\n"
                msg += f"<i>{conflict.get('reason', '')}</i>\n"
        else:
            msg += "<b>✅ Tidak Ada Konflik Ditemukan</b>\n"
        
        msg += f"\n<b>💡 Rekomendasi:</b>\n{recommendation}"
        
        # Send to Telegram
        send_telegram_message(msg)
    
    return result

@app.post("/api/routine/apply-ai-recommendation")
def apply_ai_recommendation():
    """Parse AI recommendation dan auto-setup routine berdasarkan analisis keamanan"""
    sync_supabase_to_sqlite()
    products = query_supabase("products?select=*")
    if not products or len(products) < 2:
        raise HTTPException(status_code=400, detail="Minimum 2 produk dibutuhkan untuk analisis.")
    
    # Get AI analysis
    ai_result = check_safety_all()
    recommendation = ai_result.get("recommendation", "")
    
    # Parse recommendation dengan AI untuk extract AM/PM assignments
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
    
    try:
        parse_result = call_gemini_api(parse_prompt)
        am_products = parse_result.get("am_routine", [])
        pm_products = parse_result.get("pm_routine", [])
        
        print(f"Parsed AI result: AM={len(am_products)}, PM={len(pm_products)}")
        print(f"AM products: {am_products}")
        print(f"PM products: {pm_products}")
        
        # Build routine steps for Supabase with explicit int conversions
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
        print(f"Built steps: {all_steps}")
        
        # Delete existing routines and insert new ones
        try:
            query_supabase("routine_steps?routine_type=eq.AM", "DELETE")
            query_supabase("routine_steps?routine_type=eq.PM", "DELETE")
        except Exception as e:
            print(f"Delete error: {e}")
        
        if all_steps:
            try:
                result = query_supabase("routine_steps", "POST", all_steps)
                print(f"Supabase POST result: {result}")
            except Exception as e:
                print(f"Supabase POST error, will use SQLite backup: {e}")
        
        # Also save to SQLite for backup
        save_routine_steps("AM", am_products)
        save_routine_steps("PM", pm_products)
        
        return {
            "status": "success",
            "message": "Rutinitas berhasil diatur berdasarkan rekomendasi AI",
            "am_count": len(am_products),
            "pm_count": len(pm_products)
        }
    except Exception as e:
        print(f"Error in apply_ai_recommendation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Gagal parse rekomendasi: {str(e)}")

def sync_supabase_to_sqlite():
    try:
        # 1. Sync products
        products = query_supabase("products?select=*")
        if products:
            from .database import get_db_connection
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM products")
            for p in products:
                cursor.execute("""
                INSERT OR REPLACE INTO products (id, brand, name, ingredients, opened_at, pao_months)
                VALUES (?, ?, ?, ?, ?, ?)
                """, (p['id'], p['brand'], p['name'], p.get('ingredients'), p.get('opened_at'), p.get('pao_months')))
            conn.commit()
            conn.close()
            print(f"Synced {len(products)} products to SQLite.")
            
        # 2. Sync routine_steps
        steps = query_supabase("routine_steps?select=*")
        from .database import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Read existing frequency_notes from SQLite first to preserve them
        cursor.execute("SELECT product_id, routine_type, frequency_notes FROM routine_steps")
        existing_notes = {(row[0], row[1]): row[2] for row in cursor.fetchall() if row[2]}
        
        cursor.execute("DELETE FROM routine_steps")
        if steps:
            for s in steps:
                prod_id = s['product_id']
                r_type = s['routine_type']
                # Try to preserve note, fallback to s.get('frequency_notes')
                note = existing_notes.get((prod_id, r_type)) or s.get('frequency_notes')
                cursor.execute("""
                INSERT OR REPLACE INTO routine_steps (id, product_id, routine_type, step_order, frequency_notes)
                VALUES (?, ?, ?, ?, ?)
                """, (s['id'], prod_id, r_type, s['step_order'], note))
        conn.commit()
        conn.close()
        print(f"Synced {len(steps) if steps else 0} routine_steps to SQLite.")
    except Exception as e:
        print(f"Error syncing Supabase to SQLite: {e}")

@app.get("/api/routine")
def fetch_routine(routine_type: str = Query(..., regex="^(AM|PM)$")):
    sync_supabase_to_sqlite()
    steps = get_routine(routine_type)
    
    # Calculate days remaining for each product using opened_at and pao_months
    current_date = date.today()
    
    processed_steps = []
    for step in steps:
        days_remaining = None
        is_expired = False
        
        opened_at_str = step.get("opened_at")
        pao_months = step.get("pao_months")
        
        if opened_at_str and pao_months:
            try:
                opened_date = datetime.strptime(opened_at_str, "%Y-%m-%d").date()
                # Simple approximation: 30 days per month
                expiration_days = pao_months * 30
                elapsed_days = (current_date - opened_date).days
                days_remaining = max(0, expiration_days - elapsed_days)
                is_expired = elapsed_days >= expiration_days
            except ValueError:
                pass
                
        processed_steps.append({
            "step_order": step["step_order"],
            "id": step["id"],
            "brand": step["brand"],
            "name": step["name"],
            "ingredients": step["ingredients"],
            "frequency_notes": step.get("frequency_notes"),
            "days_remaining": days_remaining,
            "is_expired": is_expired
        })
        
    return {
        "routine_type": routine_type,
        "steps": processed_steps
    }

@app.post("/api/routine/steps")
def save_routine(data: RoutineSaveSchema):
    save_routine_steps(data.routine_type, data.product_ids)
    return {"status": "success", "message": f"{data.routine_type} routine updated successfully."}

@app.post("/api/routine/log")
def log_routine(logs: List[RoutineLogSchema]):
    completed_count = 0
    skipped_count = 0
    details = []
    
    for log in logs:
        add_routine_log(log.product_id, log.status)
        prod = get_product(log.product_id)
        prod_name = f"{prod['brand']} {prod['name']}" if prod else f"Product #{log.product_id}"
        
        if log.status == "COMPLETED":
            completed_count += 1
            details.append(f"✅ {prod_name}")
        else:
            skipped_count += 1
            details.append(f"❌ {prod_name} (Skipped)")
            
    # Send Telegram notification if configured
    if completed_count > 0 or skipped_count > 0:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        msg = f"<b>📅 Skincare Log - {now_str}</b>\n\n"
        msg += f"Status pemakaian produk:\n" + "\n".join(details) + "\n\n"
        msg += f"Total: {completed_count} digunakan, {skipped_count} dilewati."
        
        send_telegram_message(msg)
        
    return {"status": "success", "completed": completed_count, "skipped": skipped_count}

@app.post("/api/telegram/webhook")
def telegram_webhook(update: dict):
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        return {"status": "error", "message": "Bot token not configured"}
    
    message = update.get("message")
    if message:
        from .telegram_bot import handle_bot_message
        handle_bot_message(bot_token, message)
        
    return {"status": "ok"}

@app.get("/api/telegram/setup-webhook")
def setup_webhook(url: str = Query(...)):
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        raise HTTPException(status_code=400, detail="Bot token not configured")
        
    webhook_url = f"{url.rstrip('/')}/api/telegram/webhook"
    telegram_url = f"https://api.telegram.org/bot{bot_token}/setWebhook?url={webhook_url}"
    
    try:
        import urllib.request
        import json
        req = urllib.request.Request(telegram_url)
        with urllib.request.urlopen(req, timeout=10) as response:
            res = json.loads(response.read().decode("utf-8"))
            if res.get("ok"):
                return {"status": "success", "message": f"Webhook set to {webhook_url}"}
            else:
                raise HTTPException(status_code=400, detail=f"Telegram error: {res}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to set webhook: {str(e)}")

@app.post("/api/settings/telegram/test")
def test_telegram(data: TelegramSettingsSchema):
    # Temporarily set these for the test or save them
    set_setting("telegram_bot_token", data.bot_token)
    set_setting("telegram_chat_id", data.chat_id)
    
    success = send_telegram_message("🔔 <b>Uji Coba Koneksi Telegram Skindaily</b>\n\nKoneksi berhasil! Bot Anda siap mengirimkan laporan dan pengingat skincare rutin.")
    
    if not success:
        raise HTTPException(status_code=400, detail="Gagal mengirim pesan Telegram. Silakan periksa kembali Token dan Chat ID.")
        
    return {"status": "success", "message": "Pesan uji coba berhasil dikirim!"}
