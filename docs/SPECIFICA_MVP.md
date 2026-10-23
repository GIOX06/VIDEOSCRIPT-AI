# VIDEOSCRIPT AI STUDIO — SPECIFICA DI SVILUPPO MVP 1.0

## RUOLO DELL'AGENTE

Agisci come Senior Software Architect, Full-Stack Developer ed esperto di tecnologie audiovisive, post-produzione, speech-to-text e controllo qualità broadcast.

Devi progettare e implementare un'applicazione locale realmente funzionante denominata:

**VideoScript AI Studio**

Non realizzare soltanto un mockup o un'interfaccia dimostrativa.

Il risultato deve essere un prototipo eseguibile, modulare e testabile, predisposto per una futura distribuzione come applicazione desktop macOS e Windows.

## 1. SCOPO DELL'APPLICAZIONE

VideoScript AI Studio è una suite professionale per:

1. Riproduzione e navigazione temporizzata di file audiovisivi.
2. Trascrizione dei dialoghi tramite AI locale.
3. Annotazione manuale e assistita di contenuti video e audio.
4. Controllo qualità audiovisivo preliminare.
5. Consultazione delle trascrizioni e dei risultati tramite chatbot.
6. Creazione di report esportabili.

L'applicazione deve essere pensata per operatori di doppiaggio, localizzazione, sottotitolazione, accessibilità audiovisiva e QC.

Tutti i contenuti multimediali devono rimanere sul computer dell'utente.

Nessun video, audio, fotogramma o trascrizione deve essere inviato automaticamente a servizi esterni.

## 2. STACK TECNOLOGICO

Frontend:
- React
- TypeScript
- Vite
- HTML5
- CSS responsivo
- Componenti modulari

Backend:
- Python 3.11 o versione compatibile con le dipendenze scelte
- FastAPI
- Uvicorn
- SQLite
- FFmpeg
- FFprobe
- faster-whisper per la trascrizione locale

Architettura:

Frontend React → API FastAPI localhost → Moduli Media, AI, QC e Database.

Il frontend deve comunicare esclusivamente con il backend locale autorizzato.

Predisporre la struttura per un futuro wrapper desktop Tauri 2, senza renderlo obbligatorio durante il primo sviluppo.

## 3. STRUTTURA DELL'INTERFACCIA

Interfaccia in stile software professionale di post-produzione.

Tema scuro predefinito.

Layout principale:

BARRA SUPERIORE:
- Nuovo progetto
- Apri progetto
- Importa video
- Salva progetto
- Esporta
- Impostazioni

PANNELLO SINISTRO:
- Video player
- Timecode
- Timeline
- Controlli di riproduzione
- Informazioni tecniche media

PANNELLO CENTRALE:
- Editor delle annotazioni
- Elenco timecode
- Trascrizioni audio
- Risultati QC
- Filtri e ricerca

PANNELLO DESTRO:
- AI Assistant
- Domande sulla trascrizione
- Suggerimenti per annotazioni
- Riepilogo delle scene
- Storico della chat del progetto

BARRA INFERIORE:
- Stato elaborazione
- Progresso dei processi AI
- Errori e avvisi
- Informazioni sul progetto

I pannelli devono essere ridimensionabili o almeno avere larghezze regolabili.

## 4. IMPORTAZIONE VIDEO

Permettere la selezione di file locali:

- MP4
- MOV
- MXF
- WebM

Quando viene caricato un file:

1. Registrare il percorso locale in modo sicuro.
2. Verificare che il file esista ed è leggibile.
3. Analizzarlo mediante FFprobe.
4. Recuperare i metadati disponibili.
5. Verificare se il codec è riproducibile dal frontend.
6. Se necessario, generare un proxy MP4 H.264/AAC.
7. Riprodurre il proxy mantenendo il collegamento all'originale.
8. Non modificare mai il file sorgente.

Il proxy deve conservare un'associazione temporale esplicita con l'originale.

Se la conversione cambia il frame rate, mostrare un avviso e non garantire automaticamente la corrispondenza frame-accurate.

Inserire una barra di avanzamento per la generazione del proxy.

## 5. TIMECODE PROFESSIONALE

Mostrare il timecode in formato:

HH:MM:SS:FF

Dove FF rappresenta il numero del fotogramma e non i centesimi di secondo.

Funzioni obbligatorie:

- Lettura automatica del TC di origine quando disponibile.
- Inserimento TC iniziale manuale.
- Rilevamento frame rate.
- Supporto frame rate razionali.
- Distinzione Drop Frame / Non-Drop Frame.
- Conversione tra TC, frame index e timestamp relativo.
- Navigazione inserendo un timecode.
- Salvataggio del TC nelle annotazioni.

Per ciascun file memorizzare:

- original_timecode
- start_timecode
- fps_numerator
- fps_denominator
- nominal_fps
- drop_frame
- media_duration
- source_frame_index

Realizzare funzioni dedicate per la matematica del timecode, evitando semplici approssimazioni basate sui millisecondi.

Per il prototipo utilizzare il frame rate del flusso video come riferimento, gestendo esplicitamente i limiti dei contenuti a frame rate variabile.

Se non è possibile garantire una navigazione esatta al fotogramma mediante il player HTML5, indicare la modalità come "approssimata" e prevedere un sistema futuro di navigazione tramite decoding.

## 6. CONTROLLI VIDEO

Realizzare controlli realmente funzionanti:

- Play
- Pause
- Stop
- Previous frame
- Next frame
- Seek -1 secondo
- Seek +1 secondo
- Seek -5 secondi
- Seek +5 secondi
- Velocità 0.25x
- Velocità 0.5x
- Velocità 0.75x
- Velocità 1x
- Velocità 1.5x
- Velocità 2x
- Mute / Volume
- Fullscreen

Scorciatoie da tastiera:

SPACE = Play/Pause

Freccia sinistra = fotogramma precedente

Freccia destra = fotogramma successivo

J = riproduzione indietro quando supportata, oppure spostamento temporale documentato

K = Pause

L = Play

I = Set TC IN

O = Set TC OUT

M = Nuovo marker

Le scorciatoie non devono interferire con la scrittura nei campi di testo.

Non simulare riproduzione inversa fluida se il motore video non la supporta.

## 7. EDITOR DELLE ANNOTAZIONI

Ogni annotazione deve avere:

- ID univoco
- Project ID
- Media ID
- TC IN
- TC OUT opzionale
- Start frame index
- End frame index opzionale
- Categoria
- Descrizione
- Origine
- Stato di verifica
- Data creazione
- Data ultima modifica

Categorie:

- Dialogue
- Visual Description
- Sound Effect
- Music
- Audio QC
- Video QC
- Technical QC
- Dubbing Note
- General Note

Funzioni:

- Aggiungi annotazione al TC corrente.
- Imposta IN/OUT.
- Modifica annotazione.
- Elimina con conferma.
- Duplica annotazione.
- Click sul TC per posizionare il player.
- Ordina per timecode.
- Filtra per categoria.
- Cerca nel testo.
- Collega annotazioni a risultati QC.
- Salvataggio automatico nel database.

Non sovrascrivere automaticamente le annotazioni manuali con risultati AI.

## 8. TRASCRIZIONE AUDIO AI LOCALE

Integrare faster-whisper o un motore compatibile.

Funzioni richieste:

- Estrazione audio mediante FFmpeg.
- Scelta della lingua o riconoscimento automatico.
- Trascrizione in segmenti.
- Timestamp iniziale e finale per segmento.
- Conversione timestamp → timecode.
- Visualizzazione progressiva dei risultati quando possibile.
- Importazione dei segmenti nell'editor.
- Correzione del testo.
- Riproduzione dal segmento selezionato.
- Possibilità di ritrascrivere un intervallo.

I timestamp prodotti dall'AI non devono essere presentati come sincronizzazione perfetta al singolo fotogramma.

Contrassegnare il testo AI come "Da verificare".

Non inventare dialoghi in assenza di audio comprensibile.

Prevedere marcatori per:
- Parlato incomprensibile
- Voci sovrapposte
- Segmenti incerti

La diarizzazione dei parlanti è opzionale e non deve essere simulata.

## 9. CONTROLLO QUALITÀ AUDIOVISIVO

Implementare un motore QC modulare.

PRIMO LIVELLO: MEDIA ANALYSIS

Recuperare:

- Container
- Codec video
- Codec audio
- Risoluzione
- Frame rate
- Bitrate
- Durata
- Numero e tipo di tracce audio
- Sample rate
- Numero di canali
- Timecode
- Pixel format
- Field order, se disponibile

SECONDO LIVELLO: QC AUTOMATICO DI BASE

Utilizzare filtri FFmpeg per cercare:

- Black frame / intervalli neri
- Silenzi audio
- Picchi audio sospetti, se misurabili
- Proprietà incompatibili con il preset selezionato
- Durata anomala rispetto ai parametri attesi

Consentire l'impostazione delle soglie e dei preset.

Classificare ogni risultato come:

- PASS
- WARNING
- FAIL
- NOT TESTED

Ogni evento temporale deve mostrare:

- Test effettuato
- TC IN
- TC OUT
- Descrizione
- Severità
- Valore misurato, se disponibile
- Soglia di riferimento, se prevista

Non trattare automaticamente un black frame o un silenzio come errore: potrebbero essere elementi intenzionali.

Fornire uno strumento per aprire l'intervallo segnalato nel player e confermare oppure respingere il rilievo.

PREPARARE, MA NON IMPLEMENTARE OBBLIGATORIAMENTE NEL MVP:

- Loudness EBU R128
- True Peak
- Freeze detection avanzata
- Flash / PSE detection
- Analisi multicanale
- Phase correlation
- Letterbox / Pillarbox
- Controlli codec e GOP per specifiche cliente

Non dichiarare conformità broadcast o PSE senza validazione tecnica dedicata.

## 10. CHATBOT AI LOCALE

Creare una chat contestuale associata al progetto.

Il chatbot deve poter utilizzare:

- Nome e metadati del file.
- Posizione attuale del player.
- Segmenti di trascrizione.
- Annotazioni.
- Eventi QC.
- Intervalli IN/OUT selezionati.

Supportare richieste come:

"Mostrami cosa viene detto in questa scena."

"Riassumi il dialogo tra questi due timecode."

"Quali problemi QC sono stati rilevati?"

"Elenca le annotazioni degli ultimi 30 secondi."

"Prepara una descrizione professionale di questa scena utilizzando le note disponibili."

"Correggi grammaticalmente questa annotazione."

"Genera un riepilogo degli errori segnalati."

Distinguere due modalità:

MODALITÀ BASE:
Consultazione locale di dati già presenti, filtri, ricerca e riepiloghi deterministici, senza modello linguistico.

MODALITÀ LLM LOCALE:
Integrazione opzionale con un modello linguistico eseguito sul computer per domande libere, riformulazioni e sintesi contestuali.

La modalità AI generativa deve risultare disponibile soltanto se un modello reale è configurato e funzionante.

In caso contrario mostrare "Modello AI non configurato", mantenendo operative le funzioni di consultazione.

Non generare risposte inventate sul contenuto delle immagini che non sono state analizzate.

Nessuna annotazione deve essere salvata o modificata dal chatbot senza conferma.

## 11. MODULO DI ANALISI VISIVA FUTURO

Predisporre un'interfaccia software per un motore multimodale locale.

Questa interfaccia deve poter ricevere:

- Frame corrente.
- Fotogrammi campionati da un intervallo.
- Timecode associati.
- Eventuali trascrizioni.
- Istruzioni dell'utente.

Output atteso:

- Descrizioni visive.
- Oggetti e azioni osservabili.
- Riepilogo della sequenza.
- Proposte di annotazioni.

Non implementare descrizioni generate artificialmente mediante testi statici o predefiniti spacciati per analisi AI.

Non inferire eventi intermedi da due soli fotogrammi senza indicare l'incertezza.

## 12. GESTIONE PROGETTI

Creare progetti persistenti.

Ogni progetto deve contenere:

- Identificativo
- Nome
- File sorgente associato
- Metadati
- Impostazioni TC
- Annotazioni
- Trascrizioni
- Risultati QC
- Impostazioni di analisi
- Cronologia chat
- Data creazione e ultima modifica

I video originali non devono essere copiati obbligatoriamente nel progetto.

Salvare percorsi e riferimenti ai file, prevedendo il ricollegamento quando il file non è più disponibile.

Salvare proxy e file temporanei in una cartella cache gestita.

Evitare perdita di lavoro in seguito a chiusure inattese.

## 13. ESPORTAZIONE

Implementare nell'MVP:

- TXT
- CSV UTF-8
- JSON

Esportare anche la trascrizione in SRT quando sono disponibili segmenti con inizio e fine.

Preparare un'estensione futura per PDF.

Le esportazioni devono includere dati reali e non contenuti dimostrativi.

Il CSV deve essere leggibile da Excel, preservando i campi timecode come testo.

## 14. SICUREZZA E PRIVACY

Il backend deve ascoltare soltanto su 127.0.0.1.

Impostare CORS in modo restrittivo.

Validare i percorsi dei file.

Non consentire esecuzione arbitraria di comandi da input utente.

Lanciare FFmpeg e FFprobe tramite argomenti sicuri, senza interpolazione in comandi shell.

Conservare eventuali impostazioni riservate fuori dal codice frontend.

Prevedere limiti di risorse, cancellazione dei processi e gestione degli errori.

Non utilizzare API cloud per impostazione predefinita.

## 15. ORGANIZZAZIONE DEL CODICE

Proporre una struttura simile a:

videoscript-ai/
  frontend/
    src/
      components/
      pages/
      hooks/
      services/
      types/
  backend/
    app/
      api/
      core/
      media/
      transcription/
      qc/
      assistant/
      database/
      models/
  tests/
  scripts/
  README.md

L'organizzazione può essere migliorata se esiste una soluzione più manutenibile.

## 16. ENDPOINT API

Definire almeno:

GET /api/health

POST /api/projects

GET /api/projects/{id}

POST /api/media/import

GET /api/media/{id}/metadata

POST /api/media/{id}/proxy

POST /api/media/{id}/transcribe

POST /api/media/{id}/qc

GET /api/projects/{id}/annotations

POST /api/projects/{id}/annotations

PATCH /api/annotations/{id}

DELETE /api/annotations/{id}

POST /api/assistant/query

GET /api/jobs/{id}

POST /api/jobs/{id}/cancel

GET /api/projects/{id}/export

Utilizzare task asincroni gestiti dal backend per i processi più lunghi.

Evitare richieste HTTP che rimangono bloccate durante un'intera conversione o trascrizione.

## 17. TEST E CRITERI DI ACCETTAZIONE

Preparare test automatici e istruzioni per un test manuale.

Verificare almeno:

1. Importazione di un MP4 valido.
2. Lettura dei metadati.
3. Rilevamento e impostazione manuale del TC.
4. Play e pausa.
5. Seek avanti e indietro.
6. Creazione di un'annotazione.
7. Associazione dell'annotazione al frame/timecode.
8. Salvataggio e riapertura del progetto.
9. Esportazione TXT/CSV/JSON.
10. Analisi QC di un media campione.
11. Trascrizione di audio di prova.
12. Apertura del video al TC di un risultato QC.
13. Cancellazione di un job senza corrompere il progetto.
14. Gestione di un media mancante.
15. Gestione di FFmpeg o modello AI non installato.

Includere test specifici delle conversioni timecode per 25 fps e 29.97 Drop Frame.

Non considerare completata una funzione che non supera i test previsti.

## 18. ORDINE OBBLIGATORIO DI REALIZZAZIONE

STEP 1:
Creare struttura progetto, backend FastAPI, frontend React e database SQLite.

STEP 2:
Realizzare l'interfaccia funzionante con video player e gestione progetto.

STEP 3:
Integrare FFprobe, timecode e proxy FFmpeg.

STEP 4:
Realizzare annotazioni sincronizzate e persistenza SQLite.

STEP 5:
Realizzare QC base con blackdetect, silencedetect e metadati.

STEP 6:
Integrare trascrizione locale con faster-whisper.

STEP 7:
Integrare assistente contestuale basato sui dati reali.

STEP 8:
Completare esportazioni, test, documentazione e script di avvio.

Eseguire e verificare ogni step prima di procedere al successivo.

## 19. DELIVERABLE RICHIESTI

Consegnare:

- Codice sorgente completo.
- Interfaccia realmente funzionante.
- Backend locale operativo.
- Database e migrazioni/schema.
- Script di avvio macOS.
- Script di avvio Windows.
- File delle dipendenze.
- README con installazione e utilizzo.
- Istruzioni per installare FFmpeg.
- Test automatici.
- Elenco delle funzioni realizzate.
- Elenco delle funzioni non ancora disponibili.
- Indicazioni per futuro packaging desktop.

## 20. REGOLE FINALI

Non utilizzare pulsanti finti o dati simulati presentati come reali.

Non affermare che una funzione sia completa senza averla verificata.

Se una funzionalità richiede dipendenze non disponibili, mostrare un errore comprensibile e documentare come abilitarla.

Mantenere sempre operativi il player, l'editor e il salvataggio, anche quando i motori AI non sono installati.

Dare priorità ad affidabilità, precisione del timecode, protezione dei file originali e facilità di utilizzo.

**INIZIA ORA DALLO STEP 1, CREA IL CODICE DEL PROGETTO E PROCEDI FINO A REALIZZARE IL PRIMO MVP FUNZIONANTE.**