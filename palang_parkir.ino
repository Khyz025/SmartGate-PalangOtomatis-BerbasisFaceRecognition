#include <Servo.h>

const int PIN_SERVO       = 9;
const int PIN_TRIG        = 7;
const int PIN_ECHO        = 8;

const int SUDUT_TUTUP     = 0;
const int SUDUT_BUKA      = 90;
const int DELAY_BUKA_MS   = 2000; // Delay tutup: 2 detik
const int COOLDOWN_MS     = 3000; // Jeda setelah tutup: 3 detik
const int JARAK_KELUAR_CM = 20;

Servo palang;

bool palangTerbuka        = false;
unsigned long waktuBuka   = 0;
unsigned long waktuTutup  = 0; // ← BARU: catat kapan palang terakhir ditutup

void setup() {
  Serial.begin(9600);
  palang.attach(PIN_SERVO);
  palang.write(SUDUT_TUTUP);
  pinMode(PIN_TRIG, OUTPUT);
  pinMode(PIN_ECHO, INPUT);
  delay(500);
  Serial.println("SISTEM SIAP");
}

void loop() {
  bool dalamCooldown = (millis() - waktuTutup < COOLDOWN_MS); // ← cek jeda

  // ----- Cek Perintah dari Python (Jalur Masuk) -----
  if (Serial.available() > 0) {
    char perintah = Serial.read();
    if (perintah == 'O') {
      if (!dalamCooldown) {
        bukaPalang();
      } else {
        Serial.println("COOLDOWN_AKTIF"); // beri tahu Python masih dalam jeda
      }
    } else if (perintah == 'C') {
      tutupPalang();
    }
  }

  // ----- Cek Sensor Ultrasonik (Jalur Keluar) -----
  float jarak = ukurJarak();
  if (jarak > 0 && jarak < JARAK_KELUAR_CM && !palangTerbuka && !dalamCooldown) {
    Serial.println("KELUAR_TERDETEKSI");
    bukaPalang();
  }

  // ----- Auto Tutup Setelah 1.5 Detik -----
  if (palangTerbuka && (millis() - waktuBuka >= DELAY_BUKA_MS)) {
    tutupPalang();
  }

  delay(100);
}

void bukaPalang() {
  palang.write(SUDUT_BUKA);
  palangTerbuka = true;
  waktuBuka = millis();
  Serial.println("PALANG_TERBUKA");
}

void tutupPalang() {
  palang.write(SUDUT_TUTUP);
  palangTerbuka = false;
  waktuTutup = millis(); // ← catat waktu penutupan → mulai cooldown 3 detik
  Serial.println("PALANG_TERTUTUP");
}

float ukurJarak() {
  digitalWrite(PIN_TRIG, LOW);
  delayMicroseconds(2);
  digitalWrite(PIN_TRIG, HIGH);
  delayMicroseconds(10);
  digitalWrite(PIN_TRIG, LOW);
  long durasi = pulseIn(PIN_ECHO, HIGH, 30000);
  if (durasi == 0) return -1;
  return (durasi * 0.0343) / 2.0;
}