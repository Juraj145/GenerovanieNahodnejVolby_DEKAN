# -*- coding: utf-8 -*-
"""
Voľba poradia vystúpenia kandidátov na dekana.

Program umožňuje:
  - zadať kandidátov na dekana (titul(y) pred menom, meno, priezvisko, titul(y) za priezviskom),
  - uložiť a znova načítať zoznam kandidátov,
  - vyzve kandidátov, aby v abecednom poradí pristúpili,
  - žrebovanie poradia po jednotlivých kandidátoch: každý kandidát stlačí ENTER
    alebo medzerník na spustenie losovania svojej pozície a opätovným stlačením
    ENTER/medzerníka losovanie zastaví a vylosuje sa mu poradové číslo,
  - pri spustení skontroluje, či je dostupná novšia verzia, a ponúkne aktualizáciu.

Podmienka: kandidáti musia byť minimálne dvaja.
"""

import json
import os
import random
import shutil
import ssl
import subprocess
import sys
import tempfile
import threading
import urllib.request
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

try:
    import certifi
    _CA_SUBOR = certifi.where()
except Exception:
    _CA_SUBOR = None


def ssl_kontext() -> ssl.SSLContext:
    """SSL kontext s overením certifikátov (certifi balík kvôli Windows)."""
    if _CA_SUBOR:
        return ssl.create_default_context(cafile=_CA_SUBOR)
    return ssl.create_default_context()


APP_VERSION = "1.3.0"

REPO_OWNER = "Juraj145"
REPO_NAME = "GenerovanieNahodnejVolby_DEKAN"
VERSION_URL = f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/main/VERSION"
INSTALLER_URL = (
    f"https://github.com/{REPO_OWNER}/{REPO_NAME}/releases/latest/download/"
    "VolbaPoradiaDekana_Setup.exe"
)


def resource_path(nazov: str) -> str:
    """Cesta k priloženému súboru (funguje aj v PyInstaller .exe)."""
    zaklad = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(zaklad, nazov)


def data_dir() -> str:
    """Priečinok na automatické ukladanie údajov používateľa."""
    zaklad = os.environ.get("APPDATA") or os.path.expanduser("~")
    cesta = os.path.join(zaklad, "GNV_DEKAN")
    os.makedirs(cesta, exist_ok=True)
    return cesta


AUTOSAVE_SUBOR = os.path.join(data_dir(), "kandidati.json")


def verzia_na_n_ticu(verzia: str):
    cisla = []
    for cast in verzia.strip().lstrip("vV").split("."):
        digits = "".join(ch for ch in cast if ch.isdigit())
        cisla.append(int(digits) if digits else 0)
    return tuple(cisla)


class Kandidat:
    def __init__(self, meno: str, priezvisko: str, tituly_pred: str = "", tituly_za: str = ""):
        self.meno = meno.strip()
        self.priezvisko = priezvisko.strip()
        self.tituly_pred = tituly_pred.strip()
        self.tituly_za = tituly_za.strip()

    def cele_meno(self) -> str:
        casti = []
        if self.tituly_pred:
            casti.append(self.tituly_pred)
        casti.append(self.meno)
        casti.append(self.priezvisko)
        text = " ".join(casti)
        if self.tituly_za:
            text += f", {self.tituly_za}"
        return text

    def kluc_abecedne(self):
        # Abecedné poradie podľa priezviska, potom mena
        return (self.priezvisko.lower(), self.meno.lower())

    def to_dict(self) -> dict:
        return {
            "meno": self.meno,
            "priezvisko": self.priezvisko,
            "tituly_pred": self.tituly_pred,
            "tituly_za": self.tituly_za,
        }

    @staticmethod
    def from_dict(d: dict) -> "Kandidat":
        return Kandidat(
            d.get("meno", ""),
            d.get("priezvisko", ""),
            d.get("tituly_pred", d.get("tituly", "")),  # spätná kompatibilita
            d.get("tituly_za", ""),
        )


class Aplikacia(tk.Tk):
    INTERVAL_MS = 70  # rýchlosť striedania čísel počas losovania

    def __init__(self):
        super().__init__()
        self.title(f"Voľba poradia vystúpenia kandidátov na dekana  (v{APP_VERSION})")
        self.geometry("860x740")
        self.minsize(720, 660)

        try:
            self.iconbitmap(resource_path("app.ico"))
        except Exception:
            pass

        self.kandidati: list[Kandidat] = []

        # stav žrebovania
        self.volba_aktivna = False
        self.faza = None  # None | "cakam_start" | "generujem"
        self._job = None
        self.poradie_kandidatov: list[Kandidat] = []
        self.aktualny_index = 0
        self.volne_pozicie: list[int] = []
        self.priradene: dict[int, int] = {}  # index v poradie_kandidatov -> pozícia

        self._vytvor_styl()
        self._vytvor_widgety()

        self.bind("<Return>", self._klaves)
        self.bind("<space>", self._klaves)

        self._nacitaj_auto()
        self.protocol("WM_DELETE_WINDOW", self._pri_zatvoreni)
        self.after(800, self._skontroluj_aktualizacie)

    # ------------------------------------------------------------------ UI
    def _vytvor_styl(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("Nadpis.TLabel", font=("Segoe UI", 16, "bold"))
        style.configure("Podnadpis.TLabel", font=("Segoe UI", 10))
        style.configure("Velke.TButton", font=("Segoe UI", 13, "bold"), padding=10)
        style.configure("Cislo.TLabel", font=("Segoe UI", 30, "bold"), foreground="#1f77b4")

    def _vytvor_widgety(self):
        hlavny = ttk.Frame(self, padding=12)
        hlavny.pack(fill="both", expand=True)

        hlavicka = ttk.Frame(hlavny)
        hlavicka.pack(fill="x")
        ttk.Label(
            hlavicka,
            text="Voľba poradia vystúpenia kandidátov na dekana",
            style="Nadpis.TLabel",
        ).pack(side="left", anchor="w")
        self.b_aktualizovat = ttk.Button(
            hlavicka, text="Aktualizovať program", command=self.aktualizuj_rucne, takefocus=False
        )
        self.b_aktualizovat.pack(side="right")

        # --- Formulár na zadanie kandidáta ---
        formular = ttk.LabelFrame(hlavny, text="Zadanie kandidáta", padding=10)
        formular.pack(fill="x", pady=(12, 8))

        ttk.Label(formular, text="Titul(y) pred menom:").grid(
            row=0, column=0, sticky="w", padx=4, pady=4
        )
        self.e_tituly_pred = ttk.Entry(formular, width=20)
        self.e_tituly_pred.grid(row=0, column=1, sticky="we", padx=4, pady=4)

        ttk.Label(formular, text="Meno:").grid(row=0, column=2, sticky="w", padx=4, pady=4)
        self.e_meno = ttk.Entry(formular, width=20)
        self.e_meno.grid(row=0, column=3, sticky="we", padx=4, pady=4)

        ttk.Label(formular, text="Priezvisko:").grid(row=1, column=0, sticky="w", padx=4, pady=4)
        self.e_priezvisko = ttk.Entry(formular, width=20)
        self.e_priezvisko.grid(row=1, column=1, sticky="we", padx=4, pady=4)

        ttk.Label(formular, text="Titul(y) za priezviskom:").grid(
            row=1, column=2, sticky="w", padx=4, pady=4
        )
        self.e_tituly_za = ttk.Entry(formular, width=20)
        self.e_tituly_za.grid(row=1, column=3, sticky="we", padx=4, pady=4)

        self.b_pridaj = ttk.Button(formular, text="Pridať kandidáta", command=self.pridaj_kandidata)
        self.b_pridaj.grid(row=0, column=4, rowspan=2, padx=8, pady=4, sticky="ns")

        formular.columnconfigure(1, weight=1)
        formular.columnconfigure(3, weight=1)

        for e in (self.e_tituly_pred, self.e_meno, self.e_priezvisko, self.e_tituly_za):
            e.bind("<Return>", self._enter_vo_formulari)

        # --- Zoznam kandidátov ---
        zoznam_ramec = ttk.LabelFrame(
            hlavny, text="Zadaní kandidáti (abecedné poradie podľa priezviska)", padding=10
        )
        zoznam_ramec.pack(fill="both", expand=True, pady=8)

        self.lb_kandidati = tk.Listbox(zoznam_ramec, height=6, font=("Segoe UI", 11))
        self.lb_kandidati.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(zoznam_ramec, orient="vertical", command=self.lb_kandidati.yview)
        sb.pack(side="left", fill="y")
        self.lb_kandidati.config(yscrollcommand=sb.set)

        ovladanie = ttk.Frame(zoznam_ramec, padding=(10, 0))
        ovladanie.pack(side="left", fill="y")
        self.b_odstran = ttk.Button(
            ovladanie, text="Odstrániť vybraného", command=self.odstran_kandidata
        )
        self.b_odstran.pack(fill="x", pady=2)
        self.b_vymaz = ttk.Button(ovladanie, text="Vymazať všetkých", command=self.vymaz_vsetkych)
        self.b_vymaz.pack(fill="x", pady=2)
        ttk.Separator(ovladanie, orient="horizontal").pack(fill="x", pady=6)
        self.b_uloz = ttk.Button(ovladanie, text="Uložiť kandidátov…", command=self.uloz_kandidatov)
        self.b_uloz.pack(fill="x", pady=2)
        self.b_nacitaj = ttk.Button(
            ovladanie, text="Načítať kandidátov…", command=self.nacitaj_kandidatov
        )
        self.b_nacitaj.pack(fill="x", pady=2)

        # --- Výzva ---
        self.l_vyzva = ttk.Label(
            hlavny,
            text="Vážení kandidáti, prosím pristúpte v abecednom poradí podľa priezviska.",
            style="Podnadpis.TLabel",
            foreground="#0a4",
        )
        self.l_vyzva.pack(anchor="w", pady=(4, 6))

        # --- Tlačidlo žrebovania ---
        self.b_generuj = ttk.Button(
            hlavny,
            text="Spustiť voľbu poradia",
            style="Velke.TButton",
            command=self.prepni_volbu,
            takefocus=False,
        )
        self.b_generuj.pack(fill="x", pady=6)

        # --- Žreb (veľké číslo) ---
        zreb = ttk.Frame(hlavny)
        zreb.pack(fill="x")
        ttk.Label(zreb, text="Vylosované poradové číslo:", style="Podnadpis.TLabel").pack(side="left")
        self.lbl_cislo = ttk.Label(zreb, text="–", style="Cislo.TLabel")
        self.lbl_cislo.pack(side="left", padx=12)

        # --- Výsledok ---
        vysledok_ramec = ttk.LabelFrame(hlavny, text="Poradie vystúpenia", padding=10)
        vysledok_ramec.pack(fill="both", expand=True, pady=(6, 0))
        self.txt_vysledok = tk.Text(
            vysledok_ramec, height=8, font=("Segoe UI", 12), state="disabled", wrap="word"
        )
        self.txt_vysledok.pack(fill="both", expand=True)

        self._obnov_zoznam()

    # -------------------------------------------------------------- kandidáti
    def _enter_vo_formulari(self, _event):
        # Enter vo formulári pridá kandidáta (nie ovládanie žrebovania)
        if not self.volba_aktivna:
            self.pridaj_kandidata()
        return "break"

    def pridaj_kandidata(self):
        if self.volba_aktivna:
            return
        meno = self.e_meno.get().strip()
        priezvisko = self.e_priezvisko.get().strip()
        tituly_pred = self.e_tituly_pred.get().strip()
        tituly_za = self.e_tituly_za.get().strip()

        if not meno or not priezvisko:
            messagebox.showwarning(
                "Neúplné údaje", "Zadajte aspoň meno a priezvisko kandidáta."
            )
            return

        self.kandidati.append(Kandidat(meno, priezvisko, tituly_pred, tituly_za))
        for e in (self.e_tituly_pred, self.e_meno, self.e_priezvisko, self.e_tituly_za):
            e.delete(0, "end")
        self.e_tituly_pred.focus_set()
        self._obnov_zoznam()
        self._uloz_auto()

    def odstran_kandidata(self):
        if self.volba_aktivna:
            return
        vyber = self.lb_kandidati.curselection()
        if not vyber:
            return
        index = vyber[0]
        zoradeni = sorted(self.kandidati, key=Kandidat.kluc_abecedne)
        cil = zoradeni[index]
        self.kandidati.remove(cil)
        self._obnov_zoznam()
        self._uloz_auto()

    def vymaz_vsetkych(self):
        if self.volba_aktivna:
            return
        if not self.kandidati:
            return
        if messagebox.askyesno("Vymazať", "Naozaj vymazať všetkých kandidátov?"):
            self.kandidati.clear()
            self._obnov_zoznam()
            self._uloz_auto()

    def _obnov_zoznam(self):
        self.lb_kandidati.delete(0, "end")
        for k in sorted(self.kandidati, key=Kandidat.kluc_abecedne):
            self.lb_kandidati.insert("end", k.cele_meno())

    # ------------------------------------------------- ukladanie / načítanie
    def uloz_kandidatov(self):
        if not self.kandidati:
            messagebox.showinfo("Uložiť", "Najprv pridajte aspoň jedného kandidáta.")
            return
        cesta = filedialog.asksaveasfilename(
            title="Uložiť kandidátov",
            defaultextension=".json",
            filetypes=[("Súbor kandidátov", "*.json"), ("Všetky súbory", "*.*")],
            initialfile="kandidati.json",
        )
        if not cesta:
            return
        try:
            self._zapis_subor(cesta)
            messagebox.showinfo("Uložené", f"Kandidáti boli uložení do:\n{cesta}")
        except OSError as e:
            messagebox.showerror("Chyba", f"Súbor sa nepodarilo uložiť:\n{e}")

    def nacitaj_kandidatov(self):
        if self.volba_aktivna:
            return
        cesta = filedialog.askopenfilename(
            title="Načítať kandidátov",
            filetypes=[("Súbor kandidátov", "*.json"), ("Všetky súbory", "*.*")],
        )
        if not cesta:
            return
        try:
            self._citaj_subor(cesta)
        except (OSError, ValueError, json.JSONDecodeError) as e:
            messagebox.showerror("Chyba", f"Súbor sa nepodarilo načítať:\n{e}")
            return
        self._obnov_zoznam()
        self._uloz_auto()
        messagebox.showinfo(
            "Načítané",
            f"Načítaných {len(self.kandidati)} kandidátov. Môžete znova spustiť voľbu poradia.",
        )

    def _zapis_subor(self, cesta: str):
        data = {"verzia": APP_VERSION, "kandidati": [k.to_dict() for k in self.kandidati]}
        with open(cesta, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _citaj_subor(self, cesta: str):
        with open(cesta, "r", encoding="utf-8") as f:
            data = json.load(f)
        zoznam = data.get("kandidati", []) if isinstance(data, dict) else data
        self.kandidati = [
            Kandidat.from_dict(d)
            for d in zoznam
            if d.get("meno") and d.get("priezvisko")
        ]

    def _uloz_auto(self):
        try:
            self._zapis_subor(AUTOSAVE_SUBOR)
        except OSError:
            pass

    def _nacitaj_auto(self):
        if os.path.exists(AUTOSAVE_SUBOR):
            try:
                self._citaj_subor(AUTOSAVE_SUBOR)
                self._obnov_zoznam()
            except (OSError, ValueError, json.JSONDecodeError):
                pass

    def _pri_zatvoreni(self):
        self._uloz_auto()
        self.destroy()

    # ------------------------------------------------------- žrebovanie
    def _klaves(self, _event):
        """ENTER / medzerník ovláda žrebovanie, keď je voľba aktívna."""
        if self.volba_aktivna:
            self._stlac()
            return "break"
        return None

    def prepni_volbu(self):
        if not self.volba_aktivna:
            self._zacni_volbu()
        else:
            self._stlac()
        self.focus_set()  # aby medzerník neaktivoval tlačidlo

    def _zacni_volbu(self):
        if len(self.kandidati) < 2:
            messagebox.showwarning(
                "Málo kandidátov",
                "Kandidáti musia byť minimálne dvaja. Pridajte ešte aspoň jedného.",
            )
            return
        self.volba_aktivna = True
        self.poradie_kandidatov = sorted(self.kandidati, key=Kandidat.kluc_abecedne)
        self.volne_pozicie = list(range(1, len(self.poradie_kandidatov) + 1))
        self.priradene = {}
        self.aktualny_index = 0
        self._zamkni_ovladanie(True)

        self.txt_vysledok.config(state="normal")
        self.txt_vysledok.delete("1.0", "end")
        self.txt_vysledok.insert("end", "Priebeh žrebovania:\n")
        self.txt_vysledok.config(state="disabled")

        self._priprav_kandidata()

    def _priprav_kandidata(self):
        self.faza = "cakam_start"
        k = self.poradie_kandidatov[self.aktualny_index]
        self.lbl_cislo.config(text="?")
        self.l_vyzva.config(
            text=f"Na rade je: {k.cele_meno()}  —  stlačte ENTER alebo medzerník pre spustenie.",
            foreground="#b30000",
        )
        self.b_generuj.config(
            text=f"{k.cele_meno()}: stlačte ENTER / medzerník pre SPUSTENIE losovania"
        )

    def _stlac(self):
        if not self.volba_aktivna:
            return
        if self.faza == "cakam_start":
            self._spusti_losovanie()
        elif self.faza == "generujem":
            self._zastav_losovanie()

    def _spusti_losovanie(self):
        self.faza = "generujem"
        self.l_vyzva.config(
            text="Prebieha losovanie…  opätovným stlačením ENTER / medzerníka ho zastavíte.",
            foreground="#b30000",
        )
        self.b_generuj.config(text="Stlačte ENTER / medzerník pre ZASTAVENIE losovania")
        self._los_tik()

    def _los_tik(self):
        if self.faza != "generujem":
            return
        self.lbl_cislo.config(text=str(random.choice(self.volne_pozicie)))
        self._job = self.after(self.INTERVAL_MS, self._los_tik)

    def _zastav_losovanie(self):
        self.faza = None
        if self._job is not None:
            self.after_cancel(self._job)
            self._job = None

        pozicia = random.choice(self.volne_pozicie)
        self.volne_pozicie.remove(pozicia)
        self.priradene[self.aktualny_index] = pozicia
        k = self.poradie_kandidatov[self.aktualny_index]

        self.lbl_cislo.config(text=str(pozicia))
        self.txt_vysledok.config(state="normal")
        self.txt_vysledok.insert("end", f"  {k.cele_meno()}  →  poradové číslo {pozicia}\n")
        self.txt_vysledok.see("end")
        self.txt_vysledok.config(state="disabled")

        self.aktualny_index += 1
        if self.aktualny_index < len(self.poradie_kandidatov):
            self.l_vyzva.config(
                text=f"{k.cele_meno()} má číslo {pozicia}. Pripravte ďalšieho kandidáta…",
                foreground="#0a4",
            )
            self.b_generuj.config(text="Pripravujem ďalšieho kandidáta…")
            self.after(1200, self._priprav_kandidata)
        else:
            self.after(900, self._dokonci_volbu)

    def _dokonci_volbu(self):
        self.volba_aktivna = False
        self.faza = None
        self._zamkni_ovladanie(False)
        self.b_generuj.config(text="Spustiť voľbu poradia")
        self.lbl_cislo.config(text="–")
        self.l_vyzva.config(
            text="Voľba poradia ukončená. Výsledné poradie vystúpenia je zobrazené nižšie.",
            foreground="#0a4",
        )
        self._zobraz_finalne()

    def _zobraz_finalne(self):
        mapovanie = {
            poz: self.poradie_kandidatov[idx] for idx, poz in self.priradene.items()
        }
        self.txt_vysledok.config(state="normal")
        self.txt_vysledok.delete("1.0", "end")
        self.txt_vysledok.insert("end", "VÝSLEDNÉ PORADIE VYSTÚPENIA:\n\n")
        for poz in range(1, len(self.poradie_kandidatov) + 1):
            k = mapovanie.get(poz)
            if k is not None:
                self.txt_vysledok.insert("end", f"{poz}. {k.cele_meno()}\n")
        self.txt_vysledok.config(state="disabled")

    def _zamkni_ovladanie(self, zamknut: bool):
        stav = "disabled" if zamknut else "normal"
        for w in (
            self.e_tituly_pred,
            self.e_meno,
            self.e_priezvisko,
            self.e_tituly_za,
            self.b_pridaj,
            self.b_odstran,
            self.b_vymaz,
            self.b_uloz,
            self.b_nacitaj,
        ):
            w.config(state=stav)

    # ------------------------------------------------------- aktualizácia
    def _zisti_vzdialenu_verziu(self) -> str:
        req = urllib.request.Request(VERSION_URL, headers={"Cache-Control": "no-cache"})
        with urllib.request.urlopen(req, timeout=6, context=ssl_kontext()) as r:
            return r.read().decode("utf-8").strip()

    def _skontroluj_aktualizacie(self):
        def worker():
            try:
                vzdialena = self._zisti_vzdialenu_verziu()
                if vzdialena and verzia_na_n_ticu(vzdialena) > verzia_na_n_ticu(APP_VERSION):
                    self.after(0, lambda: self._ponukni_aktualizaciu(vzdialena))
            except Exception:
                pass  # bez internetu jednoducho pokračujeme

        threading.Thread(target=worker, daemon=True).start()

    def aktualizuj_rucne(self):
        """Manuálna aktualizácia po stlačení tlačidla „Aktualizovať program"."""
        self.b_aktualizovat.config(state="disabled")
        self.l_vyzva.config(text="Kontrolujem dostupnosť aktualizácie...", foreground="#b30000")

        def worker():
            try:
                vzdialena = self._zisti_vzdialenu_verziu()
            except Exception:
                vzdialena = None
            self.after(0, lambda: self._po_rucnej_kontrole(vzdialena))

        threading.Thread(target=worker, daemon=True).start()

    def _po_rucnej_kontrole(self, vzdialena):
        self.b_aktualizovat.config(state="normal")
        self.l_vyzva.config(
            text="Vážení kandidáti, prosím pristúpte v abecednom poradí podľa priezviska.",
            foreground="#0a4",
        )
        if not vzdialena:
            messagebox.showerror(
                "Aktualizácia",
                "Nepodarilo sa overiť aktualizáciu.\n"
                "Skontrolujte pripojenie na internet a skúste znova.",
            )
            return
        if verzia_na_n_ticu(vzdialena) > verzia_na_n_ticu(APP_VERSION):
            if messagebox.askyesno(
                "Dostupná aktualizácia",
                f"Je dostupná novšia verzia {vzdialena} (máte {APP_VERSION}).\n\n"
                "Stiahnuť a nainštalovať teraz?",
            ):
                self._stiahni_a_instaluj()
        else:
            if messagebox.askyesno(
                "Aktuálna verzia",
                f"Máte najnovšiu verziu ({APP_VERSION}).\n\n"
                "Chcete aj tak znova prevziať a nainštalovať najnovšiu verziu?",
            ):
                self._stiahni_a_instaluj()

    def _ponukni_aktualizaciu(self, vzdialena: str):
        if messagebox.askyesno(
            "Dostupná aktualizácia",
            f"Je dostupná novšia verzia {vzdialena} (máte {APP_VERSION}).\n\n"
            "Chcete ju teraz stiahnuť a nainštalovať?",
        ):
            self._stiahni_a_instaluj()

    def _stiahni_a_instaluj(self):
        self.l_vyzva.config(text="Sťahujem aktualizáciu, čakajte prosím...", foreground="#b30000")

        def worker():
            try:
                ciel = os.path.join(tempfile.gettempdir(), "VolbaPoradiaDekana_Setup.exe")
                with urllib.request.urlopen(
                    INSTALLER_URL, timeout=120, context=ssl_kontext()
                ) as resp, open(ciel, "wb") as f:
                    shutil.copyfileobj(resp, f)
                self.after(0, lambda: self._spusti_instalator(ciel))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror(
                    "Chyba aktualizácie",
                    f"Aktualizáciu sa nepodarilo stiahnuť:\n{e}",
                ))

        threading.Thread(target=worker, daemon=True).start()

    def _spusti_instalator(self, cesta: str):
        try:
            self._uloz_auto()
            subprocess.Popen([cesta])
            self.destroy()
        except OSError as e:
            messagebox.showerror("Chyba", f"Inštalátor sa nepodarilo spustiť:\n{e}")


def main():
    app = Aplikacia()
    app.mainloop()


if __name__ == "__main__":
    main()
