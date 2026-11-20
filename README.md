# LOX2HTML 3.0 — visualizzatore 3D universale per rilievi Therion

Converte un modello Therion/Loch `.lox` in **un unico file HTML** che si apre offline su qualunque dispositivo: computer (Windows, macOS, Linux), Android, iPhone e iPad. Il file contiene già tutto (motore grafico Plotly, geometrie, interfaccia): basta aprirlo con un browser, senza installare nulla e senza connessione.

La conversione **non modifica la geometria del LOX**: tratte, stazioni e triangoli originali delle mesh sono conservati; nessuna riproiezione, scala, lisciatura o ritriangolazione. Se il LOX contiene una superficie altimetrica, vengono estratte curve di livello vettoriali 3D (10/20/50 m). Ortofoto e raster non vengono incorporati.

## Un solo HTML per tutti i dispositivi

L'interfaccia si adatta automaticamente allo schermo e al tipo di input:

| Dispositivo | Disposizione | Comandi |
|---|---|---|
| Computer, portatile, iPad orizzontale | pannello laterale fisso (Esplora, Livelli, Vista, Info) | mouse: trascina ruota, tasto destro sposta, rotella zoom · tastiera: `+` `−`, frecce, `1`–`4` viste, `R` inquadra, `F` schermo intero, `/` cerca |
| Telefono verticale, iPad verticale | barra in basso e pannelli a scomparsa | un dito ruota, due dita zoom e spostamento, joystick, pulsanti `+` `−` |
| Telefono orizzontale | barra laterale compatta | come sopra, con controlli più piccoli |

Inoltre: rispetto di notch e aree sicure di iPhone, ricerca ed elenco dei rilievi con visibilità per singolo rilievo, isolamento, viste pianta e sezioni E–O / N–S, proiezione ortogonale, esagerazione verticale, esportazione PNG, schermo intero dove il browser lo consente, avviso chiaro se WebGL non è disponibile. Con modelli molto grandi su dispositivi con poca memoria i volumi vengono nascosti all'avvio (riattivabili da *Livelli*), senza eliminare alcun triangolo.

Le mesh dei LOX prodotti da Therion sono spesso divise in decine di migliaia di pezzi: LOX2HTML le raggruppa in un oggetto grafico per rilievo (stessi vertici e triangoli, solo impacchettati), così anche un sistema con 37.000 tratte e 32.000 mesh resta fluido su telefono.

## Installazione (una volta)

Richiede Python 3.10+ con `pip`. Su macOS/Linux:

```bash
cd LOX2HTML
bash INSTALLA.command
```

Il comando crea un ambiente `.venv` locale, installa NumPy e scikit-image ed esegue i test. Su Windows:

```bat
py -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
```

Aprire l'HTML generato non richiede Python.

## Convertire

Un file:

```bash
bash CONVERTI_UNIVERSALE.command "/percorso/rilievo.lox" --site-name "Nome del sistema"
```

Risultato: `output/rilievo_3D.html`. Su Windows: `.venv\Scripts\python convert_lox_universal.py "C:\percorso\rilievo.lox"`.

Una cartella (sottocartelle con `--recursive`):

```bash
bash CONVERTI_CARTELLA_UNIVERSALE.command "/percorso/LOX" --recursive -o "/percorso/HTML"
```

Ogni LOX produce un `.html` e un `.qa.json` (conteggi e SHA-256 del sorgente); `BATCH_UNIVERSAL_REPORT.json` riassume successi ed errori.

### Opzioni principali

| Opzione | Effetto |
|---|---|
| `-o file.html` | percorso di uscita |
| `--site-name "Nome"` | titolo della pagina |
| `--crs EPSG:32632`, `--z-label "Quota (m)"` | solo etichette, nessuna trasformazione |
| `--start-mode auto\|balanced\|light\|detailed` | livelli visibili all'apertura; `auto` (predefinito) si adatta al dispositivo |
| `--group-mode auto\|top\|survey` | raggruppamento dei rilievi nell'elenco |
| `--type cave\|mine`, `--mine "*miniera*"`, `--cave "*abisso*"` | categorie facoltative (predefinito: neutro) |
| `--surface-index N`, `--no-contours`, `--min-contour-length M` | scelta della superficie e delle isoipse |
| `--origin X0 Y0`, `--coordinate-decimals N` | origine di disegno e arrotondamento delle coordinate visualizzate |

Elenco completo: `.venv/bin/python convert_lox_universal.py --help`.

Raggruppamento `auto`: usa i rami `grotte`/`miniere`/`caves`/`mines` se presenti; altrimenti segue la gerarchia del progetto Therion, ignora i rami vuoti e scende finché il sistema si divide in grotte distinte. Se un survey eredita il titolo dal padre, nell'elenco compare il suo nome (es. `Bueno_Fonteno` invece di dieci voci identiche).

## Aprire il file sui vari dispositivi

- **Computer**: doppio clic sul file, oppure trascinalo in Chrome, Edge, Firefox o Safari.
- **iPhone / iPad**: il modo affidabile è aprire il file da un **indirizzo web in Safari** (un sito o GitHub Pages, un server della rete locale, una cartella condivisa via web). Le anteprime rapide di File, Mail, WhatsApp e dei servizi cloud mostrano l'HTML senza eseguire JavaScript, quindi la scena 3D non parte: in quel caso la pagina stessa lo segnala dopo qualche secondo.
- **Android**: apri il file con Chrome (o Firefox/Edge), anche da locale; se il gestore file propone un'anteprima, scegli «Apri con» → Chrome.

Prova rapida dal computer verso telefono/tablet nella stessa rete Wi-Fi:

```bash
cd output && python3 -m http.server 8000
# poi sul telefono: http://<indirizzo-IP-del-computer>:8000/rilievo_3D.html
```

Serve un browser con WebGL (tutti i browser attuali). I modelli molto grandi producono HTML di decine di MB: su telefono conviene `--start-mode light`.

## Verifica

```bash
bash VERIFICA.command
```

Esegue il controllo di integrità, i test Python (conversione, raggruppamento, impacchettamento delle mesh senza perdita di vertici o triangoli, HTML autonomo) e, se Node.js è installato, i test del visualizzatore (sintassi compatibile con Safari meno recenti, comandi, matematica di zoom e spostamento). Il test facoltativo `tests/browser_check.cjs` apre gli HTML in Chromium con profili computer, Android, iPhone e iPad (richiede `playwright-core`).

## Contenuto

- `convert_lox_universal.py`, `batch_convert_universal.py`, `universal_viewer_template.html`: convertitore e visualizzatore universale (consigliati).
- `lox_io.py`: lettore LOX interoperabile (chunk Therion 1–6), senza dipendenze.
- `convert_lox_html.py` + `viewer_template.html` (desktop) e `convert_lox_mobile.py` + `mobile_viewer_template.html` (mobile): convertitori della versione 2.x, invariati per compatibilità; vedi [README_MOBILE.md](README_MOBILE.md).
- `vendor/plotly.min.js`: Plotly.js 3.3.1 (licenza MIT), incorporato in ogni HTML.
- `esempi/ESEMPIO_NO_DTM.lox`: piccolo LOX sintetico per prove.
- `tests/`: test automatici.

## Limiti

- Con più superfici nel LOX se ne usa una (`--surface-index`), mai fuse automaticamente.
- I comandi `--crs` e `--z-label` cambiano solo le etichette.
- Il file HTML non contiene raster, ortofoto o texture del LOX.
- Visualizzazione affidata a WebGL: su dispositivi molto datati o con poca memoria grafica i volumi 3D possono essere lenti; poligonali e isoipse restano utilizzabili.
