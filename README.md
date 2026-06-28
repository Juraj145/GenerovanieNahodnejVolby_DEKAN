# Generovanie náhodnej voľby – DEKAN

Program na náhodné určenie **poradia vystúpenia kandidátov na dekana**.

## Funkcie
- Zadávanie kandidátov: **titul(y) pred menom, meno, priezvisko, titul(y) za priezviskom** (tlačidlo „Pridať kandidáta"). Celé meno sa zobrazí v tvare `doc. Ing. Peter Novák, PhD.`.
- Zoznam sa automaticky zoraďuje **abecedne podľa priezviska** + výzva, aby kandidáti pristúpili v abecednom poradí.
- **Žrebovanie poradia po jednotlivých kandidátoch:** každý kandidát (v abecednom poradí) príde a stlačí **ENTER alebo medzerník** na spustenie losovania svojej pozície a opätovným stlačením **ENTER/medzerníka** losovanie zastaví — vylosuje sa mu poradové číslo. Takto sa vystrieda každý kandidát, kým nemajú všetci pridelené poradie.
- Podmienka: kandidáti musia byť **minimálne dvaja**.
- Možnosť odstrániť vybraného kandidáta alebo vymazať všetkých.
- **Uloženie a opätovné načítanie** zoznamu kandidátov + automatické zapamätanie medzi spusteniami.
- Tlačidlo **„Aktualizovať program"** a automatická kontrola novej verzie pri štarte.

## Spustenie zo zdrojového kódu
Potrebuješ Python 3.10+ s knižnicou Tkinter (štandardná súčasť inštalácie z [python.org](https://www.python.org/)).

```
python volba_poradia.py
```

## Zostavenie .exe (Windows)
Dvojklikom spusti `build.bat`, alebo ručne:

```
python -m pip install pyinstaller
python -m PyInstaller --noconfirm --onefile --windowed --name "VolbaPoradiaDekana" volba_poradia.py
```

Hotový súbor sa objaví v `dist\VolbaPoradiaDekana.exe`.

## Automatické zostavenie cez GitHub Actions
Pri každom pushnutí do vetvy `main` (alebo manuálnym spustením workflow „Build Windows EXE" v záložke **Actions**) sa `.exe` zostaví automaticky.
Hotový súbor stiahneš z danej akcie v sekcii **Artifacts** ako `VolbaPoradiaDekana`.
