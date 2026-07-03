"""
============================================
PENDAFTARAN WAJAH BARU
Sistem Palang Parkir Otomatis
============================================
"""

import cv2
import face_recognition
import numpy as np
import pickle
import os

# ===== KONFIGURASI =====
FILE_DATABASE = "database_wajah.pkl"  # File penyimpanan database
FOLDER_FOTO   = "foto_terdaftar"      # Folder foto referensi (opsional)

# ===== WARNA UNTUK DISPLAY (BGR) =====
WARNA_KOTAK  = (0, 255, 0)    # Hijau
WARNA_TEKS   = (255, 255, 255) # Putih
WARNA_BG     = (0, 150, 0)    # Hijau tua (background teks)


def muat_database():
    """Muat database wajah yang sudah ada."""
    if os.path.exists(FILE_DATABASE):
        with open(FILE_DATABASE, "rb") as f:
            data = pickle.load(f)
        print(f"[INFO] Database dimuat: {len(data['nama'])} wajah terdaftar")
        return data
    else:
        print("[INFO] Database baru dibuat")
        return {"nama": [], "encoding": []}


def simpan_database(data):
    """Simpan database wajah ke file."""
    with open(FILE_DATABASE, "wb") as f:
        pickle.dump(data, f)
    print(f"[INFO] Database tersimpan: {len(data['nama'])} wajah")


def tangkap_wajah(nama):
    """
    Buka kamera dan tangkap wajah untuk didaftarkan.
    Tekan SPASI untuk mengambil foto, Q untuk batal.
    """
    kamera = cv2.VideoCapture(0)
    
    if not kamera.isOpened():
        print("[ERROR] Kamera tidak ditemukan!")
        return None
    
    print(f"\n[INFO] Mendaftarkan wajah untuk: {nama}")
    print("[INFO] Hadapkan wajah ke kamera")
    print("[INFO] Tekan SPASI untuk ambil foto | Q untuk batal")
    
    encoding_tersimpan = None
    
    while True:
        ret, frame = kamera.read()
        if not ret:
            break
        
        # Deteksi wajah real-time untuk preview
        frame_kecil = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)
        frame_rgb   = cv2.cvtColor(frame_kecil, cv2.COLOR_BGR2RGB)
        
        lokasi_wajah = face_recognition.face_locations(frame_rgb, model="hog")
        
        # Gambar kotak di wajah yang terdeteksi
        for (atas, kanan, bawah, kiri) in lokasi_wajah:
            # Sesuaikan kembali ke ukuran frame asli
            cv2.rectangle(frame,
                          (kiri*2, atas*2),
                          (kanan*2, bawah*2),
                          WARNA_KOTAK, 2)
        
        # Tampilkan status
        status = f"Wajah Terdeteksi: {len(lokasi_wajah)}"
        cv2.rectangle(frame, (0, 0), (300, 35), WARNA_BG, -1)
        cv2.putText(frame, status, (5, 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, WARNA_TEKS, 2)
        
        instruksi = "SPASI=Ambil Foto | Q=Batal"
        cv2.putText(frame, instruksi, (5, frame.shape[0]-10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, WARNA_KOTAK, 1)
        
        cv2.imshow(f"Daftar Wajah - {nama}", frame)
        
        key = cv2.waitKey(1) & 0xFF
        
        if key == ord('q') or key == ord('Q'):
            print("[INFO] Pendaftaran dibatalkan")
            break
        
        elif key == ord(' '):  # Tekan spasi
            if len(lokasi_wajah) == 0:
                print("[PERINGATAN] Tidak ada wajah terdeteksi! Coba lagi.")
                continue
            elif len(lokasi_wajah) > 1:
                print("[PERINGATAN] Lebih dari 1 wajah terdeteksi! Pastikan hanya 1 wajah.")
                continue
            
            # Ambil encoding wajah dari frame penuh
            frame_rgb_penuh = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            lokasi_penuh    = face_recognition.face_locations(frame_rgb_penuh, model="hog")
            encodings       = face_recognition.face_encodings(frame_rgb_penuh, lokasi_penuh)
            
            if encodings:
                encoding_tersimpan = encodings[0]
                print(f"[SUKSES] Wajah {nama} berhasil diambil!")
                
                # Simpan foto referensi (opsional)
                os.makedirs(FOLDER_FOTO, exist_ok=True)
                cv2.imwrite(f"{FOLDER_FOTO}/{nama}.jpg", frame)
                
                break
            else:
                print("[ERROR] Gagal mengambil encoding, coba lagi.")
    
    kamera.release()
    cv2.destroyAllWindows()
    return encoding_tersimpan


def main():
    print("=" * 50)
    print("  SISTEM PENDAFTARAN WAJAH PARKIR OTOMATIS")
    print("=" * 50)
    
    database = muat_database()
    
    while True:
        print("\n[ MENU UTAMA ]")
        print("1. Daftarkan wajah baru")
        print("2. Lihat daftar wajah terdaftar")
        print("3. Hapus wajah dari database")
        print("4. Keluar")
        
        pilihan = input("\nPilih menu (1-4): ").strip()
        
        if pilihan == "1":
            nama = input("Masukkan nama pengguna: ").strip()
            
            if not nama:
                print("[ERROR] Nama tidak boleh kosong!")
                continue
            
            if nama in database["nama"]:
                ganti = input(f"[PERINGATAN] '{nama}' sudah terdaftar. Timpa? (y/n): ")
                if ganti.lower() != 'y':
                    continue
                # Hapus data lama
                idx = database["nama"].index(nama)
                database["nama"].pop(idx)
                database["encoding"].pop(idx)
            
            encoding = tangkap_wajah(nama)
            
            if encoding is not None:
                database["nama"].append(nama)
                database["encoding"].append(encoding)
                simpan_database(database)
                print(f"[SUKSES] '{nama}' berhasil didaftarkan ke sistem parkir!")
        
        elif pilihan == "2":
            if not database["nama"]:
                print("[INFO] Belum ada wajah terdaftar.")
            else:
                print(f"\n[ DAFTAR WAJAH TERDAFTAR — {len(database['nama'])} pengguna ]")
                for i, nama in enumerate(database["nama"], 1):
                    print(f"  {i}. {nama}")
        
        elif pilihan == "3":
            if not database["nama"]:
                print("[INFO] Database kosong.")
                continue
            
            print("\n[ DAFTAR WAJAH ]")
            for i, nama in enumerate(database["nama"], 1):
                print(f"  {i}. {nama}")
            
            try:
                nomor = int(input("Masukkan nomor yang akan dihapus: ")) - 1
                if 0 <= nomor < len(database["nama"]):
                    nama_hapus = database["nama"].pop(nomor)
                    database["encoding"].pop(nomor)
                    simpan_database(database)
                    print(f"[SUKSES] '{nama_hapus}' berhasil dihapus.")
                else:
                    print("[ERROR] Nomor tidak valid.")
            except ValueError:
                print("[ERROR] Masukkan angka yang valid.")
        
        elif pilihan == "4":
            print("\n[INFO] Program pendaftaran selesai.")
            break
        
        else:
            print("[ERROR] Pilihan tidak valid.")


if __name__ == "__main__":
    main()