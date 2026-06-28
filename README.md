# Generovanie náhodnej voľby – DEKAN

Program na náhodné určenie **poradia vystúpenia kandidátov na dekana**.

## Funkcie
- Zadávanie kandidátov: **titul(y), meno, priezvisko** (tlačidlo „Pridať kandidáta").
- Zoznam sa automaticky zoraďuje **abecedne podľa priezviska** + výzva, aby kandidáti pristúpili v abecednom poradí.
- Veľké tlačidlo: **1. stlačenie spustí** náhodné losovanie poradia (animácia), **2. stlačenie ho ukončí** a zobrazí finálne poradie vystúpenia.
- Podmienka: kandidáti musia byť **minimálne dvaja**.
- Možnosť odstrániť vybraného kandidáta alebo vymazať všetkých.

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
