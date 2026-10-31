% UNO Overlays per OpenDeck — Manuale
% Indice

# Introduzione {#introduction}

UNO Overlays controlla gli overlay di [UNO](https://overlays.uno) (Singular.live) da OpenDeck su Linux, con tasti e knob: mostrare e nascondere, slot del server, tabellone, orologi, origini dati, sondaggi, obiettivi, macro, OBS Studio e diagnostica.

È pensato per Rise Mode Vision 01 (15 tasti) e Vision Sound 01 (6 tasti, 3 knob e 3 pulsanti senza schermo) e funziona con ogni dispositivo supportato da OpenDeck.

- Ogni tasto mostra il proprio stato: l'icona è **bianca** fuori onda e **rosso acceso** in onda. Lo stato arriva da UNO in tempo reale.
- Ogni operazione su UNO, da qualsiasi dispositivo, tasto, knob o inspector, passa da **una coda globale**, una alla volta e in ordine.
- Trigger, gruppi esclusivi e l'elenco delle control app sono **globali**: funzionano con qualsiasi profilo o dispositivo sullo schermo.

# Installazione {#installation}

## Requisiti

- OpenDeck per Linux 2.6.0 o successivo.
- Python 3.10 o successivo, con certificati HTTPS (Debian/Ubuntu: `sudo apt install python3 ca-certificates`).
- Accesso a internet per comunicare con UNO.
- OBS Studio 28 o successivo, solo per le azioni e i trigger di OBS.
- Nient'altro: l'unica dipendenza (`websockets`) è inclusa nel pacchetto.

## Installare o aggiornare

1. Scarica `opendeck-uno-overlays-<versione>-linux.plugin.zip` dalla release.
2. In OpenDeck apri **Plugins → Install from file** e scegli il file.
3. L'installazione sostituisce la cartella precedente del plugin. Tasti, knob e impostazioni restano: gli identificatori del plugin e delle sue azioni non sono cambiati.
4. Se un tasto non si aggiorna, riavvia OpenDeck.

![OpenDeck: Plugins → Install from file](botao_instalar_plugins.jpg)

## Aggiornare dalla versione 1.0

- I trigger dei tasti Overlay passano da soli all'elenco globale la prima volta che ogni tasto compare. Un tasto che non compare mai (un altro profilo, un dispositivo non collegato) conserva i vecchi trigger finché non compare una volta: apri quel profilo una volta dopo l'aggiornamento.
- L'opzione "Modifiche in onda (facoltativo) – Nascondi, modifica, mostra di nuovo" non esiste più: le modifiche in onda vengono sempre scritte direttamente, dopo la pausa impostata nella pagina delle impostazioni.

# Primi passi {#first-steps}

1. In UNO apri la Control App dell'overlay, **? → API Description**, e copia il token: la parte dell'indirizzo tra `/controlapps/` e `/api`. Usa il token di controllo, non l'URL di output usato in OBS.
2. In OpenDeck trascina un'azione **UNO Overlays** su un tasto, incolla il token in **Token API** e fai clic su **Connetti / Ricarica**.
3. Scegli l'overlay (l'elenco ha ricerca e ★ preferiti) e cosa fa il tasto. Le modifiche nel modulo vanno direttamente a UNO; attendi **Salvato su UNO.**
4. Ogni campo ha un **?** accanto: passa il puntatore sopra, o raggiungilo con Tab, per leggere cosa fa il campo. Esc chiude il testo.

![Inspector di un tasto Overlay](inspetor_overlay.jpg)

# Pagina delle impostazioni {#settings-page}

Ciò che tutti i tasti condividono si trova nella pagina delle impostazioni del plugin: in OpenDeck, in **Plugins**, sulla scheda **UNO Overlays**, fai clic sull'ingranaggio verde (**Settings**). La pagina si apre nel browser predefinito, accetta connessioni solo da questo computer e si chiude dopo 10 minuti di inattività.

![OpenDeck: l'ingranaggio del plugin UNO Overlays](engrenagem_plugins.jpg)

![Pagina delle impostazioni del plugin](pagina_configuracoes.jpg)

{{settings}}

## Lingue

Il plugin parla portoghese (Brasile), inglese, spagnolo, italiano, tedesco, giapponese, cinese (semplificato), coreano e francese. Con **Automatico (lingua di OpenDeck)** segue la lingua scelta nelle impostazioni di OpenDeck; una lingua scelta nella pagina delle impostazioni ha la precedenza. OpenDeck non offre l'italiano, quindi l'italiano si sceglie solo nella pagina delle impostazioni. Quando la lingua di OpenDeck cambia, riapri un inspector o la pagina delle impostazioni perché il plugin la legga.

## Trigger

Un trigger esegue una funzione quando avviene un evento, come i trigger di vMix: mostrare o nascondere un overlay dopo un ritardo fino a 30 000 ms. Eventi: una scena di OBS entra o esce dal programma, lo streaming inizia o termina, la registrazione inizia o termina, un overlay di UNO entra o esce dall'onda (le catene "Quando questo overlay va in onda / esce dall'onda" della versione 1.0). Usa **Aggiungi trigger** per crearne quanti ne servono; ognuno può essere disattivato senza eliminarlo.

Ogni trigger scrive nel log del plugin: l'evento ricevuto, la decisione (eseguito o ignorato, e perché) e il risultato su UNO, senza token.

## Gruppi esclusivi

Gli overlay dello stesso gruppo non sono mai in onda insieme: mostrarne uno nasconde gli altri, anche quelli il cui tasto non è sullo schermo. I tasti Overlay scelgono il gruppo per nome; il tempo e i membri sono nella pagina delle impostazioni.

# Come funziona {#how-it-works}

- **Coda globale.** Tutti i tasti, knob e inspector di tutti i dispositivi entrano in un'unica coda: un'operazione su UNO alla volta, in ordine. Le rotazioni sullo stesso campo si sommano in un'unica scrittura.
- **Limiti.** La coda attende la finestra successiva quando raggiunge i limiti annunciati da UNO. Il piano gratuito di uno ha un limite giornaliero di 10 000 chiamate alla App API; il tasto Stato le conta.
- **Scritture.** Solo il server conferma una scrittura; nulla viene ripetuto da solo dopo un timeout.
- **Modifiche in onda.** Con l'overlay in onda, una modifica viene inviata solo dopo una pausa senza cambiamenti (1000 ms predefiniti), così il pubblico non vede mai una parola scritta a metà. Chiudere l'inspector, passare a un altro campo, premere un tasto o il Panico la inviano subito.
- **Tasti fuori schermo.** I timer di Auto Close e le pressioni già fatte continuano dopo un cambio di profilo; solo una modifica reale delle impostazioni del tasto, il Panico o una nuova pressione li annullano.

# Limitazioni {#limitations}

- **Visore e knob.** Un tasto Visore e il suo knob funzionano solo mentre entrambi sono sullo schermo: il knob conserva ciò che sta scegliendo, e OpenDeck informa il plugin solo dei knob del profilo selezionato.
- **Ripristina.** L'insieme di overlay che Ripristina riporta in onda vive in memoria: un riavvio del plugin lo dimentica.
- **Ritardi dei trigger.** Un ritardo di trigger già in corso sopravvive alle modifiche del trigger; il Panico lo annulla.
- **Tasti eliminati.** OpenDeck invia lo stesso evento quando un tasto viene eliminato e quando il suo profilo viene cambiato, quindi un Auto Close già in corso termina normalmente (al massimo 120 s).
- **Migrazione.** I trigger della versione 1.0 passano all'elenco globale solo quando il loro tasto compare almeno una volta.
- **Quiz.** Rivela risposta è generico: scegli il campo e i valori che il tuo overlay usa per rivelare la risposta.

# Casi d'uso {#use-cases}

## Tabellone

Tasti Campi numerici per ogni squadra (il tasto mostra +1, +2, +3…), un tasto Display del valore per ogni punteggio, Annulla, Blocco, Cambio campo quando le squadre cambiano lato, Ciclo per il periodo e Azzera tenuto premuto 2 s alla fine.

## Quiz

Un knob Ruota degli slot con il carosello attivo: ogni scatto manda in onda la domanda successiva; premere mostra o nasconde l'overlay. Un tasto Rivela risposta rivela la risposta e copia l'opzione corretta nel campo di evidenziazione; la domanda successiva la nasconde di nuovo da sola.

## Orologio

Un tasto Orologio in un campo di testo: conto alla rovescia, conteggio progressivo, ora del giorno o fino a un orario di fine, con colori di chiusura. Su un knob, girare regola il tempo e un tasto Visore lo mostra.

## Ticker ed elenchi

Un'Origine dati con un elenco scritto, un file .txt o .csv, mappata sui campi dell'overlay, con Auto Next e Ripeti.

## OBS Studio

Un tasto OBS: scena cambia la scena di programma e può mostrare un overlay. Un trigger mostra il sottopancia della telecamera quando la scena "Webcam" va in programma e lo nasconde quando esce. OBS: aggiorna browser ricarica più sorgenti browser, o tutte le sorgenti browser di una scena.

# Azioni {#actions}

{{actions}}

# Risoluzione dei problemi {#troubleshooting}

- **"Inserisci il token API di controllo, non l'URL di output."** Incolla solo il token (lettere, numeri, `_` e `-`).
- **"UNO HTTP 4xx".** Il token è errato o è stato revocato: copialo di nuovo in **API Description**.
- **"UNO HTTP 429".** Troppe richieste: attendi un momento; evita strumenti che interrogano UNO con lo stesso token.
- **"OBS non è connesso…".** Configuralo nella pagina delle impostazioni e verifica che OBS sia aperto.
- **L'ingranaggio non apre nulla.** Nessun browser predefinito impostato: `xdg-settings get default-web-browser` mostra quale usa il sistema.
- **Un tasto mostra solo un avviso.** Il banco è bloccato (Blocco del banco rosso) o il tasto è fuori dalle scene di OBS consentite.
- **Un trigger non è partito.** Guarda il log del plugin: ogni trigger scrive se è stato eseguito o ignorato, e perché. Log: `~/.local/share/opendeck/logs/plugins/dev.br.consciencia.opendeck.uno-overlays.sdPlugin.log`

# Privacy e sicurezza {#privacy}

Nomi e testi degli overlay sono dati personali e vanno a UNO. Il plugin non invia nulla ai suoi autori e non scrive token nei log. I token sono conservati nelle impostazioni di OpenDeck su questo computer; la pagina delle impostazioni non mostra mai un token né la password di OBS. Le scene salvate e il log possono essere eliminati su richiesta (Elimina scena salvata, Cancella log). Per esercitare i tuoi diritti secondo la LGPD brasiliana, apri una issue nel progetto. Dettagli in PRIVACY.md e SECURITY.md del plugin.
