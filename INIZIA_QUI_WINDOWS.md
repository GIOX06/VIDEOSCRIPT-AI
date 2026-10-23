# Inizia qui — Windows

Questa guida ti porta alla prima prova del programma sul tuo PC. Per iniziare non servono un account AI, un modello scaricato o conoscenze di programmazione.

Il progetto è una prima applicazione eseguibile dal browser locale, non un installer `.exe`. Gli script Windows sono forniti per l'avvio; la verifica automatica svolta nell'ambiente di sviluppo non sostituisce una prova sul tuo PC Windows.

## 1. Scarica ed estrai il progetto

Apri la [repository GitHub](https://github.com/GIOX06/VIDEOSCRIPT-AI/tree/main), premi **Code → Download ZIP**, poi fai clic destro sul file scaricato → **Estrai tutto**. Puoi anche usare lo ZIP del progetto fornito nella consegna. Non avviare i file direttamente dentro lo ZIP.

Apri la cartella estratta che contiene `README.md`, `pyproject.toml` e la cartella `scripts`.

Su GitHub seleziona il ramo **main** per trovare codice, documentazione e script. Non servono Git né un account AI per scaricare lo ZIP e iniziare la prova locale.

## 2. Installa i quattro strumenti necessari

Apri **Terminale Windows** oppure **Prompt dei comandi** dal menu Start. Copia una riga alla volta e attendi che termini prima di passare alla successiva:

```bat
winget install --exact --id Python.Python.3.12
winget install --exact --id OpenJS.NodeJS.LTS
winget install --exact --id Gyan.FFmpeg
winget install --exact --id astral-sh.uv
```

Se uno strumento è già installato, passa alla riga successiva. Se Windows richiede autorizzazione per l'installer, segui la richiesta mostrata sul tuo PC.

**Chiudi tutte le finestre del terminale e riaprile** al termine, così Windows riconoscerà i nuovi comandi. Se `winget` non è disponibile, installa/aggiorna **Programma di installazione app** dal Microsoft Store oppure usa i link agli installer nel [README](README.md).

## 3. Apri il terminale nella cartella giusta

In Esplora file apri la cartella estratta del progetto. Fai clic sulla barra degli indirizzi in alto, scrivi `cmd` e premi Invio: si aprirà il Prompt dei comandi nella cartella corretta.

In alternativa, apri il Prompt dei comandi e usa un comando simile, sostituendo il percorso con quello reale della tua cartella:

```bat
cd /d "C:\Users\IL_TUO_NOME\Downloads\VIDEOSCRIPT-AI"
```

Le virgolette sono necessarie se il percorso contiene spazi. Per controllare di essere nella cartella corretta puoi scrivere `dir`: nell'elenco deve comparire `README.md`.

## 4. Prepara il programma — solo la prima volta

Nel Prompt dei comandi aperto nella cartella del progetto esegui:

```bat
scripts\setup-windows.bat --base
```

Attendi il messaggio di installazione completata. Sono necessarie una connessione Internet e alcuni minuti. Questa prima installazione abilita player, progetti, note, QC, esportazioni e assistente di consultazione; il modello di trascrizione si può aggiungere in seguito.

Se compare un errore, fermati a quel messaggio e copiane il testo nella chat. Non devi cancellare il progetto o ricominciare da GitHub.

## 5. Avvia il programma

Sempre nella stessa finestra esegui:

```bat
scripts\start-windows.bat
```

Il browser si apre automaticamente quando frontend e backend locali sono pronti. **Lascia aperta la finestra del terminale mentre usi il programma.** Per chiudere la suite torna nel terminale e premi `Ctrl+C`.

Le volte successive basta aprire la cartella del progetto, avviare il Prompt dei comandi come sopra ed eseguire lo stesso comando di avvio. Non serve reinstallare tutto.

## 6. Fai la prima prova

1. Crea un nuovo progetto e dagli un nome, per esempio “Prima prova”.
2. Importa un breve video MP4 presente sul tuo PC.
3. Premi Play, metti in pausa e aggiungi un'annotazione al punto corrente.
4. Scrivi una nota e verifica il messaggio di salvataggio. Progetto e annotazioni vengono conservati automaticamente nel database locale.
5. Riapri il progetto e controlla che la nota sia ancora presente.
6. Prova l'esportazione TXT o JSON; in un secondo momento puoi eseguire il QC.

Il video viene elaborato dal backend sul tuo computer. L'importazione mediante percorso mantiene il riferimento all'originale; la selezione dal browser crea una copia nella cartella dati locale. Non viene inviato automaticamente a servizi cloud.

## 7. Aggiungi la trascrizione AI quando la prima prova funziona

Arresta prima la suite con `Ctrl+C`. Nello stesso Prompt dei comandi e nella cartella del progetto esegui, una riga alla volta:

```bat
uv sync --frozen --extra ai
uv run --frozen --extra ai python scripts/download_model.py --size tiny
scripts\start-windows.bat
```

Il secondo comando scarica esplicitamente il modello in `.data\models\whisper-tiny`; non invia video o audio. Il backend riconosce automaticamente questa cartella. Il modello `tiny` è adatto a una prima prova; l'accuratezza dipende dall'audio e i risultati richiedono verifica.

Ora importa un breve video con parlato comprensibile e prova la trascrizione scegliendo la lingua corretta. Se non scarichi il modello, le altre funzioni continuano a funzionare.

Per assistente generativo, opzioni avanzate e copie di sicurezza consulta il [README](README.md). Non è necessario configurarli per iniziare.
