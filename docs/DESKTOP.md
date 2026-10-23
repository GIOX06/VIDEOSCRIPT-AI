# Percorso verso un'applicazione desktop

L'MVP separa frontend React, API locale FastAPI e moduli di analisi. Questa struttura permette di aggiungere un wrapper **Tauri2** senza cambiare il formato dei progetti. Il wrapper e gli installer non sono inclusi nella prima versione.

## Passi successivi

1. Aggiungere un progetto Tauri2 separato che utilizzi la build di `frontend/dist`.
2. Distribuire il backend Python come processo sidecar, con un interprete e dipendenze verificati per ciascuna piattaforma. L'installazione non deve dipendere da un Python globale dell'utente.
3. Avviare il backend soltanto su loopback, con una porta assegnata e un token di sessione non esposto a siti esterni. Tauri deve verificare la readiness prima di mostrare il progetto.
4. Sostituire l'importazione dal browser con un dialogo file nativo che fornisca il percorso originale senza copiarlo obbligatoriamente. Il backend continua a validarlo e a non modificare l'originale.
5. Definire una cartella dati per utente e migrazioni SQLite versionate; conservare il ricollegamento ai media, la cache gestita e le copie di sicurezza.
6. Gestire arresto del backend e dei processi FFmpeg quando si chiude la finestra. Chiedere conferma se ci sono job attivi e preservare gli stati interrotti.
7. Gestire download opzionali dei modelli con progresso, verifica di integrità, spazio disponibile e consenso esplicito. Nessun modello deve comportare invio del media a servizi esterni.
8. Preparare build separate per macOS Apple Silicon/Intel e Windows x64, verificando i binari FFmpeg, CTranslate2 e la licenza di distribuzione di ciascuna dipendenza.
9. Applicare firma del codice, notarizzazione macOS e firma degli installer Windows; verificare gli aggiornamenti prima dell'installazione.
10. Eseguire la checklist manuale e i test di sicurezza su ogni piattaforma supportata prima di dichiarare disponibile un pacchetto desktop.

## Sicurezza del wrapper

Le capability Tauri devono essere ristrette alle funzioni necessarie. Non abilitare shell generiche o lettura arbitraria del filesystem nel frontend. I comandi multimediali rimangono nel backend con argomenti separati. La WebView deve impedire navigazioni a contenuti remoti e caricare soltanto gli asset locali della suite.

Il futuro token di sessione integra le verifiche Host/Origin e la CORS restrittiva. Non inserire credenziali o impostazioni riservate nei bundle JavaScript.

## Estensioni pianificate

- Decoding dedicato per navigazione realmente esatta al fotogramma; il player HTML5 resta dichiarato approssimato fino a questa integrazione.
- Analisi visiva tramite un modello locale reale, con frame e TC associati e indicazione dell'incertezza.
- Misure QC avanzate EBU R128/True Peak, analisi multicanale, freeze, PSE e specifiche cliente, ciascuna con validazione tecnica dedicata.
- Diarizzazione dei parlanti e report PDF.

Queste estensioni richiedono implementazione e test propri. Non sono dichiarazioni di funzionalità già disponibili o di conformità broadcast.
