# VIDEOSCRIPT-AI

**VideoScript AI Studio**

**Usi Windows e vuoi iniziare subito? Segui [INIZIA_QUI_WINDOWS.md](INIZIA_QUI_WINDOWS.md).**

Suite locale per visionare audiovisivi, aggiungere annotazioni sincronizzate, eseguire controlli qualità preliminari e trascrivere audio con un modello sul proprio computer. Frontend React/TypeScript, backend FastAPI, database SQLite, FFmpeg e faster-whisper opzionale.

GitHub conserva il codice del progetto. Per usare la suite devi scaricare il codice e avviare l'applicazione sul tuo computer: collegare un repository non installa automaticamente un programma. Questa versione è un'applicazione web locale; il pacchetto desktop per macOS/Windows è uno sviluppo successivo.

## 1. Prepara il computer

Servono:

- Python **3.11–3.13**; 3.12 è una scelta consigliata.
- Node.js **22.12 o successivo**, preferibilmente una versione LTS, con npm.
- [uv](https://docs.astral.sh/uv/getting-started/installation/) per installare le dipendenze Python dal lockfile.
- [FFmpeg e FFprobe](https://ffmpeg.org/download.html), entrambi disponibili nel `PATH`.
- Git, oppure il file ZIP scaricato dalla pagina GitHub del progetto.

L'installazione delle dipendenze e il download facoltativo dei modelli richiedono Internet. Lavorare su video, annotazioni, QC e trascrizioni locali non richiede API cloud.

**macOS con Homebrew:** se hai già installato Homebrew puoi eseguire `brew install python@3.12 node ffmpeg uv`. In alternativa usa gli installer ufficiali dei singoli strumenti. Chiudi e riapri il terminale dopo l'installazione.

**Windows:** usa gli installer ufficiali di [Python](https://www.python.org/downloads/windows/) e [Node.js LTS](https://nodejs.org/). Seleziona l'aggiunta al `PATH` nell'installer Python. Per FFmpeg scegli una build Windows indicata dalla pagina ufficiale FFmpeg, estraila e aggiungi la cartella `bin` al `PATH`; deve contenere anche `ffprobe.exe`. uv è disponibile con `winget install --id astral-sh.uv -e`. Riapri il terminale dopo avere modificato il `PATH`.

Verifica in un terminale:

```text
python --version
node --version
npm --version
uv --version
ffmpeg -version
ffprobe -version
```

Su macOS il comando Python può chiamarsi `python3`.

## 2. Scarica il progetto

Scarica lo ZIP dalla [repository GitHub](https://github.com/GIOX06/VIDEOSCRIPT-AI) con **Code → Download ZIP**, oppure clona il progetto:

```text
git clone https://github.com/GIOX06/VIDEOSCRIPT-AI.git
cd VIDEOSCRIPT-AI
```

Se hai scaricato lo ZIP, estrailo e apri il terminale nella cartella che contiene questo `README.md`. Se stai sviluppando in un ambiente Codex già preparato, usa il checkout esistente: ogni task cloud ha già un ambiente isolato e non serve creare un Git worktree.

## 3. Installa le dipendenze

**macOS**, dal terminale nella cartella del progetto:

```bash
bash scripts/setup-macos.command
```

**Windows**, dal Prompt dei comandi nella cartella del progetto:

```bat
scripts\setup-windows.bat
```

Gli script installano le dipendenze Python in `.venv`, incluse quelle per la trascrizione, e quelle frontend in `frontend/node_modules`. Non scaricano un modello AI e non installano automaticamente programmi di sistema.

Per installare solo player, progetti, annotazioni, QC, esportazioni e consultazione base, aggiungi `--base` allo script. Puoi abilitare le dipendenze AI in seguito con:

```text
uv sync --frozen --extra ai
```

Installazione equivalente manuale:

```text
uv sync --frozen --extra ai
npm --prefix frontend ci
```

## 4. Avvia la suite

**macOS:**

```bash
bash scripts/start-macos.command
```

**Windows:**

```bat
scripts\start-windows.bat
```

Si aprirà il browser sul servizio locale. Mantieni aperto il terminale; `Ctrl+C` arresta frontend e backend. Il launcher controlla le dipendenze, rileva le porte già occupate e verifica che entrambi i servizi rispondano prima di aprire il browser.

Puoi anche avviare il launcher direttamente con Python:

```text
python scripts/start.py
```

Il parametro `--no-browser` evita l'apertura automatica del browser; `--check` controlla prerequisiti e porte senza avviare nulla. Il backend ascolta su `127.0.0.1:8000` e il frontend su `127.0.0.1:5173`, esclusivamente sull'interfaccia locale.

## 5. Primo progetto

1. Crea un progetto e assegnagli un nome.
2. Importa un video MP4, MOV, MXF o WebM. L'importazione mediante percorso assoluto mantiene un riferimento al file esistente. La selezione mediante browser, se usata, crea una copia gestita dal backend locale: il browser non espone il percorso completo del file originale.
3. Controlla i metadati, il frame rate e il timecode iniziale. Imposta manualmente il TC se necessario.
4. Usa il player e aggiungi un'annotazione al fotogramma corrente. Le modifiche vengono salvate in SQLite.
5. Esegui il QC e apri gli intervalli segnalati per verificarli. Nero e silenzio sono rilievi da valutare: possono essere intenzionali.
6. Esporta il lavoro in TXT, CSV UTF-8 o JSON. SRT è disponibile per segmenti di trascrizione con inizio/fine.
7. Riapri il progetto dall'elenco per riprendere il lavoro. Se un originale è stato spostato, usa il ricollegamento al nuovo percorso.

Tutti i file scelti devono essere accessibili al computer che esegue il backend. In un ambiente cloud un percorso sul tuo Mac/PC non è accessibile: usa il cloud per sviluppare e testare il codice con campioni sintetici; avvia la suite sul tuo computer per lavorare sui contenuti privati.

## Trascrizione locale

La trascrizione usa faster-whisper sul computer dell'utente. L'installazione della libreria non basta: serve un modello compatibile scaricato in una cartella locale. Il download è un'azione esplicita; non viene avviato durante l'importazione o la trascrizione di un video.

Scarica esplicitamente il modello `tiny` (il download può richiedere diversi minuti):

```text
uv run --frozen --extra ai python scripts/download_model.py --size tiny
```

Lo script usa per impostazione predefinita `.data/models/whisper-tiny`, che il backend riconosce automaticamente. Usa `--output PERCORSO` per scegliere un'altra cartella e `--help` per tutte le opzioni. Per un percorso diverso imposta `VIDEOSCRIPT_WHISPER_MODEL` **prima** di avviare la suite.

macOS:

```bash
export VIDEOSCRIPT_WHISPER_MODEL="/percorso/assoluto/modello"
bash scripts/start-macos.command
```

Windows, Prompt dei comandi:

```bat
set "VIDEOSCRIPT_WHISPER_MODEL=C:\percorso\modello"
scripts\start-windows.bat
```

Il modello `tiny` è utile per una prima verifica rapida; modelli più grandi richiedono più memoria e tempo. La configurazione CPU usa quantizzazione int8. I timestamp AI sono stime e i segmenti sono marcati **Da verificare**; non equivalgono a sincronizzazione garantita al singolo fotogramma. La diarizzazione non è inclusa. Se il modello non è disponibile, player, annotazioni e salvataggio continuano a funzionare.

## Assistente del progetto

La modalità **base** consulta esclusivamente dati reali già presenti: metadati, trascrizioni, annotazioni e rilievi QC. Offre filtri e riepiloghi deterministici e non inventa descrizioni delle immagini.

La modalità generativa richiede un modello locale configurato e un motore disponibile. L'integrazione opzionale Ollama usa soltanto il servizio loopback sulla porta 11434 e `VIDEOSCRIPT_OLLAMA_MODEL`. L'interfaccia deve confermare la disponibilità effettiva prima dell'uso; altrimenti mostra **Modello AI non configurato**. Per la prima installazione puoi utilizzare tutte le funzioni base senza Ollama.

Nessuna modifica alle annotazioni viene applicata dal chatbot senza un'azione esplicita dell'utente.

## Dati, privacy e copie di sicurezza

- Database, cache, proxy e copie importate tramite browser sono nella cartella `.data` del progetto. `VIDEOSCRIPT_DATA_DIR` permette di scegliere un'altra directory locale.
- L'importazione per percorso non modifica il file sorgente. Il proxy, quando necessario, viene creato nella cache mantenendo il collegamento temporale all'originale.
- Nessun video, audio, fotogramma o trascrizione viene inviato automaticamente a servizi esterni. Non configurare tunnel o pubblicazioni Internet del backend locale.
- Per una copia di sicurezza arresta l'app, copia l'intera cartella dati e conserva separatamente i media originali. Il salvataggio del progetto non incorpora necessariamente i video originali.
- Non aggiungere a Git `.data`, `.venv`, modelli, media privati o credenziali. Il `.gitignore` del progetto esclude i principali file locali.

## Timecode e limiti tecnici

Il timecode `HH:MM:SS:FF` usa fotogrammi, frame rate razionali e gestione esplicita Drop Frame/Non-Drop Frame. `FF` non rappresenta centesimi di secondo. È incluso il supporto alla matematica 29.97 DF; `;` identifica il separatore DF.

La navigazione mediante player HTML5 è dichiarata **approssimata**: il browser non garantisce il decoding esatto di ogni frame. I contenuti a frame rate variabile richiedono attenzione e vengono segnalati. Il tasto `J` effettua uno spostamento temporale: non simula una riproduzione inversa fluida.

I controlli QC sono preliminari. Sample peak non equivale a True Peak. Non viene dichiarata conformità broadcast, EBU R128 o PSE. Il QC avanzato, l'analisi visiva multimodale, la diarizzazione, il PDF e il packaging desktop non fanno parte di questa prima versione.

Nel CSV i dati arbitrari devono essere protetti dall'interpretazione come formule. Per modifiche in Excel importa il file come CSV UTF-8 e seleziona **Testo** per le colonne timecode: l'apertura diretta può applicare conversioni automatiche dipendenti dalla versione di Excel.

## Test e sviluppo

```text
uv run --frozen --extra ai pytest
npm --prefix frontend test
npm --prefix frontend run build
```

I test end-to-end del browser usano Playwright. Il download di Chromium è facoltativo ed esplicito; dalla cartella `frontend` esegui:

```text
npx playwright install chromium
npm run test:e2e
```

Se disponi già di un browser Chromium compatibile, puoi indicarne il percorso tramite `VIDEOSCRIPT_BROWSER_PATH` ed evitare il download. I test end-to-end richiedono anche FFmpeg e l'ambiente Python del progetto; eseguili senza altre istanze della suite in ascolto sulle porte usate dai test. Il download del browser non fa parte del normale avvio della suite.

Per un test manuale ripetibile segui [docs/TEST_MANUALE.md](docs/TEST_MANUALE.md). I test automatici usano media sintetici, senza caricare contenuti dell'utente su servizi esterni. I test che richiedono un modello locale devono essere distinti dai test di gestione del modello assente.

Avvio separato per sviluppatori, in due terminali dalla directory del progetto:

```text
uv run --frozen uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
npm --prefix frontend run dev
```

Il frontend usa il proxy Vite `/api` verso il solo backend locale. FFmpeg e FFprobe vengono eseguiti con argomenti separati, senza interpolazione in una shell. SQLite usa WAL per la persistenza locale.

```text
backend/app/       API, database, media/timecode, QC, trascrizione, assistente
frontend/src/      interfaccia React e componenti del player/editor
scripts/           avvio, setup e download esplicito del modello
tests/             test automatici e campioni generati a runtime
docs/              specifica, test manuali e percorso desktop
```

Il dettaglio delle funzioni effettivamente verificate e delle eventuali limitazioni dell'istanza di sviluppo viene riportato insieme alla consegna; la presenza di un comando in questa guida non certifica da sola l'esecuzione su macOS o Windows.

## Risoluzione dei problemi

| Problema | Azione |
| --- | --- |
| Porta 8000 o 5173 occupata | Chiudi un'altra istanza della suite; il launcher non termina processi che non ha avviato. |
| FFmpeg/FFprobe mancanti | Installa entrambi e riapri il terminale; verifica `ffmpeg -version` e `ffprobe -version`. |
| Modello AI non configurato | Installa l'extra `ai`, scarica esplicitamente un modello e imposta il relativo percorso. |
| Video non riproducibile nel browser | Genera il proxy H.264/AAC; verifica eventuali avvisi sul frame rate. |
| File originale non disponibile | Ricollega il media al nuovo percorso senza eliminare il progetto o le annotazioni. |
| Dipendenze frontend assenti | Esegui `npm --prefix frontend ci`. |
| Dipendenze Python assenti | Esegui `uv sync --frozen`, oppure aggiungi `--extra ai`. |
| Download modello bloccato | Verifica accesso ai domini Hugging Face indicati dall'errore; non disattivare TLS. Le altre funzioni restano utilizzabili. |

Per una futura applicazione installabile leggi [docs/DESKTOP.md](docs/DESKTOP.md). La specifica originale è conservata in [docs/SPECIFICA_MVP.md](docs/SPECIFICA_MVP.md).

Stato delle verifiche e limiti della consegna: [docs/VERIFICA_MVP.md](docs/VERIFICA_MVP.md).
