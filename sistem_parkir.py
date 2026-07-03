"""
============================================
SISTEM PALANG PARKIR OTOMATIS
Main Program — Pengenalan Wajah + Arduino
============================================
"""

import cv2
import face_recognition
import numpy as np
import serial
import serial.tools.list_ports
import pickle
import os
import time
import sys

# ===== KONFIGURASI UTAMA =====
PORT_ARDUINO    = "COM6"       
BAUD_RATE       = 9600         
FILE_DATABASE   = "database_wajah.pkl"

# ===== PARAMETER PENGENALAN =====
TOLERANSI       = 0.55         # Threshold jarak wajah (0.4 ketat — 0.6 longgar)
SKALA_FRAME     = 0.5          # Resize frame untuk percepatan (0.5 = setengah ukuran)
PROSES_TIAP_N   = 3            # Proses face recognition setiap N frame (hemat CPU)

# ===== WARNA DISPLAY (BGR) =====
WARNA_DIKENAL   = (0, 255, 0)   # Hijau — wajah dikenal
WARNA_ASING     = (0, 0, 255)   # Merah — wajah tidak dikenal
WARNA_INFO      = (255, 255, 0) # Cyan — informasi sistem


def cari_port_arduino():
    """Cari port Arduino secara otomatis."""
    ports = serial.tools.list_ports.comports()
    for port in ports:
        if "Arduino" in port.description or "CH340" in port.description or "USB Serial" in port.description:
            print(f"[INFO] Arduino ditemukan di port: {port.device}")
            return port.device
    return None


def muat_database():
    """Muat database wajah dari file."""
    if not os.path.exists(FILE_DATABASE):
        print(f"[ERROR] File database '{FILE_DATABASE}' tidak ditemukan!")
        print("[INFO] Jalankan 'daftar_wajah.py' terlebih dahulu untuk mendaftarkan wajah.")
        sys.exit(1)
    
    with open(FILE_DATABASE, "rb") as f:
        data = pickle.load(f)
    
    if not data["nama"]:
        print("[PERINGATAN] Database kosong! Daftarkan wajah terlebih dahulu.")
        sys.exit(1)
    
    print(f"[INFO] Database dimuat: {len(data['nama'])} wajah terdaftar")
    for nama in data["nama"]:
        print(f"         → {nama}")
    
    return data["nama"], data["encoding"]


def hubungkan_arduino(port):
    """Buat koneksi serial ke Arduino."""
    try:
        arduino = serial.Serial(port, BAUD_RATE, timeout=1)
        time.sleep(2)  # Tunggu Arduino selesai reset
        print(f"[INFO] Arduino terhubung di {port}")
        return arduino
    except serial.SerialException as e:
        print(f"[ERROR] Gagal terhubung ke Arduino: {e}")
        print("[TIPS] Pastikan port benar dan Arduino terhubung.")
        return None


def kirim_perintah(arduino, perintah):
    """Kirim perintah ke Arduino via serial."""
    if arduino and arduino.is_open:
        try:
            arduino.write(perintah.encode())
            arduino.flush()
        except serial.SerialException as e:
            print(f"[ERROR] Gagal kirim perintah: {e}")


def gambar_info_wajah(frame, lokasi, nama, dikenal, jarak=None):
    """Gambar kotak dan label di sekitar wajah yang terdeteksi."""
    atas, kanan, bawah, kiri = lokasi
    
    # Sesuaikan kembali dari frame yang di-resize
    atas   = int(atas   / SKALA_FRAME)
    kanan  = int(kanan  / SKALA_FRAME)
    bawah  = int(bawah  / SKALA_FRAME)
    kiri   = int(kiri   / SKALA_FRAME)
    
    warna = WARNA_DIKENAL if dikenal else WARNA_ASING
    
    # Gambar kotak wajah
    cv2.rectangle(frame, (kiri, atas), (kanan, bawah), warna, 2)
    
    # Background label
    teks_label = nama if dikenal else "TIDAK DIKENAL"
    if jarak is not None and dikenal:
        teks_label += f" ({jarak:.2f})"
    
    (lebar_teks, tinggi_teks), _ = cv2.getTextSize(
        teks_label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 1)
    
    cv2.rectangle(frame,
                  (kiri, bawah - tinggi_teks - 10),
                  (kiri + lebar_teks + 5, bawah),
                  warna, -1)
    
    cv2.putText(frame, teks_label,
                (kiri + 2, bawah - 5),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                (255, 255, 255), 1)


def tampilkan_status_sistem(frame, status_palang, fps):
    """Tampilkan informasi status sistem di sudut frame."""
    h, w = frame.shape[:2]
    
    # Panel info atas
    cv2.rectangle(frame, (0, 0), (w, 45), (30, 30, 30), -1)
    
    cv2.putText(frame, "SISTEM PALANG PARKIR OTOMATIS",
                (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.55,
                WARNA_INFO, 1)
    
    warna_palang = WARNA_DIKENAL if "TERBUKA" in status_palang else WARNA_ASING
    cv2.putText(frame, f"Palang: {status_palang}  |  FPS: {fps:.1f}",
                (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.45,
                warna_palang, 1)
    
    # Instruksi bawah
    cv2.rectangle(frame, (0, h-25), (w, h), (30, 30, 30), -1)
    cv2.putText(frame, "Tekan Q untuk keluar",
                (10, h-8), cv2.FONT_HERSHEY_SIMPLEX, 0.4,
                (150, 150, 150), 1)


def main():
    print("=" * 55)
    print("   SISTEM PALANG PARKIR OTOMATIS")
    print("   Pengolahan Citra Digital — Face Recognition")
    print("=" * 55)
    
    # ===== Muat Database Wajah =====
    nama_terdaftar, encoding_terdaftar = muat_database()
    encoding_terdaftar_np = [np.array(enc) for enc in encoding_terdaftar]
    
    # ===== Koneksi Arduino =====
    port = cari_port_arduino() or PORT_ARDUINO
    arduino = hubungkan_arduino(port)
    
    if arduino is None:
        print("[PERINGATAN] Sistem berjalan TANPA Arduino (mode simulasi)")
    
    # ===== Buka Kamera =====
    kamera = cv2.VideoCapture(0)
    
    if not kamera.isOpened():
        print("[ERROR] Kamera tidak dapat dibuka!")
        sys.exit(1)
    
    kamera.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
    kamera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    kamera.set(cv2.CAP_PROP_FPS, 30)
    
    print("\n[INFO] Sistem berjalan — Hadapkan wajah ke kamera")
    print("[INFO] Tekan Q untuk menghentikan sistem\n")
    
    # ===== Variabel State =====
    hitung_frame      = 0
    lokasi_wajah_prev = []
    nama_wajah_prev   = []
    dikenal_prev      = []
    jarak_prev        = []
    
    status_palang     = "TERTUTUP"
    waktu_aksi_terakhir = 0
    cooldown_detik    = 3.0  # Jeda minimum antara aksi buka palang
    
    # FPS counter
    fps_waktu = time.time()
    fps_hitung = 0
    fps_display = 0.0
    
    # ===== Loop Utama =====
    while True:
        ret, frame = kamera.read()
        if not ret:
            print("[ERROR] Gagal membaca frame kamera!")
            break
        
        hitung_frame += 1
        fps_hitung  += 1
        
        # Hitung FPS setiap detik
        if time.time() - fps_waktu >= 1.0:
            fps_display = fps_hitung
            fps_hitung  = 0
            fps_waktu   = time.time()
        
        # Baca status dari Arduino
        if arduino and arduino.in_waiting > 0:
            try:
                pesan = arduino.readline().decode().strip()
                if pesan == "PALANG_TERBUKA":
                    status_palang = "TERBUKA"
                elif pesan == "PALANG_TERTUTUP":
                    status_palang = "TERTUTUP"
                elif pesan == "KELUAR_TERDETEKSI":
                    print("[INFO] Kendaraan keluar terdeteksi oleh sensor!")
                    status_palang = "TERBUKA (KELUAR)"
            except:
                pass
        
        # ===== PROSES FACE RECOGNITION (Setiap N Frame) =====
        if hitung_frame % PROSES_TIAP_N == 0:
            # Resize dan konversi warna
            frame_kecil = cv2.resize(frame, (0, 0), fx=SKALA_FRAME, fy=SKALA_FRAME)
            frame_rgb   = cv2.cvtColor(frame_kecil, cv2.COLOR_BGR2RGB)
            
            # Deteksi lokasi wajah
            lokasi_wajah = face_recognition.face_locations(frame_rgb, model="hog")
            
            # Ambil encoding wajah yang terdeteksi
            encodings_frame = face_recognition.face_encodings(frame_rgb, lokasi_wajah)
            
            lokasi_wajah_prev = lokasi_wajah
            nama_wajah_prev   = []
            dikenal_prev      = []
            jarak_prev        = []
            
            waktu_sekarang = time.time()
            
            for encoding in encodings_frame:
                # Hitung jarak ke semua wajah terdaftar
                jarak_ke_db = face_recognition.face_distance(
                    encoding_terdaftar_np, encoding)
                
                idx_terdekat = np.argmin(jarak_ke_db)
                jarak_terkecil = jarak_ke_db[idx_terdekat]
                
                if jarak_terkecil < TOLERANSI:
                    # ===== WAJAH DIKENAL =====
                    nama_dikenal = nama_terdaftar[idx_terdekat]
                    nama_wajah_prev.append(nama_dikenal)
                    dikenal_prev.append(True)
                    jarak_prev.append(jarak_terkecil)
                    
                    # Cek cooldown agar tidak spam perintah
                    if waktu_sekarang - waktu_aksi_terakhir > cooldown_detik:
                        print(f"[AKSES DITERIMA] Selamat datang, {nama_dikenal}! "
                              f"(jarak: {jarak_terkecil:.3f})")
                        kirim_perintah(arduino, 'O')
                        waktu_aksi_terakhir = waktu_sekarang
                        status_palang = "TERBUKA"
                else:
                    # ===== WAJAH TIDAK DIKENAL =====
                    nama_wajah_prev.append("ASING")
                    dikenal_prev.append(False)
                    jarak_prev.append(jarak_terkecil)
                    print(f"[AKSES DITOLAK] Wajah tidak terdaftar "
                          f"(jarak: {jarak_terkecil:.3f})")
        
        # ===== GAMBAR HASIL DETEKSI =====
        for i, lokasi in enumerate(lokasi_wajah_prev):
            if i < len(nama_wajah_prev):
                gambar_info_wajah(
                    frame, lokasi,
                    nama_wajah_prev[i],
                    dikenal_prev[i],
                    jarak_prev[i] if i < len(jarak_prev) else None
                )
        
        # ===== TAMPILKAN STATUS SISTEM =====
        tampilkan_status_sistem(frame, status_palang, fps_display)
        
        # ===== TAMPILKAN FRAME =====
        cv2.imshow("Sistem Palang Parkir Otomatis", frame)
        
        # ===== CEK INPUT KEYBOARD =====
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q') or key == ord('Q'):
            print("\n[INFO] Sistem dihentikan oleh pengguna.")
            break
    
    # ===== BERSIHKAN RESOURCES =====
    kamera.release()
    cv2.destroyAllWindows()
    
    if arduino:
        kirim_perintah(arduino, 'C')  # Pastikan palang tertutup
        time.sleep(0.5)
        arduino.close()
    
    print("[INFO] Sistem berhasil dihentikan.")


if __name__ == "__main__":
    main()