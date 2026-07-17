# System Design Specification: Personal Skincare Tracker & Layering Analyzer

Dokumen ini mendefinisikan spesifikasi desain sistem (*System Design Specification*) untuk aplikasi web **Skincare Tracker & Layering Analyzer**. Dokumen ini menjadi acuan arsitektur cetak biru (*blueprint*) bagi developer untuk memahami interaksi antar komponen, struktur data mendalam, antarmuka pemrograman (API), dan desain pengalaman pengguna (UX).

---

## 📋 Daftar Isi
1. [Prinsip Desain & Batasan Sistem](#1-prinsip-desain--batasan-sistem)
2. [Arsitektur Data & Kamus Data (*Data Dictionary*)](#2-arsitektur-data--kamus-data-data-dictionary)
3. [Spesifikasi Kontrak API (*API Contract*)](#3-spesifikasi-kontrak-api-api-contract)
4. [Alur Logika Sistem (*Sequence Diagrams*)](#4-alur-logika-sistem-sequence-diagrams)
5. [Desain Antarmuka Pengguna (*Wireframe & UX Flow*)](#5-desain-antarmuka-pengguna-wireframe--ux-flow)

---

## 1. Prinsip Desain & Batasan Sistem

Aplikasi dirancang berdasarkan kebutuhan spesifik pengguna dengan karakteristik penanganan data lokal yang ringkas dan integrasi AI yang efisien.

*   **Mobile-First Integration:** Antarmuka diprioritaskan penuh untuk resolusi layar ponsel (`360px` hingga `480px`). Tata letak tombol, ukuran teks, dan area ketuk (*hit target*) disesuaikan untuk penggunaan satu tangan di depan cermin.
*   **Privacy by Design:** Seluruh data inventaris produk dan catatan riwayat log penggunaan harian disimpan sepenuhnya di penyimpanan lokal (Local Storage / SQLite lokal), tanpa ada sinkronisasi ke cloud pihak ketiga selain pengiriman gambar ke Gemini API.
*   **Zero-Configuration AI:** Integrasi AI dijalankan secara asinkron menggunakan model *stateless*. API tidak menyimpan memori percakapan sebelumnya untuk menghemat kuota token dan mempercepat waktu respons (*low latency*).

---

## 2. Arsitektur Data & Kamus Data (*Data Dictionary*)

Berikut adalah detail tipe data, batasan (*constraints*), dan relasi antar entitas di dalam database SQLite.

### Tabel 1: `products`
Menyimpan informasi utama produk perawatan kulit yang dimiliki oleh pengguna.
*   `id` (INTEGER, Primary Key, Auto Increment): ID unik produk.
*   `brand` (TEXT, Not Null): Nama produsen atau merek produk (contoh: *Hada Labo*, *Azarine*).
*   `name` (TEXT, Not Null): Nama varian produk (contoh: *Gokujyun Premium Lotion*).
*   `ingredients` (TEXT, Nullable): Daftar bahan aktif hasil ekstraksi Gemini, disimpan dalam format teks terpisah koma (*comma-separated values*).
*   `opened_at` (DATE, Nullable): Tanggal pengguna pertama kali membuka segel produk (format: `YYYY-MM-DD`).
*   `pao_months` (INTEGER, Nullable): Durasi ketahanan produk setelah dibuka dalam satuan bulan (contoh: `6`, `12`).

### Tabel 2: `routine_steps`
Menyimpan konfigurasi urutan pemakaian produk untuk jadwal tertentu.
*   `id` (INTEGER, Primary Key, Auto Increment): ID unik langkah rutinitas.
*   `product_id` (INTEGER, Foreign Key terhubung ke `products.id` dengan aksi `ON DELETE CASCADE`).
*   `routine_type` (TEXT, Not Null): Kategori waktu penggunaan, dibatasi hanya untuk nilai `AM` (Pagi) atau `PM` (Malam).
*   `step_order` (INTEGER, Not Null): Nomor urutan pengaplikasian produk pada wajah (dimulai dari urutan `1`).

### Tabel 3: `routine_logs`
Mencatat riwayat kedisiplinan harian pengguna.
*   `id` (INTEGER, Primary Key, Auto Increment): ID unik log transaksi.
*   `product_id` (INTEGER, Foreign Key terhubung ke `products.id`).
*   `logged_at` (TIMESTAMP, Default `CURRENT_TIMESTAMP`): Waktu tepat saat tombol selesai ditekan.
*   `status` (TEXT, Not Null): Status pemakaian, bernilai `COMPLETED` jika produk dipakai, atau `SKIPPED` jika dilewati.

---

## 3. Spesifikasi Kontrak API (*API Contract*)

Seluruh komunikasi data antara Frontend dan Backend FastAPI menggunakan format data JSON melalui protokol HTTP.

### Endpoint 1: Mengambil Jadwal Rutinitas
*   **URL:** `/api/routine`
*   **Metode:** `GET`
*   **Response (200 OK):**
    ```json
    {
      "routine_type": "PM",
      "steps": [
        {
          "step_order": 1,
          "id": 4,
          "brand": "Hada Labo",
          "name": "Gokujyun Wash",
          "ingredients": "Hyaluronic Acid",
          "days_remaining": 240,
          "is_expired": false
        }
      ]
    }
    ```

### Endpoint 2: Ekstraksi Gambar Produk via Gemini
*   **URL:** `/api/products/scan`
*   **Metode:** `POST`
*   **Content-Type:** `multipart/form-data`
*   **Request Body:** `file: [Binary Image Data]`
*   **Response (200 OK):**
    ```json
    {
      "brand": "Facetology",
      "name": "Triple Care Sunscreen",
      "active_ingredients": ["Niacinamide", "Centella Asiatica", "Tranexamic Acid"]
    }
    ```

### Endpoint 3: Cek Keamanan Layering Kandungan
*   **URL:** `/api/products/check-safety`
*   **Metode:** `GET`
*   **Query Parameters:** `id_a=[int]`, `id_b=[int]`
*   **Response (200 OK):**
    ```json
    {
      "status": "BAHAYA",
      "reason": "Penggabungan Retinol (Produk A) dengan AHA/BHA (Produk B) dalam satu waktu dapat menyebabkan over-eksfoliasi, merusak skin barrier, dan memicu iritasi ekstrem."
    }
    ```

---

## 4. Alur Logika Sistem (*Sequence Diagrams*)

### Proses Pemindaian Produk Baru (AI Extraction Flow)
```
[User Interface]           [FastAPI Backend]            [Gemini API]
       |                           |                         |
       |--- 1. Kirim Foto ------>|                         |
       |    (Multipart Form)       |--- 2. Forward Image --->|
       |                           |    + Prompt Kontrak     |
       |                           |<-- 3. Return JSON ------|
       |                           |    (Brand, Name, Active)|
       |<-- 4. Tampilkan Hasil ----|                         |
       |    di Form Validasi       |                         |
```

### Proses Validasi Keamanan Layering Rutinitas
```
[User Interface]           [FastAPI Backend]            [Gemini API]
       |                           |                         |
       |--- 1. Pilih Dua Prod ---->|                         |
       |    (ID_A & ID_B)          |--- 2. Ambil data DB --->| (Query lokal)
       |                           |--- 3. Analisis Layer -->|
       |                           |    (Kirim teks bahan)   |
       |                           |<-- 4. Status & Alasan ---|
       |<-- 5. Render Peringatan --|                         |
       |    (Merah/Kuning/Hijau)   |                         |
```

---

## 5. Desain Antarmuka Pengguna (*Wireframe & UX Flow*)

Aplikasi ini mengadopsi sistem navigasi bawah (*Bottom Navigation Bar*) yang konstan untuk mempermudah perpindahan halaman dengan ibu jari.

### Sketsa Tata Letak Halaman Utama (Rutinitas Harian)
```
+------------------------------------------+
|  [☀️ AM ROUTINE] / [🌙 PM ROUTINE]       | <- Header Dinamis (Warna Berubah)
|  Jumat, 17 Juli 2026                     |
+------------------------------------------+
| ⚠️ Sisa PAO Hada Labo Serum < 30 Hari!   | <- Warning Card (Kondisional)
+------------------------------------------+
| [ Lgkh 1 ] Hada Labo Facial Wash     [v] | <- Checklist Komponen (Card)
| Merek: Rohto | Bahan: Hyaluronic Acid    |
|                                          |
| [ Lgkh 2 ] Facetology Toner          [ ] | <- Belum dicentang
| Merek: Facetology | Bahan: Centella      |
+------------------------------------------+
|                                          |
|    [ SIMPAN RUTINITAS ]                  | <- Tombol Utama Stabil di Bawah
|                                          |
+------------------------------------------+
|   [📅 Rutin]    [📷 Scan]    [🛡️ Safety] | <- Fixed Bottom Navbar
+------------------------------------------+
```

### Panduan Desain Warna (*Design Tokens*)
Untuk menjaga konsistensi visual saat transisi waktu harian, gunakan kode warna Tailwind CSS berikut:
*   **Mode Pagi (AM):** `from-amber-500 to-orange-500` (Merepresentasikan kehangatan cahaya matahari pagi).
*   **Mode Malam (PM):** `from-slate-700 to-indigo-900` (Merepresentasikan ketenangan waktu malam sebelum tidur).
*   **Status Bahaya Layering:** `bg-red-50 border-red-500 text-red-700` untuk memberikan efek psikologis tanda berhenti / waspada bagi kulit.
*   **Status Aman Layering:** `bg-emerald-50 border-emerald-500 text-emerald-700` menandakan produk sangat aman diaplikasikan bersamaan.
