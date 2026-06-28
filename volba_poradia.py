# -*- coding: utf-8 -*-
"""
Voľba poradia vystúpenia kandidátov na dekana.

Program umožňuje:
  - zadať kandidátov na dekana (meno, priezvisko, titul/y),
  - vyzve kandidátov, aby v abecednom poradí pristúpili,
  - po stlačení tlačidla sa spustí generovanie (náhodné losovanie poradia),
  - po opätovnom stlačení sa generovanie ukončí a zobrazí sa výsledné poradie.

Podmienka: kandidáti musia byť minimálne dvaja.
"""

import random
import tkinter as tk
from tkinter import messagebox, ttk


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


class Aplikacia(tk.Tk):
    INTERVAL_MS = 80  # rýchlosť premiešavania počas generovania

    def __init__(self):
        super().__init__()
        self.title("Voľba poradia vystúpenia kandidátov na dekana")
        self.geometry("780x620")
        self.minsize(680, 560)

        self.kandidati: list[Kandidat] = []
        self.generuje_sa = False
        self._job = None
        self.vysledne_poradie: list[Kandidat] = []

        self._vytvor_styl()
        self._vytvor_widgety()

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

    def vymaz_vsetkych(self):
        if self.generuje_sa:
            return
        if not self.kandidati:
            return
        if messagebox.askyesno("Vymazať", "Naozaj vymazať všetkých kandidátov?"):
            self.kandidati.clear()
            self._obnov_zoznam()

    def _obnov_zoznam(self):
        self.lb_kandidati.delete(0, "end")
        for k in sorted(self.kandidati, key=Kandidat.kluc_abecedne):
            self.lb_kandidati.insert("end", k.cele_meno())

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


def main():
    app = Aplikacia()
    app.mainloop()


if __name__ == "__main__":
    main()
