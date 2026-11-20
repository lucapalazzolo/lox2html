# Comandi rapidi

HTML universale (computer, Android, iPhone, iPad) — consigliato:

```bash
bash CONVERTI_UNIVERSALE.command "/percorso/sistema.lox" --site-name "Sistema carsico"
bash CONVERTI_CARTELLA_UNIVERSALE.command "/percorso/lox" --recursive -o "$HOME/Downloads/html"
```

Installazione (macOS / Linux):

```bash
cd ~/Downloads
unzip -q LOX2HTML_UNIVERSALE_v2_1_COMPLETO.zip
cd LOX2HTML_UNIVERSALE_v2_1
bash INSTALLA.command
```

Conversione mobile neutra (qualsiasi LOX):

```bash
bash CONVERTI_MOBILE.command "/percorso/sistema.lox" \
  --site-name "Sistema carsico" \
  -o output/sistema_mobile.html
```

Conversione desktop invariata:

```bash
bash CONVERTI_LOX.command "/percorso/sistema.lox" \
  -o output/sistema_desktop.html
```

Categorie facoltative:

```bash
bash CONVERTI_MOBILE.command "/percorso/sistema.lox" \
  --mine "*miniera*" --cave "*grotta*" \
  -o output/sistema_mobile.html
```

Avvio leggero su dispositivi meno potenti:

```bash
bash CONVERTI_MOBILE.command "/percorso/sistema.lox" \
  --start-mode light
```

Conversione mobile batch:

```bash
bash CONVERTI_CARTELLA_MOBILE.command "/percorso/lox" \
  --recursive -o "$HOME/Downloads/html_mobile"
```

Verifica:

```bash
bash VERIFICA.command
```

Apri l'HTML sul Mac:

```bash
open output/sistema_mobile.html
```

Per tutte le opzioni: `python3 convert_lox_mobile.py --help`. Documentazione: `README_MOBILE.md`.

Zoom iPhone: tasti + e − sempre visibili; anche pinch a due dita.

Joystick v2.2: trascina il disco in basso a sinistra per spostare la scena senza ruotarla.
