# Test manuale di accettazione

Eseguire sul computer che ospita il backend, usando un media di prova che si può legittimamente analizzare. Non usare dati sensibili per verificare un'installazione cloud. Questa checklist descrive le verifiche da effettuare: le caselle non rappresentano risultati già ottenuti.

## Preparazione

1. Installa i prerequisiti e le dipendenze come descritto nel README.
2. Avvia `scripts/start.py --no-browser` e verifica che annunci la disponibilità di entrambi i servizi.
3. Apri nel browser l'indirizzo locale indicato dal launcher.
4. Usa un video MP4 con audio di cui conosci durata, contenuto e frame rate; prepara anche un MOV/MXF/WebM che richieda un proxy, se disponibile.
5. Annota sistema operativo, versioni Python/Node/FFmpeg, modello di trascrizione e data della verifica.

Un campione sintetico di 8 secondi a 25 fps con nero e silenzio si può generare senza condividere media personali:

```text
ffmpeg -f lavfi -i "color=c=black:s=320x180:r=25:d=8" -f lavfi -i "anullsrc=r=48000:cl=stereo" -t 8 -c:v libx264 -pix_fmt yuv420p -c:a aac sample-qc.mp4
```

Questo campione serve per importazione, player e QC. Non dimostra la trascrizione di parlato: per quella usa un breve audio comprensibile con testo noto.

## Progetti, importazione e player

- [ ] Crea un progetto con un nome contenente lettere accentate.
- [ ] Importa il campione da un percorso assoluto leggibile.
- [ ] Verifica nome, durata, codec, dimensioni, frame rate e tracce audio nei metadati.
- [ ] Verifica che il file sorgente conservi dimensione e data di modifica originali.
- [ ] Riproduci, metti in pausa e arresta il video. Stop deve tornare all'inizio.
- [ ] Prova seek ±1s e ±5s, fotogramma precedente/successivo, velocità disponibili, mute, volume e fullscreen.
- [ ] Verifica l'avviso di navigazione HTML5 approssimata.
- [ ] Prova le scorciatoie SPACE, frecce, J/K/L, I/O e M.
- [ ] Scrivi in un campo di testo e verifica che le scorciatoie non spostino il player o creino marker.
- [ ] Se il formato non è riproducibile, genera il proxy; segui progresso e messaggio finale, quindi verifica la riproduzione.
- [ ] Su un media VFR verifica l'avviso e l'assenza di promesse di precisione al singolo frame.

## Timecode

- [ ] Verifica il TC di origine, se presente nel media.
- [ ] Imposta manualmente un TC iniziale e controlla che il frame 0 lo riporti.
- [ ] A 25 fps verifica che dopo `00:00:00:24` compaia `00:00:01:00`.
- [ ] A 29.97 DF verifica la transizione `00:00:59;29` → `00:01:00;02`.
- [ ] Verifica che `00:01:00;00` e `00:01:00;01` siano rifiutati in DF.
- [ ] Verifica la transizione `00:09:59;29` → `00:10:00;00`.
- [ ] Digita un TC valido per navigare; controlla che l'etichetta e la posizione relativa siano coerenti.
- [ ] Digita un TC fuori intervallo o precedente all'inizio; attendi un errore comprensibile.

## Annotazioni e persistenza

- [ ] Imposta IN e OUT e crea un'annotazione con categoria e descrizione.
- [ ] Controlla che frame index e timecode siano associati al media corretto.
- [ ] Modifica la descrizione e verifica il salvataggio automatico.
- [ ] Duplica l'annotazione; la copia deve avere un ID distinto.
- [ ] Filtra per categoria, cerca un testo e ordina per TC.
- [ ] Clicca sul TC di un'annotazione e verifica lo spostamento del player.
- [ ] Elimina un'annotazione dopo conferma; annullando la conferma deve restare presente.
- [ ] Chiudi e riapri il browser e il progetto. Verifica che il lavoro persista.
- [ ] Arresta e riavvia i servizi; il progetto e le annotazioni devono restare disponibili.

## QC

- [ ] Esegui l'analisi del campione nero/silenzioso e segui l'avanzamento.
- [ ] Verifica rilievi nero e silenzio come WARNING da verificare, senza automatiche dichiarazioni di errore.
- [ ] Apri un rilievo nel player e controlla il TC IN/OUT.
- [ ] Conferma o respingi un rilievo; controlla la persistenza della scelta.
- [ ] Collega una nuova annotazione al rilievo.
- [ ] Prova un media senza audio: controlli audio devono risultare NOT TESTED.
- [ ] Modifica soglie e preset; verifica la soglia riportata nel risultato e l'assenza di dichiarazioni di conformità broadcast/PSE.

## Trascrizione reale

Questa sezione richiede l'extra `ai` e un modello locale reale. Un errore di modello mancante verifica la gestione dell'errore, non il motore di trascrizione.

- [ ] Imposta `VIDEOSCRIPT_WHISPER_MODEL` e verifica che il motore risulti disponibile.
- [ ] Trascrivi un breve media con parlato noto e lingua selezionata.
- [ ] Confronta i segmenti con l'audio: devono derivare dall'audio reale, senza dialoghi dimostrativi.
- [ ] Controlla timestamp, conversione TC e stato Da verificare.
- [ ] Clicca un segmento e verifica il posizionamento del player.
- [ ] Correggi il testo e salva; riapri il progetto e verifica la correzione.
- [ ] Importa un segmento nelle annotazioni; non deve sovrascrivere annotazioni manuali.
- [ ] Ritrascrivi un intervallo: timestamp e TC devono includere l'offset dell'intervallo originale.
- [ ] Su audio incomprensibile verifica l'indicazione di incertezza; la diarizzazione non deve essere simulata.

## Assistente ed esportazioni

- [ ] In modalità base chiedi i problemi QC del progetto e confronta con i rilievi presenti.
- [ ] Chiedi annotazioni o trascrizioni in un intervallo selezionato; verifica che il contesto sia quello atteso.
- [ ] Senza LLM verifica il messaggio Modello AI non configurato e la disponibilità della modalità base.
- [ ] Chiedi una descrizione di immagini non analizzate: l'assistente non deve inventare oggetti o eventi.
- [ ] Verifica che la chat non modifichi automaticamente le annotazioni.
- [ ] Esporta TXT, CSV e JSON, quindi confronta i dati con quelli realmente salvati.
- [ ] Esporta SRT dopo una trascrizione; verifica inizio/fine e testo dei segmenti.
- [ ] Importa il CSV in Excel come UTF-8, colonne TC come Testo; verifica accenti e TC.
- [ ] Inserisci una nota che inizia con `=`, esportala e controlla che non venga interpretata come formula.

## Errori e recupero

- [ ] Avvia un job lungo e annullalo. Verifica stato cancelled e progetto ancora apribile.
- [ ] Arresta l'app durante un job e riavviala: il job non deve risultare completato falsamente.
- [ ] Sposta temporaneamente il media; progetto e annotazioni devono riaprirsi, mentre player/analisi mostrano un errore recuperabile.
- [ ] Ricollega il media; se frame rate o durata cambiano, deve comparire un avviso.
- [ ] Avvia senza modello configurato; player, editor, salvataggio ed esportazioni restano utilizzabili.
- [ ] Prova l'errore FFmpeg/FFprobe mancante in un ambiente isolato, senza rimuovere strumenti dal sistema: il messaggio deve spiegare il requisito mancante.
- [ ] Prova un percorso inesistente, un'estensione non ammessa e un URL remoto: importazione rifiutata senza eseguire comandi arbitrari.

## Registrazione dell'esito

Per ogni punto segnare **PASS**, **FAIL**, **SKIPPED** o **NOT TESTED**, con motivazione. Distinguere gli skip per modello assente da una trascrizione eseguita con successo. Conservare errori e log, evitando percorsi e contenuti sensibili quando si apre una segnalazione.
