% UNO Overlays für OpenDeck — Handbuch
% Inhalt

# Einführung {#introduction}

UNO Overlays steuert die Overlays von [UNO](https://overlays.uno) (Singular.live) aus OpenDeck unter Linux, mit Tasten und Knobs: zeigen und ausblenden, Server-Slots, Anzeigetafel, Uhren, Datenquellen, Umfragen, Ziele, Makros, OBS Studio und Diagnose.

Es ist für die Rise Mode Vision 01 (15 Tasten) und die Vision Sound 01 (6 Tasten, 3 Knobs und 3 Knöpfe ohne Display) gedacht und funktioniert mit jedem Gerät, das OpenDeck unterstützt.

- Jede Taste zeigt ihren Zustand: Das Symbol ist **weiß** außerhalb der Sendung und **leuchtend rot** auf Sendung. Der Zustand kommt in Echtzeit von UNO.
- Jede UNO-Operation, von jedem Gerät, jeder Taste, jedem Knob und jedem Inspektor, läuft durch **eine globale Warteschlange**, eine nach der anderen und in Reihenfolge.
- Trigger, exklusive Gruppen und die Liste der Control Apps sind **global**: Sie funktionieren mit jedem Profil oder Gerät auf dem Bildschirm.

# Installation {#installation}

## Voraussetzungen

- OpenDeck für Linux 2.6.0 oder neuer.
- Python 3.10 oder neuer mit HTTPS-Zertifikaten (Debian/Ubuntu: `sudo apt install python3 ca-certificates`).
- Internetzugang für die Verbindung zu UNO.
- OBS Studio 28 oder neuer, nur für die OBS-Aktionen und -Trigger.
- Sonst nichts: Die einzige Abhängigkeit (`websockets`) ist im Paket enthalten.

## Installieren oder aktualisieren

1. Lade `opendeck-uno-overlays-<Version>-linux.plugin.zip` aus dem Release herunter.
2. Öffne in OpenDeck **Plugins → Install from file** und wähle die Datei.
3. Die Installation ersetzt den bisherigen Ordner des Plugins. Tasten, Knobs und Einstellungen bleiben erhalten: Die Kennungen des Plugins und seiner Aktionen haben sich nicht geändert.
4. Wenn eine Taste sich nicht aktualisiert, starte OpenDeck neu.

![OpenDeck: Plugins → Install from file](botao_instalar_plugins.jpg)

## Aktualisieren von Version 1.0

- Die Trigger der Overlay-Tasten wandern von selbst in die globale Liste, sobald jede Taste zum ersten Mal erscheint. Eine Taste, die nie erscheint (anderes Profil, nicht verbundenes Gerät), behält ihre alten Trigger, bis sie einmal erscheint: Öffne dieses Profil nach dem Update einmal.
- Die Option „Änderungen auf Sendung (optional) – Ausblenden, ändern, wieder zeigen“ gibt es nicht mehr: Änderungen auf Sendung werden immer direkt geschrieben, nach der auf der Einstellungsseite festgelegten Pause.

# Erste Schritte {#first-steps}

1. Öffne in UNO die Control App des Overlays, **? → API Description**, und kopiere das Token: den Teil der Adresse zwischen `/controlapps/` und `/api`. Verwende das Steuertoken, nicht die Ausgabe-URL aus OBS.
2. Ziehe in OpenDeck eine **UNO Overlays**-Aktion auf eine Taste, füge das Token in **API-Token** ein und klicke auf **Verbinden / Neu laden**.
3. Wähle das Overlay (die Liste hat Suche und ★ Favoriten) und was die Taste tut. Änderungen im Formular gehen direkt an UNO; warte auf **In UNO gespeichert.**
4. Jedes Feld hat daneben ein **?**: Fahre mit dem Zeiger darüber oder erreiche es mit Tab, um zu lesen, was das Feld tut. Esc schließt den Text.

![Inspektor einer Overlay-Taste](inspetor_overlay.jpg)

# Einstellungsseite {#settings-page}

Was alle Tasten gemeinsam nutzen, steht auf der eigenen Einstellungsseite des Plugins: In OpenDeck unter **Plugins** auf der Karte **UNO Overlays** auf das grüne Zahnrad (**Settings**) klicken. Die Seite öffnet sich im Standardbrowser, nimmt nur Verbindungen von diesem Computer an und schließt sich nach 10 Minuten ohne Nutzung.

![OpenDeck: das Zahnrad des Plugins UNO Overlays](engrenagem_plugins.jpg)

![Einstellungsseite des Plugins](pagina_configuracoes.jpg)

{{settings}}

## Sprachen

Das Plugin spricht Portugiesisch (Brasilien), Englisch, Spanisch, Italienisch, Deutsch, Japanisch, Chinesisch (vereinfacht), Koreanisch und Französisch. Mit **Automatisch (Sprache von OpenDeck)** folgt es der in den OpenDeck-Einstellungen gewählten Sprache; eine auf der Einstellungsseite gewählte Sprache hat Vorrang. OpenDeck bietet kein Italienisch an, daher wird Italienisch nur auf der Einstellungsseite gewählt. Wenn sich die Sprache von OpenDeck ändert, öffne einen Inspektor oder die Einstellungsseite erneut, damit das Plugin sie liest.

## Trigger

Ein Trigger führt eine Funktion aus, wenn ein Ereignis eintritt, wie die Trigger von vMix: ein Overlay zeigen oder ausblenden, nach einer Verzögerung von bis zu 30 000 ms. Ereignisse: Eine OBS-Szene kommt ins Programm oder verlässt es, das Streaming beginnt oder endet, die Aufnahme beginnt oder endet, ein UNO-Overlay geht auf Sendung oder von Sendung (die Verkettungen „Wenn dieses Overlay auf Sendung / von Sendung geht“ der Version 1.0). Mit **Trigger hinzufügen** legst du so viele an wie nötig; jeder lässt sich ausschalten, ohne ihn zu löschen.

Jeder Trigger schreibt ins Log des Plugins: das empfangene Ereignis, die Entscheidung (ausgelöst oder ignoriert, und warum) und das Ergebnis in UNO, ohne Tokens.

## Exklusive Gruppen

Overlays derselben Gruppe sind nie gleichzeitig auf Sendung: Eines zu zeigen blendet die anderen aus, auch die, deren Taste nicht auf dem Bildschirm ist. Overlay-Tasten wählen ihre Gruppe per Name; Zeit und Mitglieder stehen auf der Einstellungsseite.

# Funktionsweise {#how-it-works}

- **Globale Warteschlange.** Alle Tasten, Knobs und Inspektoren aller Geräte gehen in eine Warteschlange: eine UNO-Operation nach der anderen, in Reihenfolge. Drehungen am selben Feld werden zu einem Schreibvorgang zusammengefasst.
- **Grenzen.** Die Warteschlange wartet auf das nächste Zeitfenster, wenn sie die von UNO angekündigten Grenzen erreicht. Der kostenlose uno-Tarif hat ein Tageslimit von 10 000 App-API-Aufrufen; die Taste Status zählt sie.
- **Schreibvorgänge.** Nur der Server bestätigt einen Schreibvorgang; nach einer Zeitüberschreitung wird nichts von selbst wiederholt.
- **Änderungen auf Sendung.** Ist das Overlay auf Sendung, wird eine Änderung erst nach einer Pause ohne Änderungen gesendet (standardmäßig 1000 ms), damit das Publikum nie ein halb getipptes Wort sieht. Inspektor schließen, zu einem anderen Feld wechseln, eine Taste drücken oder Panik senden sie sofort.
- **Tasten außerhalb des Bildschirms.** Auto-Close-Timer und bereits gemachte Tastendrücke laufen nach einem Profilwechsel weiter; nur eine echte Änderung der Tasteneinstellungen, Panik oder ein neuer Druck brechen sie ab.

# Einschränkungen {#limitations}

- **Visier und Knob.** Eine Visier-Taste und ihr Knob funktionieren nur, solange beide auf dem Bildschirm sind: Der Knob behält, was er gerade wählt, und OpenDeck meldet dem Plugin nur Knobs des ausgewählten Profils.
- **Wiederherstellen.** Die Menge der Overlays, die Wiederherstellen zurückholt, liegt im Speicher: Ein Neustart des Plugins vergisst sie.
- **Trigger-Verzögerungen.** Eine bereits laufende Trigger-Verzögerung übersteht Änderungen am Trigger; Panik bricht sie ab.
- **Gelöschte Tasten.** OpenDeck sendet dasselbe Ereignis, wenn eine Taste gelöscht und wenn ihr Profil gewechselt wird; ein bereits laufendes Auto Close endet daher normal (höchstens 120 s).
- **Migration.** Trigger der Version 1.0 wandern nur dann in die globale Liste, wenn ihre Taste mindestens einmal erscheint.
- **Quiz.** Antwort aufdecken ist allgemein: Wähle das Feld und die Werte, mit denen dein Overlay die Antwort aufdeckt.

# Anwendungsfälle {#use-cases}

## Anzeigetafel

Zahlenfelder-Tasten für jedes Team (die Taste zeigt +1, +2, +3 …), eine Wertanzeige-Taste für jeden Spielstand, Rückgängig, Sperre, Seitenwechsel, wenn die Teams die Seiten tauschen, Zyklus für den Spielabschnitt und Zurücksetzen, am Ende 2 s gehalten.

## Quiz

Ein Slot-Rad-Knob mit eingeschaltetem Karussell: Jede Rastung bringt die nächste Frage auf Sendung; Drücken zeigt oder blendet das Overlay aus. Eine Taste Antwort aufdecken deckt die Antwort auf und kopiert die richtige Option in das Hervorhebungsfeld; die nächste Frage verbirgt sie wieder von selbst.

## Uhr

Eine Uhr-Taste in einem Textfeld: Countdown, aufwärts zählend, Uhrzeit oder bis zu einer Endzeit, mit Schlussfarben. Am Knob stellt Drehen die Zeit ein, und eine Visier-Taste zeigt sie.

## Ticker und Listen

Eine Datenquelle mit getippter Liste, einer .txt- oder .csv-Datei, den Feldern des Overlays zugeordnet, mit Auto Next und Wiederholen.

## OBS Studio

Eine Taste OBS: Szene wechselt die Programmszene und kann ein Overlay zeigen. Ein Trigger zeigt die Bauchbinde der Kamera, wenn die Szene „Webcam“ ins Programm geht, und blendet sie aus, wenn sie es verlässt. OBS: Browser aktualisieren lädt mehrere Browserquellen neu oder alle Browserquellen einer Szene.

# Aktionen {#actions}

{{actions}}

# Fehlerbehebung {#troubleshooting}

- **„Gib das API-Steuertoken ein, nicht die Ausgabe-URL.“** Füge nur das Token ein (Buchstaben, Ziffern, `_` und `-`).
- **„UNO HTTP 4xx“.** Das Token ist falsch oder wurde widerrufen: Kopiere es erneut unter **API Description**.
- **„UNO HTTP 429“.** Zu viele Anfragen: Warte einen Moment; meide Werkzeuge, die UNO mit demselben Token abfragen.
- **„OBS ist nicht verbunden …“.** Richte es auf der Einstellungsseite ein und prüfe, ob OBS geöffnet ist.
- **Das Zahnrad öffnet nichts.** Es ist kein Standardbrowser festgelegt: `xdg-settings get default-web-browser` zeigt, welchen das System verwendet.
- **Eine Taste zeigt nur eine Warnung.** Das Pult ist gesperrt (Pultsperre rot) oder die Taste ist außerhalb der erlaubten OBS-Szenen.
- **Ein Trigger wurde nicht ausgeführt.** Sieh ins Log des Plugins: Jeder Trigger schreibt, ob er ausgelöst oder ignoriert wurde, und warum. Log: `~/.local/share/opendeck/logs/plugins/dev.br.consciencia.opendeck.uno-overlays.sdPlugin.log`

# Datenschutz und Sicherheit {#privacy}

Namen und Texte der Overlays sind personenbezogene Daten und gehen an UNO. Das Plugin sendet nichts an seine Autoren und schreibt keine Tokens ins Log. Tokens liegen in den Einstellungen von OpenDeck auf diesem Computer; die Einstellungsseite zeigt nie ein Token oder das OBS-Passwort zurück. Gespeicherte Szenen und das Log können auf Wunsch gelöscht werden (Gespeicherte Szene löschen, Log leeren). Um deine Rechte nach dem brasilianischen LGPD auszuüben, eröffne ein Issue im Projekt. Details in PRIVACY.md und SECURITY.md des Plugins.
