# Verifica della prima versione

Verifiche eseguite nell'ambiente cloud Linux sul codice di questa consegna. L'esecuzione nativa su Windows o macOS resta da verificare. I sorgenti e le istruzioni di installazione sono distribuiti tramite la repository GitHub e lo ZIP del progetto.

## Risultati

- **62 test backend superati**, nessun test saltato: timecode 25 fps e29.97/59.94 Drop Frame, import MP4 reale sintetico, metadati/TC FFprobe, proxy H.264/AAC con sorgente invariato, annotazioni e riapertura SQLite, export TXT/CSV/JSON/SRT, QC FFmpeg, media mancanti e ricollegamento, controllo Host/Origin, gestione componenti mancanti, cancellazione di un processo reale e recovery dopo arresto.
- **5 test frontend superati** per timecode, frame rate razionali e Drop Frame.
- **1 scenario Playwright superato in Chromium**: creazione progetto, import, play/pausa, seek avanti/indietro e da TC, creazione/modifica nota, ricaricamento con nota conservata, QC reale, conferma rilievo, apertura del player al TC del rilievo e download JSON con la nota corretta. Nessun errore JavaScript del browser.
- Installazione ripetuta con `uv sync --frozen --extra ai` e `npm --prefix frontend ci`; compilazione TypeScript/Vite di produzione riuscita.
- Launcher verificato su Linux: avvio backend e frontend, risposta tramite proxy, arresto di entrambi, rilevamento porta occupata. Script shell controllati con `bash -n`.

I campioni audiovisivi sono generati dai test: non contengono materiali dell'utente. Per SRT sono usati record di test dichiarati; questo non costituisce prova di riconoscimento vocale.

## Funzioni disponibili

Player e navigazione HTML5 approssimata, TC iniziale e Drop Frame, progetti persistenti, annotazioni manuali sincronizzate e modificabili, ricerca/categorie, proxy, rilievi QC revisionabili, esportazioni e consultazione deterministica dei dati locali. Backend limitato al loopback, origini ristrette e comandi FFmpeg senza shell.

## AI: implementata, inferenza ancora da verificare

faster-whisper e il motore nativo sono installati e importabili. La trascrizione locale, l'estrazione audio, i segmenti progressivi e gli intervalli sono implementati. **Il modello non è incluso e nessuna inferenza reale è stata verificata**: il download effettivamente tentato da Hugging Face è stato bloccato da CONNECT403 della rete cloud. Gli11 test di trascrizione controllano errori/prerequisiti; non provano l'accuratezza del riconoscimento. I test di accettazione sul parlato rimangono da eseguire dopo un download riuscito del modello.

Per Windows seguire `INIZIA_QUI_WINDOWS.md`: la prima installazione base funziona senza AI; il download modello è esplicito in un secondo momento. Nessuna chiave API cloud richiesta.

L'integrazione generativa Ollama è opzionale e non verificata con un modello reale in questa istanza. La UI abilita questa modalità soltanto quando un modello locale effettivamente raggiungibile risponde al controllo di disponibilità. Nessuna diarizzazione simulata.

## Limiti dichiarati

- Seek HTML5 approssimato; VFR rilevato indicativamente dai metadati, senza garanzia frame-accurate. La matematica TC usa frame interi e frame rate razionali; ore oltre24 non vengono riciclate.
- QC nero/silenzio e sample peak sulla prima traccia audio; non True Peak, EBU R128 o certificazione broadcast/PSE.
- Modello tiny utile per una prima prova, non garanzia di qualità professionale. Cancellazione inferenza cooperativa fra segmenti: un singolo passo nativo può richiedere tempo prima di fermarsi.
- Analisi visiva futura predisposta come interfaccia software; nessun modello visivo incluso.
- PDF, diarizzazione e installer desktop Tauri ancora da realizzare. Sono forniti script per applicazione web locale, non un `.exe`.
- Gli export non incorporano gli originali. Effettuare backup della cartella dati e conservare separatamente i media sorgenti.

## Configurazione cloud

Salvati in bozza `install_script`, `start_skill` e domini aggiuntivi Hugging Face per il download esplicito del modello. I domini salvati sono huggingface.co, cas-bridge.xethub.hf.co, cas-server.xethub.hf.co, transfer.xethub.hf.co, cdn-lfs.huggingface.co, cdn-lfs-us-1.hf.co e cdn-lfs-eu-1.hf.co; i preset dei package manager sono preservati.

Il salvataggio della bozza non applica automaticamente la rete né pubblica l'ambiente. Per riutilizzare l'ambiente cloud, rivedere e salvare le modifiche nelle impostazioni ambiente, poi pubblicarlo. La restaurazione in un task nuovo non è stata verificata. Per la distribuzione sul PC scaricare il codice dalla [repository GitHub](https://github.com/GIOX06/VIDEOSCRIPT-AI/tree/main) con Code → Download ZIP, oppure usare lo ZIP fornito nella consegna.
