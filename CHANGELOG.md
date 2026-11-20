# v3.0 — HTML universale per ogni dispositivo (20 novembre 2026)

- Nuovo `convert_lox_universal.py` (+ `batch_convert_universal.py`, `CONVERTI_UNIVERSALE.command`, `CONVERTI_CARTELLA_UNIVERSALE.command`): un unico HTML che funziona su computer, Android, iPhone e iPad.
- Nuovo `universal_viewer_template.html`: layout adattivo (pannello laterale su schermi grandi, pannelli a scomparsa su telefono, barra laterale in orizzontale), comandi adattati a mouse, trackpad, tastiera e touch; aree sicure di iPhone; avviso se WebGL manca; esportazione PNG; viste pianta e sezioni E–O/N–S; proiezione ortogonale.
- Zoom e spostamento coerenti con Plotly: lo zoom scala la distanza attorno al centro inquadrato, lo spostamento (joystick, due dita, frecce) trasla insieme occhio e centro, senza ruotare la vista. Si usa la camera effettiva della scena, non quella memorizzata nel layout, evitando salti dopo rotella o pizzico.
- Mesh impacchettate per rilievo: stessi vertici e triangoli, ma un solo oggetto WebGL per gruppo (es. 32.238 mesh → 3), indispensabile per i sistemi grandi su telefono.
- Raggruppamento `auto` migliorato (anche per i convertitori 2.x): ignora i rami vuoti, segue le catene di un solo ramo nei progetti Therion gerarchici, mostra il nome del survey quando il titolo è ereditato dal padre. Risultati su Dossena invariati.
- `--surface-index` fuori intervallo produce un messaggio chiaro invece di un errore interno.
- Nuovi test: `tests/test_universal_converter.py`, `tests/check_universal_viewer.cjs`, test browser facoltativo `tests/browser_check.cjs`. `VERIFICA.command` esegue l'intera suite.
- I convertitori desktop e mobile 2.x restano disponibili e invariati nel formato di uscita.

# v2.2 — joystick mobile (19 novembre 2026)

- Aggiunto joystick touch per traslazione rigida della camera in direzioni dello schermo.
- Nessuna modifica a lettore LOX, geometria, isoipse o convertitore desktop.
- Pointer Events con fallback Touch Events; stop immediato al rilascio e in background.
- Limitazione degli aggiornamenti Plotly a circa 22 Hz per evitare accumulo di render.
- Supporto tastiera con frecce, viewport orizzontale e test matematici dedicati.
- Consegna sempre cartella completa con HTML mobile rigenerato.

# LOX2HTML UNIVERSALE 2.1 — iPhone/mobile zoom

- Aggiunti comandi permanenti + e − (minimo 56 px) in `mobile_viewer_template.html`, indipendenti dalla gestione nativa del pinch Plotly.
- Gestione opzionale pinch a due dita tramite eventi Touch e zoom della camera 3D; mantiene rotazione, orientamento e selezione.
- Limiti alla distanza della camera per evitare clipping e scene inutilizzabili.
- Aggiornate istruzioni e test JS eseguibili sulle trasformazioni della camera.
- Nessuna modifica a parser LOX, conversione desktop, dati XYZ, classificazione facoltativa, isolamenti e formati di output.
- ZIP completo standalone; nessuna patch da applicare.

---

# LOX2HTML UNIVERSALE 2.0 — Mobile viewer

- Aggiunti `convert_lox_mobile.py`, `batch_convert_mobile.py` e `mobile_viewer_template.html` come percorso parallelo, senza modificare lettore, conversione e template desktop.
- Interfaccia touch con dock a quattro pulsanti, pannelli a comparsa, ricerca dei survey, selezione e isolamento, orientamento 3D/pianta/sezione e curve di livello configurabili.
- Categorie `all` per default. Possibili classificazioni esplicite `--type cave|mine`, `--mine` e `--cave`, senza inferenze automatiche dal nome nel viewer mobile.
- Opzioni di avvio `balanced|light|detailed` per scegliere i livelli inizialmente visibili: geometria completa sempre inclusa.
- Test del convertitore mobile, test JS statico e verifica browser di pannelli/controlli su viewport smartphone.
- `.gitignore` e documentazione per uso standalone/GitHub.

---

# LOX2HTML UNIVERSALE 1.0

Original source: DOSSENA_HTML_PORTABILE generator and viewer.

## Changes (additive generalization)

- Replaced fixed Dossena page branding with user-selectable area name.
- Replaced hardcoded EPSG:32632 and absolute-elevation assumptions with explicit descriptive labels; no data transformation.
- Survey grouping now works without Dossena-specific GR/MN survey IDs and preserves unmapped geometry. Supports `auto`, `top`, `survey`.
- Removed catalog markers from cave group counts; kept the entrance points.
- Preserved full LOX shot and mesh topology; no automatic dropping of any shot or triangle.
- Handles LOX without terrain, with empty/NoData terrain, without meshes, with nested survey trees and with only root-level shots.
- Fixed scene extent to include both cave depth and terrain elevation rather than clipping underground geometry to the terrain height range.
- Added batch conversion, SHA256 audit, standalone macOS/Linux commands and conversion tests.
- Kept the original vendored Plotly JS and interoperable LOX reader unchanged.

## Explicit limits

- Multiple LOX height surfaces: user selects one by index.
- 10/20/50 m contour controls assume base interval of 10 m.
- Standalone viewer needs browser WebGL; no online dependency.
- Existing mesh facets are not modified or decimated.
