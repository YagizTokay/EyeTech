import os
import time
import ctypes
import psutil
import winsound
import tkinter as tk
from tkinter import ttk
from threading import Thread, Lock
from queue import Queue, Empty
from datetime import datetime

# ---------------------------------------------------------------------------
# 64-BIT WIN32 API TİP GÜVENLİĞİ VE KÜTÜPHANE BAĞLANTILARI
# ---------------------------------------------------------------------------
HDC  = ctypes.c_void_p
BOOL = ctypes.c_bool
DWORD = ctypes.c_ulong

user32   = ctypes.windll.user32
gdi32    = ctypes.windll.gdi32
kernel32 = ctypes.windll.kernel32

user32.GetDC.argtypes           = [ctypes.c_void_p]
user32.GetDC.restype            = HDC
user32.ReleaseDC.argtypes       = [ctypes.c_void_p, HDC]
user32.ReleaseDC.restype        = ctypes.c_int
gdi32.SetDeviceGammaRamp.argtypes = [HDC, ctypes.c_void_p]
gdi32.SetDeviceGammaRamp.restype  = BOOL

GetWin   = user32.GetForegroundWindow
GetPID   = user32.GetWindowThreadProcessId
GetLen   = user32.GetWindowTextLengthW
GetTitle = user32.GetWindowTextW

# ---------------------------------------------------------------------------
# AKTİVİTE TAKİP SİSTEMİ
# ---------------------------------------------------------------------------
desktop       = os.path.join(os.path.expanduser("~"), "Desktop")
oturum_klasor = os.path.join(desktop, "Oturumlar")
if not os.path.exists(oturum_klasor):
    os.makedirs(oturum_klasor)

uygulama_sure = {}
baslangic     = datetime.now()
tarayicilar   = ["chrome", "zen", "firefox", "edge", "opera", "brave"]
system_list   = {
    "windowsterminal", "openconsole", "runtimebroker", "sihost",
    "dllhost", "taskhostw", "widgets", "winlogon", "csrss",
    "lsass", "searchhost", "idle", "system"
}

def pencere_basligi():
    h = GetWin()
    if not h: return ""
    l = GetLen(h)
    buf = ctypes.create_unicode_buffer(l + 1)
    GetTitle(h, buf, l + 1)
    return buf.value

def aktif_uygulama():
    h = GetWin()
    if not h: return None, None
    pid_hold = ctypes.c_ulong()
    GetPID(h, ctypes.byref(pid_hold))
    pid = pid_hold.value
    try:
        p   = psutil.Process(pid)
        exe = p.name().lower()
    except:
        return None, pid
    if exe in ("windowsterminal.exe", "openconsole.exe"):
        for c in p.children():
            cname = c.name().lower()
            if "powershell" in cname or "pwsh" in cname:
                return cname.replace(".exe", ""), c.pid
        return exe.replace(".exe", ""), pid
    if exe == "explorer.exe": return "masaüstü", pid
    return exe.replace(".exe", ""), pid

def sekme_birlestir(exe, title):
    if exe in tarayicilar and title:
        if " - "  in title: title = title.split(" - ")[0]
        elif " — " in title: title = title.split(" — ")[0]
        return f"{exe} – {title.strip()}"
    return exe

def kaydet():
    if not uygulama_sure: return
    dosya_adi = baslangic.strftime("Oturum - %d.%m.%Y %H.%M.txt")
    yol = os.path.join(oturum_klasor, dosya_adi)
    with open(yol, "w", encoding="utf-8") as f:
        f.write(f"=== Arka Plan Oturumu ({baslangic.strftime('%H:%M:%S')}) ===\n")
        for app, saniye in uygulama_sure.items():
            dakika = saniye // 60
            sn     = saniye % 60
            f.write(f"{app}: {dakika} dk {sn} sn\n")
        f.write("=====================================\n")

def aktivite_takip_dongusu():
    save_counter = 0
    try:
        while True:
            exe, pid = aktif_uygulama()
            title    = pencere_basligi()
            if not exe or exe in system_list:
                time.sleep(1)
                continue
            app = sekme_birlestir(exe, title)
            if app not in uygulama_sure: uygulama_sure[app] = 0
            uygulama_sure[app] += 1
            save_counter += 1
            if save_counter >= 10:
                kaydet()
                save_counter = 0
            time.sleep(1)
    finally:
        kaydet()

# ---------------------------------------------------------------------------
# SAĞLIK VE ERGONOMİ SİSTEMİ
# ---------------------------------------------------------------------------
GECE_SAATI = 22

def yas_ayarlarini_al(yas):
    if 0 <= yas <= 2:
        return {
            "goz_mola_dk": 0, "kisa_mola_dk": 0, "uzun_mola_dk": 0, "gunluk_dk": 15,
            "aciklama": "0-2 Yaş: Günlük maks 15 dk (Sadece aileyle görüntülü konuşma).",
            "goz": "", "kisa": "", "uzun": "",
            "gunluk": "GÜNLÜK MAKSİMUM SÜRE ({gunluk}) DOLDU!\nLütfen ekranı derhal kapatın.",
        }
    elif 3 <= yas <= 5:
        return {
            "goz_mola_dk": 0, "kisa_mola_dk": 20, "uzun_mola_dk": 0, "gunluk_dk": 60,
            "aciklama": "3-5 Yaş: Günlük max 1 saat. 20 dk'da bir ara.",
            "goz": "",
            "kisa": "Ara Verme Vakti!\nLütfen ekranı 1-2 dakika kapatıp gözlerinizi dinlendirin.",
            "uzun": "BÜYÜK DİNLENME MOLASI!\nÜst üste 3 kısa mola geçirdiniz. Lütfen ekran başından kalkın ve oyun oynayarak dinlenin.",
            "gunluk": "GÜNLÜK MAKSİMUM SÜRE ({gunluk}) DOLDU!\nLütfen ekranı tamamen kapatın.",
        }
    elif 6 <= yas <= 12:
        return {
            "goz_mola_dk": 20, "kisa_mola_dk": 30, "uzun_mola_dk": 120, "gunluk_dk": 90,
            "aciklama": "6-12 Yaş: Günlük max 1.5 saat. 20 dk'da bir göz molası, 30 dk'da bir kısa mola, 2 saatte bir uzun mola.",
            "goz": "Göz Molası!\n6 metre uzaktaki bir nesneye en az 20 saniye odaklanarak gözlerinizi dinlendirin.",
            "kisa": "Kısa Mola Vakti!\nAyağa kalkın, derin nefes alın ve hafif esneme hareketleri yaparak omurganızdaki yükü hafifletin.",
            "uzun": "BÜYÜK DİNLENME MOLASI!\nUzun süredir ekrana bakıyorsunuz. Lütfen 10-15 dakika boyunca ekrandan tamamen uzaklaşın, odadan ayrılın.",
            "gunluk": "GÜNLÜK MAKSİMUM SÜRE ({gunluk}) DOLDU!\nOkul ödevleri haricindeki ekran kullanımını sonlandırın.",
        }
    elif 13 <= yas <= 18:
        return {
            "goz_mola_dk": 20, "kisa_mola_dk": 30, "uzun_mola_dk": 120, "gunluk_dk": 120,
            "aciklama": "13-18 Yaş: Günlük max 2 saat. 20 dk'da bir göz molası, 30 dk'da bir kısa mola, 2 saatte bir uzun mola.",
            "goz": "Göz Molası!\n6 metre uzaktaki bir nesneye en az 20 saniye odaklanarak göz siliyer kaslarınızı gevşetin.",
            "kisa": "Kısa Mola Zamanı!\nAyağa kalkın, derin nefes alın ve omurga üzerindeki statik yükü hafifletecek hafif esneme egzersizleri yapın.",
            "uzun": "BÜYÜK DİNLENME MOLASI!\nGöz sağlığınız ve postürünüz için 10-15 dakika boyunca ekrandan ve çalışma ortamından tamamen uzaklaşın.",
            "gunluk": "GÜNLÜK MAKSİMUM SÜRE ({gunluk}) DOLDU!\nEğlence ve sosyal medya için limitiniz bitti.",
        }
    elif 19 <= yas <= 64:
        return {
            "goz_mola_dk": 20, "kisa_mola_dk": 30, "uzun_mola_dk": 120, "gunluk_dk": 150,
            "aciklama": "19-64 Yaş: Max 2.5 saat. 20 dk'da bir göz molası (20-20-20), 30 dk'da bir kısa mola, 2 saatte bir uzun mola.",
            "goz": "20-20-20 Göz Molası!\n6 metre uzaktaki bir nesneye en az 20 saniye odaklanarak göz siliyer kaslarınızı gevşetin.",
            "kisa": "Kısa Mola!\nAyağa kalkın, derin nefes alın ve omurga üzerindeki statik yükü hafifletecek hafif esneme egzersizleri yapın.",
            "uzun": "BÜYÜK ERGONOMİ MOLASI!\n10-15 dakika boyunca ekrandan ve çalışma ortamından tamamen uzaklaşın. Ayağa kalkın ve esneme hareketleri yapın.",
            "gunluk": "GÜNLÜK MAKSİMUM SÜRE ({gunluk}) DOLDU!\nİş/Ders dışındaki boş zaman limitiniz doldu, lütfen dinlenin.",
        }
    else:
        return {
            "goz_mola_dk": 20, "kisa_mola_dk": 30, "uzun_mola_dk": 120, "gunluk_dk": 180,
            "aciklama": "65+ Yaş: Günlük max 3 saat. 20 dk'da bir göz molası, 30 dk'da bir kısa mola, 2 saatte bir uzun mola.",
            "goz": "Göz Molası!\n6 metre uzaktaki bir nesneye en az 20 saniye odaklanarak gözlerinizi dinlendirin.",
            "kisa": "Kısa Mola!\nAyağa kalkın, derin nefes alın ve hafif esneme hareketleri yaparak omurganızdaki yükü hafifletin.",
            "uzun": "BÜYÜK DİNLENME MOLASI!\n10-15 dakika boyunca ekrandan tamamen uzaklaşın. Kan dolaşımınızı dengelemek için yürüyüş yapın.",
            "gunluk": "GÜNLÜK MAKSİMUM SÜRE ({gunluk}) DOLDU!\nLütfen ekran başından tamamen ayrılın.",
        }

def sure_formatla(saniye):
    if saniye <= 0: return ""
    if saniye < 60: return f"{int(saniye)} saniye"
    dakika = int(saniye // 60)
    if dakika < 60: return f"{dakika} dakika"
    saat = dakika // 60
    kalan_dk = dakika % 60
    if kalan_dk == 0: return f"{saat} saat"
    return f"{saat} saat {kalan_dk} dakika"

class MaviIsikOverlay:
    def __init__(self): self.aktif = False
    def _renk_ayarla(self, sicaklik=0.75):
        try:
            hdc = user32.GetDC(None)
            if not hdc: return
            RampDizisi = ((ctypes.c_ushort * 256) * 3)()
            for i in range(256):
                orjinal_renk      = int((i * 65535) / 255)
                RampDizisi[0][i]  = orjinal_renk
                RampDizisi[1][i]  = int(orjinal_renk * (1.0 - (sicaklik * 0.15)))
                RampDizisi[2][i]  = int(orjinal_renk * (1.0 - (sicaklik * 0.55)))
            gdi32.SetDeviceGammaRamp(hdc, ctypes.byref(RampDizisi))
            user32.ReleaseDC(None, hdc)
        except: pass
    def ac(self):
        if self.aktif: return
        self.aktif = True
        self._renk_ayarla(0.75)
    def kapat(self):
        if not self.aktif: return
        self.aktif = False
        self._renk_ayarla(0.0)

overlay = MaviIsikOverlay()

PHANDLER_ROUTINE = ctypes.WINFUNCTYPE(BOOL, DWORD)
def konsol_kapanma_yoneticisi(ctrl_type):
    overlay.kapat()
    kaydet()
    return False
_konsol_tutucu_referans = PHANDLER_ROUTINE(konsol_kapanma_yoneticisi)
kernel32.SetConsoleCtrlHandler(_konsol_tutucu_referans, True)

def ses_cal(tip="normal"):
    def _cal():
        try:
            if tip == "buyuk":
                for freq, dur in [(600, 200), (800, 200), (600, 200), (800, 400)]:
                    winsound.Beep(freq, dur)
                    time.sleep(0.05)
            else:
                winsound.Beep(660, 220)
        except: pass
    Thread(target=_cal, daemon=True).start()

def popup_goster(root, baslik, mesaj, tip="normal", sure_ms=9000):
    pencere = tk.Toplevel(root)
    pencere.overrideredirect(True)
    pencere.attributes("-topmost", True)
    pencere.attributes("-alpha", 0.97)

    ekran_w = root.winfo_screenwidth()
    ekran_h = root.winfo_screenheight()

    if tip == "buyuk":
        bg, fg_b  = "#2b0000", "#ff3333"
        gw, gh    = 650, 360
        bf, mf    = ("Segoe UI", 20, "bold"), ("Segoe UI", 13, "bold")
        btn_bg    = "#cc0000"
        x = (ekran_w - gw) // 2
        y = (ekran_h - gh) // 2
    else:
        bg, fg_b  = "#1a1a2e", "#e94560"
        gw, gh    = 480, 195
        bf, mf    = ("Segoe UI", 12, "bold"), ("Segoe UI", 10, "bold")
        btn_bg    = "#e94560"
        x = ekran_w - gw - 20
        y = ekran_h - gh - 60

    pencere.configure(bg=bg)
    pencere.geometry(f"{gw}x{gh}+{x}+{y}")

    if tip == "buyuk":
        tk.Label(pencere, text="⛔ DİKKAT ⛔", bg=bg, fg="#ff3333",
                 font=("Segoe UI", 35, "bold")).pack(pady=(20, 0))

    tk.Label(pencere, text=baslik, bg=bg, fg=fg_b, font=bf,
             anchor="center", pady=10).pack(fill="x")
    tk.Label(pencere, text=mesaj, bg=bg, fg="#ffffff", font=mf,
             justify="center", wraplength=gw - 40).pack(fill="x", padx=20)

    kalan_saniye = sure_ms // 1000
    lbl_sayac = tk.Label(pencere,
                         text=f"Bu uyarı {kalan_saniye} saniye içinde otomatik kapanacaktır.",
                         bg=bg, fg="#888888", font=("Segoe UI", 9, "italic"))
    lbl_sayac.pack(pady=5)

    tk.Button(pencere, text="KAPAT", bg=btn_bg, fg="#ffffff",
              font=("Segoe UI", 10, "bold"), relief="flat", cursor="hand2",
              command=pencere.destroy, padx=20, pady=8).pack(pady=10)

    def geri_say(sure_sol):
        if not pencere.winfo_exists(): return
        if sure_sol <= 0:
            pencere.destroy()
        else:
            lbl_sayac.config(text=f"Bu uyarı {sure_sol} saniye içinde otomatik kapanacaktır.")
            pencere.after(1000, lambda: geri_say(sure_sol - 1))
    geri_say(kalan_saniye)

# ---------------------------------------------------------------------------
# SAĞLIK UYARI SİSTEMİ
# Her uyarı için ayrı bir thread açılır.
# time.sleep(bekleme_suresi) → kuyruga yaz → popup.
# Test modunda 1 gerçek saniye = 1 dakika: dk kadar saniye beklenir.
# Normal modda dk * 60 saniye beklenir.
# carpan_degistir() nesil numarasını artırır; eski thread'ler uyanınca
# nesil uyuşmadığını görüp sessizce çıkar.
# ---------------------------------------------------------------------------
class SaglikUyariSistemi:

    def __init__(self, yas):
        ayar          = yas_ayarlarini_al(yas)
        self.aciklama = ayar["aciklama"]
        self.queue    = Queue()
        self.cikis    = False
        self._gece_yapildi = False
        self._nesil        = 0
        self._nesil_lock   = Lock()
        self._test_modu    = False   # False = normal, True = test (1sn=1dk)

        fmt_gunluk = sure_formatla(ayar["gunluk_dk"] * 60)
        self.BILDIRIMLER = {
            "goz_molasi":   ("Göz Molası",            ayar["goz"],                                 "normal"),
            "kisa_mola":    ("Kısa Mola",             ayar["kisa"],                                "normal"),
            "uzun_mola":    ("BÜYÜK DİNLENME MOLASI", ayar["uzun"],                                "buyuk"),
            "gunluk_limit": ("GÜNLÜK LİMİT AŞIMI",    ayar["gunluk"].format(gunluk=fmt_gunluk),    "buyuk"),
        }

        # (anahtar, dakika_cinsinden_sure)  — 0 ise bu yaş için devre dışı
        self._program = [
            ("goz_molasi",   ayar["goz_mola_dk"]),
            ("kisa_mola",    ayar["kisa_mola_dk"]),
            ("uzun_mola",    ayar["uzun_mola_dk"]),
            ("gunluk_limit", ayar["gunluk_dk"]),
        ]

    # ------------------------------------------------------------------
    # Her uyarı için ayrı thread
    # ------------------------------------------------------------------
    def _bekle_ve_bildir(self, anahtar, bekleme_sn, nesil):
        time.sleep(bekleme_sn)
        with self._nesil_lock:
            if nesil != self._nesil or self.cikis:
                return          # carpan değişti veya uygulama kapandı
        self.queue.put(anahtar)

    def _gece_bekle(self):
        while not self.cikis:
            if datetime.now().hour >= GECE_SAATI and not self._gece_yapildi:
                self._gece_yapildi = True
                self.queue.put("__gece__")
                return
            time.sleep(30)

    # ------------------------------------------------------------------
    # Tüm uyarı thread'lerini (yeniden) başlat
    # ------------------------------------------------------------------
    def _tum_uyarilari_baslat(self):
        with self._nesil_lock:
            self._nesil += 1
            nesil = self._nesil

        for anahtar, dk in self._program:
            if dk <= 0:
                continue
            # Test modunda dakika = saniye; normal modda dakika * 60
            bekleme = dk if self._test_modu else dk * 60
            Thread(target=self._bekle_ve_bildir,
                   args=(anahtar, bekleme, nesil),
                   daemon=True).start()

    # ------------------------------------------------------------------
    # Dışarıdan çağrılan metodlar
    # ------------------------------------------------------------------
    def carpan_degistir(self, yeni_carpan):
        self._test_modu = (yeni_carpan == 60)
        self._tum_uyarilari_baslat()

    def sayac_dongusu(self):
        Thread(target=self._gece_bekle, daemon=True).start()
        self._tum_uyarilari_baslat()

# ---------------------------------------------------------------------------
# GÖRSEL ARAYÜZ PANELİ
# ---------------------------------------------------------------------------
class KontrolPaneli:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Sağlık & Ergonomi Asistanı")
        self.root.geometry("420x340")
        self.root.configure(bg="#1a1a2e")
        self.root.resizable(False, False)

        ew = self.root.winfo_screenwidth()
        eh = self.root.winfo_screenheight()
        self.root.geometry(f"+{(ew-420)//2}+{(eh-340)//2}")
        self.sistem = None

        tk.Label(self.root, text="SAĞLIK & ERGONOMİ ASİSTANI",
                 bg="#1a1a2e", fg="#e94560",
                 font=("Segoe UI", 14, "bold"), pady=15).pack()
        tk.Label(self.root, text="Lütfen Yaşınızı Seçiniz:",
                 bg="#1a1a2e", fg="#cccccc", font=("Segoe UI", 10)).pack(pady=5)

        self.yas_spin = ttk.Spinbox(self.root, from_=0, to=99, width=10,
                                    font=("Segoe UI", 11))
        self.yas_spin.set(25)
        self.yas_spin.pack(pady=5)

        self.btn_baslat = tk.Button(self.root, text="Sistemi Başlat",
                                    bg="#e94560", fg="white",
                                    font=("Segoe UI", 11, "bold"),
                                    relief="flat", cursor="hand2",
                                    command=self.sistemi_baslat,
                                    padx=20, pady=8)
        self.btn_baslat.pack(pady=15)

        self.lbl_bilgi = tk.Label(self.root,
                                   text="Sistem Hazır. Yaşınızı seçip başlatın.",
                                   bg="#1a1a2e", fg="#888888",
                                   font=("Segoe UI", 9), wraplength=380)
        self.lbl_bilgi.pack(pady=10)

        self.btn_test = tk.Button(self.root, text="Test Modu: KAPALI",
                                   bg="#2e2e50", fg="white",
                                   font=("Segoe UI", 9), relief="flat",
                                   cursor="hand2",
                                   command=self.test_modu_degis,
                                   state="disabled")
        self.btn_test.pack(side="bottom", fill="x", pady=0)
        self.root.protocol("WM_DELETE_WINDOW", self.kapat)

    def sistemi_baslat(self):
        try:
            yas = int(self.yas_spin.get())
        except ValueError:
            return

        self.sistem = SaglikUyariSistemi(yas)
        self.lbl_bilgi.config(text=f"Aktif Kural Seti:\n{self.sistem.aciklama}",
                              fg="#00ffcc")
        self.btn_baslat.config(state="disabled", bg="#444444",
                               text="Sistem Arka Planda Aktif")
        self.yas_spin.config(state="disabled")
        self.btn_test.config(state="normal")

        Thread(target=self.sistem.sayac_dongusu, daemon=True).start()
        self.root.after(500, self.filtre_sorgu_penceresi)
        self.root.after(100, self.kuyruk_kontrol)

    def filtre_sorgu_penceresi(self):
        p = tk.Toplevel(self.root)
        p.overrideredirect(True)
        p.attributes("-topmost", True)
        p.configure(bg="#1a1a2e")
        gw, gh = 360, 140
        ew = self.root.winfo_screenwidth()
        eh = self.root.winfo_screenheight()
        p.geometry(f"{gw}x{gh}+{(ew-gw)//2}+{(eh-gh)//2}")

        tk.Label(p, text="Mavi Işık Filtresi", bg="#1a1a2e", fg="#e94560",
                 font=("Segoe UI", 11, "bold"), pady=10).pack()
        tk.Label(p, text="Mavi ışık filtresi açılsın mı?",
                 bg="#1a1a2e", fg="#cccccc", font=("Segoe UI", 9)).pack()

        def evet(): p.destroy(); overlay.ac()
        def hayir(): p.destroy()

        f = tk.Frame(p, bg="#1a1a2e")
        f.pack(pady=15)
        tk.Button(f, text="Aç", bg="#e94560", fg="white",
                  font=("Segoe UI", 9, "bold"), width=8,
                  command=evet, relief="flat", cursor="hand2").pack(side="left", padx=10)
        tk.Button(f, text="Kapat", bg="#2e2e50", fg="white",
                  font=("Segoe UI", 9), width=8,
                  command=hayir, relief="flat", cursor="hand2").pack(side="left", padx=10)

    def test_modu_degis(self):
        if not self.sistem: return
        if not self.sistem._test_modu:
            self.sistem.carpan_degistir(60)
            self.btn_test.config(text="Test Modu: AKTİF (1sn = 1dk)", bg="#00aa7f")
        else:
            self.sistem.carpan_degistir(1)
            self.btn_test.config(text="Test Modu: KAPALI", bg="#2e2e50")

    def kuyruk_kontrol(self):
        if not self.sistem: return
        try:
            while True:
                tip = self.sistem.queue.get_nowait()
                if tip == "__gece__":
                    overlay.ac()
                    popup_goster(self.root, "Uyku Vakti Kuralı",
                                 "Saat 22:00 oldu.\nUykudan 1 saat önce ekran ışığını kısmalısınız.\nFiltre otomatik devreye alındı.",
                                 tip="buyuk", sure_ms=15000)
                    ses_cal("buyuk")
                else:
                    baslik, mesaj, popup_tip = self.sistem.BILDIRIMLER[tip]
                    sure = 20000 if popup_tip == "buyuk" else 10000
                    ses_cal(popup_tip)
                    popup_goster(self.root, baslik, mesaj, tip=popup_tip, sure_ms=sure)
        except Empty:
            pass
        self.root.after(100, self.kuyruk_kontrol)

    def kapat(self):
        if self.sistem: self.sistem.cikis = True
        overlay.kapat()
        self.root.destroy()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    Thread(target=aktivite_takip_dongusu, daemon=True).start()
    panel = KontrolPaneli()
    panel.run()
