# LOX2HTML Mobile — v2.1

> **Nota (v3.0):** per un HTML unico che funziona su computer, Android, iPhone e iPad usa il convertitore universale descritto nel [README](README.md) (`CONVERTI_UNIVERSALE.command`). Questa pagina documenta il convertitore mobile 2.x, mantenuto per compatibilità.

Convertitore 3D per telefoni e tablet. Usa lo stesso lettore LOX della versione desktop, ma produce un HTML con interfaccia touch. Le versioni desktop e mobile sono indipendenti: nessuno script desktop è stato sostituito.

## Installazione macOS / Linux

Da Terminale, dopo aver decompresso lo ZIP:

```bash
cd ~/Downloads/LOX2HTML_UNIVERSALE_v2_1
bash INSTALLA.command
```

Richiede Python >=3.10, NumPy e scikit-image. Il comando crea `.venv` nella cartella. Un output HTML già generato si apre semplicemente nel browser, senza Python.

## Converti un LOX qualsiasi — categorie neutre

```bash
bash CONVERTI_MOBILE.command "/percorso/al/rilievo.lox" \
  --site-name "Nome del sistema" \
  -o output/rilievo_mobile.html
```

Apri il risultato sul Mac:

```bash
open output/rilievo_mobile.html
```

Su iPhone e Android trasferisci **solo** `rilievo_mobile.html` (AirDrop, File, cloud, email). Aprilo con un browser che supporti WebGL; alcuni visualizzatori di anteprima integrati nelle app non supportano WebGL e potrebbero richiedere «Apri nel browser».

Per impostazione predefinita **tutti i rilievi sono neutri (`all`)**: nessun riconoscimento di grotte/miniere, nessuna legenda per categorie. I rilievi vengono visualizzati con un colore unico.

## Categorie opzionali

Per dichiarare che l'intero LOX contiene grotte oppure miniere:

```bash
bash CONVERTI_MOBILE.command "rilievo.lox" --type cave
bash CONVERTI_MOBILE.command "miniera.lox" --type mine
```

Per un LOX misto, usa una o più regole sui nomi o codici dei survey:

```bash
bash CONVERTI_MOBILE.command "sistema.lox" \
  --mine "*miniera*" \
  --mine "*galleria*" \
  --cave "*abisso*" \
  -o output/sistema_mobile.html
```

Le corrispondenze sono case-insensitive; `*` e `?` attivano pattern glob, mentre un testo semplice cerca una sottostringa. Una regola non trovata o che assegna simultaneamente due categorie allo stesso survey interrompe la conversione, indicando il nome in conflitto. I rilievi non corrispondenti rimangono `all`.

Si può combinare un valore globale con delle eccezioni: `--type cave --mine '*galleria*'`.

### Prestazioni / avvio

```bash
# Viene mostrata subito la rete di poligonali; volumi attivabili dal pannello Livelli
bash CONVERTI_MOBILE.command rilievo.lox --start-mode light

# Volumi visibili e isoipse a 10 m
bash CONVERTI_MOBILE.command rilievo.lox --start-mode detailed
```

`balanced` (default): volumi e poligonali visibili, isoipse a 20 m. `light`: volumi nascosti all'apertura, isoipse a 50 m. `detailed`: volumi visibili, isoipse a 10 m. **Anche in modalità light le mesh restano integralmente nel file HTML** e possono essere attivate in seguito. Non c'è semplificazione dei triangoli né perdita delle tratte.

## Converti una cartella

```bash
bash CONVERTI_CARTELLA_MOBILE.command "/percorso/LOX" \
  --recursive \
  --start-mode light \
  -o "/percorso/HTML_mobile"
```

La struttura delle sottocartelle è conservata. Sono generati report JSON per ogni LOX e un report batch complessivo.

## Comandi del visualizzatore

- **Esplora**: ricerca rapida, selezione e inquadramento del rilievo.
- **Livelli**: volumi, poligonali, ingressi, curve di livello 10/20/50 m, opacità e (se definite) categorie.
- **Vista**: orientamento 3D/pianta/sezione e scala verticale 1×/2×/3×.
- **Reset**: inquadra il sistema e annulla l'isolamento.
- Tocco su un rilievo: informazioni e comando **Isola**.

La vista rispetta safe area e orientamento dello schermo. Sui browser WebGL, trascina con un dito per ruotare; lo zoom funziona anche dai pulsanti + e −; il pinch a due dita dispone di un handler esplicito.

## Zoom e navigazione su iPhone (v2.1)

- Premi il pulsante **+** sul lato destro per avvicinare la camera 3D; **−** per allontanarla.
- Due dita: il pinch agisce sulla distanza della camera tramite un handler dedicato, senza fare affidamento sulla configurazione `scrollZoom` di Plotly.
- Un dito: ruota la scena. **Reset** torna alla vista iniziale, mentre **Esplora** inquadra un singolo survey.
- `1×`, `2×`, `3×` modificano soltanto l'esagerazione verticale, **non** lo zoom.
- L'apertura in Safari e Chrome su iOS può avere limitazioni della piattaforma WebKit: i tasti +/− sono indipendenti dai gesti nativi. Apri l'HTML in una scheda del browser (non in una preview inline di File/WhatsApp).

## Input particolari

- `--no-contours`: non usa il DTM incorporato nel LOX; elimina anche il relativo livello dall'interfaccia.
- `--surface-index 1`: utilizza la seconda superficie del file.
- `--group-mode auto|top|survey`: regola la suddivisione dei rilievi secondo la gerarchia LOX. Non determina le categorie.
- `--crs EPSG:32632`: etichetta descrittiva, nessuna trasformazione delle coordinate.
- `--min-contour-length 25`: soglia minima in metri per le isoipse.
- `--coordinate-decimals 3`: arrotondamento delle coordinate di visualizzazione, non del file LOX originale.

Non serve che il LOX contenga DTM, ortofoto o volumi: quando mancano, il visualizzatore mostra gli elementi disponibili. Il sistema non scarica raster né inventa geometrie assenti.

## Test

```bash
bash VERIFICA_MOBILE.command
```

Verifica tutte le 8 prove desktop e le 6 prove mobile, con test JS aggiuntivi se Node.js è presente. Lo script mobile è stato verificato in Chromium su viewport 390×844 per i controlli UI; in tale ambiente di test WebGL era disabilitato, quindi il rendering GPU reale deve essere verificato su telefono.

## Pubblicazione su GitHub

- Carica sorgenti Python, `mobile_viewer_template.html`, `lox_io.py`, `requirements.txt`, `.command`, `vendor/` e la documentazione.
- `.gitignore` esclude `.venv`, cache e `output/`.
- Le librerie vendorizzate conservano l'attribuzione in `vendor/README_LICENSE.md`. Se pubblichi il progetto, scegli la licenza del **tuo codice** prima di distribuirlo.
- Il LOX reale e gli HTML di esempio sono inclusi nella distribuzione completa per facilitare i test; puoi ometterli da un repository pubblico per ridurre le dimensioni e non distribuire rilievi georeferenziati.

### Joystick per traslazione (v2.2)

Sul telefono, trascina il joystick circolare in basso a sinistra: il modello si muove
rigidamente nel piano dello schermo (destra/sinistra/alto/basso), senza
modificare le coordinate LOX, la rotazione o lo zoom. La velocita dipende
dall'inclinazione della leva e dalla distanza della camera. Il movimento
termina quando rilasci il dito, cambi applicazione o la scheda va in background.

Il joystick usa Pointer Events su iOS recente; include fallback Touch Events per
WebKit meno recenti. I pulsanti + e - continuano a funzionare separatamente.
Da tastiera, metti a fuoco il joystick e usa le quattro frecce.

Per rigenerare gli esempi:

```bash
bash CONVERTI_MOBILE.command esempi/DOSSENA_sorgente.lox --site-name Dossena \
  --crs EPSG:32632 -o esempi/DOSSENA_MOBILE.html
bash VERIFICA_MOBILE.command
```
