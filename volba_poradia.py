# -*- coding: utf-8 -*-
"""
Voľba poradia vystúpenia kandidátov na dekana.

Program umožňuje:
  - zadať kandidátov na dekana (meno, priezvisko, titul/y),
  - uložiť a znova načítať zoznam kandidátov (a znova vygenerovať poradie),
  - vyzve kandidátov, aby v abecednom poradí pristúpili,
  - po stlačení tlačidla sa spustí generovanie (náhodné losovanie poradia),
  - po opätovnom stlačení sa generovanie ukončí a zobrazí sa výsledné poradie,
  - pri spustení skontroluje, či je dostupná novšia verzia, a ponúkne aktualizáciu.

Podmienka: kandidáti musia byť minimálne dvaja.
"""

import json
import os
import random
import subprocess
import sys
import tempfile
import threading
import urllib.request
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

APP_VERSION = "1.1.0"

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
    def __init__(self, meno: str, priezvisko: str, tituly: str = ""):
        self.meno = meno.strip()
        self.priezvisko = priezvisko.strip()
        self.tituly = tituly.strip()

    def cele_meno(self) -> str:
        casti = []
        if self.tituly:
            casti.append(self.tituly)
        casti.append(self.meno)
        casti.append(self.priezvisko)
        return " ".join(casti)

    def kluc_abecedne(self):
        # Abecedné poradie podľa priezviska, potom mena
        return (self.priezvisko.lower(), self.meno.lower())

    def to_dict(self) -> dict:
        return {"meno": self.meno, "priezvisko": self.priezvisko, "tituly": self.tituly}

    @staticmethod
    def from_dict(d: dict) -> "Kandidat":
        return Kandidat(d.get("meno", ""), d.get("priezvisko", ""), d.get("tituly", ""))


class Aplikacia(tk.Tk):
    INTERVAL_MS = 80  # rýchlosť premiešavania počas generovania

    def __init__(self):
        super().__init__()
        self.title(f"Voľba poradia vystúpenia kandidátov na dekana  (v{APP_VERSION})")
        self.geometry("820x680")
        self.minsize(700, 600)

        try:
            self.iconbitmap(resource_path("app.ico"))
        except Exception:
            pass

        self.kandidati: list[Kandidat] = []
        self.generuje_sa = False
        self._job = None
        self.vysledne_poradie: list[Kandidat] = []

        self._vytvor_styl()
        self._vytvor_widgety()

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

    def _vytvor_widgety(self):
        hlavny = ttk.Frame(self, padding=12)
        hlavny.pack(fill="both", expand=True)

        ttk.Label(
            hlavny,
            text="Voľba poradia vystúpenia kandidátov na dekana",
            style="Nadpis.TLabel",
        ).pack(anchor="w")

        # --- Formulár na zadanie kandidáta ---
        formular = ttk.LabelFrame(hlavny, text="Zadanie kandidáta", padding=10)
        formular.pack(fill="x", pady=(12, 8))

        ttk.Label(formular, text="Titul(y):").grid(row=0, column=0, sticky="w", padx=4, pady=4)
        self.e_tituly = ttk.Entry(formular, width=18)
        self.e_tituly.grid(row=0, column=1, sticky="we", padx=4, pady=4)

        ttk.Label(formular, text="Meno:").grid(row=0, column=2, sticky="w", padx=4, pady=4)
        self.e_meno = ttk.Entry(formular, width=18)
        self.e_meno.grid(row=0, column=3, sticky="we", padx=4, pady=4)

        ttk.Label(formular, text="Priezvisko:").grid(row=0, column=4, sticky="w", padx=4, pady=4)
        self.e_priezvisko = ttk.Entry(formular, width=18)
        self.e_priezvisko.grid(row=0, column=5, sticky="we", padx=4, pady=4)

        ttk.Button(formular, text="Pridať kandidáta", command=self.pridaj_kandidata).grid(
            row=0, column=6, padx=8, pady=4
        )
        formular.columnconfigure(1, weight=1)
        formular.columnconfigure(3, weight=1)
        formular.columnconfigure(5, weight=1)

        self.e_meno.bind("<Return>", lambda _e: self.pridaj_kandidata())
        self.e_priezvisko.bind("<Return>", lambda _e: self.pridaj_kandidata())
        self.e_tituly.bind("<Return>", lambda _e: self.pridaj_kandidata())

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
        ttk.Button(ovladanie, text="Odstrániť vybraného", command=self.odstran_kandidata).pack(
            fill="x", pady=2
        )
        ttk.Button(ovladanie, text="Vymazať všetkých", command=self.vymaz_vsetkych).pack(
            fill="x", pady=2
        )
        ttk.Separator(ovladanie, orient="horizontal").pack(fill="x", pady=6)
        ttk.Button(ovladanie, text="Uložiť kandidátov…", command=self.uloz_kandidatov).pack(
            fill="x", pady=2
        )
        ttk.Button(ovladanie, text="Načítať kandidátov…", command=self.nacitaj_kandidatov).pack(
            fill="x", pady=2
        )

        # --- Výzva ---
        self.l_vyzva = ttk.Label(
            hlavny,
            text="Vážení kandidáti, prosím pristúpte v abecednom poradí podľa priezviska.",
            style="Podnadpis.TLabel",
            foreground="#0a4",
        )
        self.l_vyzva.pack(anchor="w", pady=(4, 6))

        # --- Tlačidlo generovania ---
        self.b_generuj = ttk.Button(
            hlavny,
            text="Spustiť generovanie poradia",
            style="Velke.TButton",
            command=self.prepni_generovanie,
        )
        self.b_generuj.pack(fill="x", pady=6)

        # --- Výsledok ---
        vysledok_ramec = ttk.LabelFrame(hlavny, text="Poradie vystúpenia", padding=10)
        vysledok_ramec.pack(fill="both", expand=True, pady=(6, 0))
        self.txt_vysledok = tk.Text(
            vysledok_ramec, height=8, font=("Segoe UI", 12), state="disabled", wrap="word"
        )
        self.txt_vysledok.pack(fill="both", expand=True)

        self._obnov_zoznam()

    # -------------------------------------------------------------- logika
    def pridaj_kandidata(self):
        if self.generuje_sa:
            return
        meno = self.e_meno.get().strip()
        priezvisko = self.e_priezvisko.get().strip()
        tituly = self.e_tituly.get().strip()

        if not meno or not priezvisko:
            messagebox.showwarning(
                "Neúplné údaje", "Zadajte aspoň meno a priezvisko kandidáta."
            )
            return

        self.kandidati.append(Kandidat(meno, priezvisko, tituly))
        self.e_tituly.delete(0, "end")
        self.e_meno.delete(0, "end")
        self.e_priezvisko.delete(0, "end")
        self.e_tituly.focus_set()
        self._obnov_zoznam()
        self._uloz_auto()

    def odstran_kandidata(self):
        if self.generuje_sa:
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
        if self.generuje_sa:
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
        if self.generuje_sa:
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
            "Načítané", f"Načítaných {len(self.kandidati)} kandidátov. Môžete znova vygenerovať poradie."
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

    # ------------------------------------------------------- generovanie
    def prepni_generovanie(self):
        if not self.generuje_sa:
            self._spusti_generovanie()
        else:
            self._zastav_generovanie()

    def _spusti_generovanie(self):
        if len(self.kandidati) < 2:
            messagebox.showwarning(
                "Málo kandidátov",
                "Kandidáti musia byť minimálne dvaja. Pridajte ešte aspoň jedného.",
            )
            return

        self.generuje_sa = True
        self.b_generuj.config(text="Zastaviť generovanie")
        self.l_vyzva.config(
            text="Prebieha generovanie poradia... Opätovným stlačením tlačidla ho ukončíte.",
            foreground="#b30000",
        )
        self._tik()

    def _tik(self):
        if not self.generuje_sa:
            return
        poradie = self.kandidati[:]
        random.shuffle(poradie)
        self._zobraz_poradie(poradie, finalne=False)
        self._job = self.after(self.INTERVAL_MS, self._tik)

    def _zastav_generovanie(self):
        self.generuje_sa = False
        if self._job is not None:
            self.after_cancel(self._job)
            self._job = None
        self.b_generuj.config(text="Spustiť generovanie poradia")

        self.vysledne_poradie = self.kandidati[:]
        random.shuffle(self.vysledne_poradie)
        self._zobraz_poradie(self.vysledne_poradie, finalne=True)
        self.l_vyzva.config(
            text="Generovanie ukončené. Výsledné poradie vystúpenia je zobrazené nižšie.",
            foreground="#0a4",
        )

    def _zobraz_poradie(self, poradie, finalne: bool):
        self.txt_vysledok.config(state="normal")
        self.txt_vysledok.delete("1.0", "end")
        if finalne:
            self.txt_vysledok.insert("end", "VÝSLEDNÉ PORADIE VYSTÚPENIA:\n\n")
        for i, k in enumerate(poradie, start=1):
            self.txt_vysledok.insert("end", f"{i}. {k.cele_meno()}\n")
        self.txt_vysledok.config(state="disabled")

    # ------------------------------------------------------- aktualizácia
    def _skontroluj_aktualizacie(self):
        def worker():
            try:
                req = urllib.request.Request(
                    VERSION_URL, headers={"Cache-Control": "no-cache"}
                )
                with urllib.request.urlopen(req, timeout=6) as r:
                    vzdialena = r.read().decode("utf-8").strip()
                if vzdialena and verzia_na_n_ticu(vzdialena) > verzia_na_n_ticu(APP_VERSION):
                    self.after(0, lambda: self._ponukni_aktualizaciu(vzdialena))
            except Exception:
                pass  # bez internetu jednoducho pokračujeme

        threading.Thread(target=worker, daemon=True).start()

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
                urllib.request.urlretrieve(INSTALLER_URL, ciel)
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
