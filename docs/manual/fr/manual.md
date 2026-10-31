% UNO Overlays pour OpenDeck — Manuel
% Sommaire

# Introduction {#introduction}

UNO Overlays pilote les overlays d'[UNO](https://overlays.uno) (Singular.live) depuis OpenDeck sous Linux, avec des touches et des knobs : afficher et masquer, slots du serveur, tableau de score, horloges, sources de données, sondages, objectifs, macros, OBS Studio et diagnostic.

Il est conçu pour la Rise Mode Vision 01 (15 touches) et la Vision Sound 01 (6 touches, 3 knobs et 3 boutons sans écran) et fonctionne avec tout appareil pris en charge par OpenDeck.

- Chaque touche montre son état : l'icône est **blanche** hors antenne et **rouge vif** à l'antenne. L'état vient d'UNO en temps réel.
- Chaque opération UNO, depuis n'importe quel appareil, touche, knob ou inspecteur, passe par **une file globale**, une à la fois et dans l'ordre.
- Les déclencheurs, les groupes exclusifs et la liste des control apps sont **globaux** : ils fonctionnent quel que soit le profil ou l'appareil à l'écran.

# Installation {#installation}

## Prérequis

- OpenDeck pour Linux 2.6.0 ou plus récent.
- Python 3.10 ou plus récent, avec les certificats HTTPS (Debian/Ubuntu : `sudo apt install python3 ca-certificates`).
- Un accès à internet pour communiquer avec UNO.
- OBS Studio 28 ou plus récent, uniquement pour les actions et déclencheurs OBS.
- Rien d'autre : la seule dépendance (`websockets`) est incluse dans le paquet.

## Installer ou mettre à jour

1. Téléchargez `opendeck-uno-overlays-<version>-linux.plugin.zip` depuis la release.
2. Dans OpenDeck, ouvrez **Plugins → Install from file** et choisissez le fichier.
3. L'installation remplace l'ancien dossier du plugin. Touches, knobs et réglages sont conservés : les identifiants du plugin et de ses actions n'ont pas changé.
4. Si une touche ne se met pas à jour, redémarrez OpenDeck.

![OpenDeck : Plugins → Install from file](botao_instalar_plugins.jpg)

## Mise à jour depuis la version 1.0

- Les déclencheurs des touches Overlay passent d'eux-mêmes dans la liste globale la première fois que chaque touche apparaît. Une touche qui n'apparaît jamais (autre profil, appareil non connecté) garde ses anciens déclencheurs jusqu'à ce qu'elle apparaisse une fois : ouvrez ce profil une fois après la mise à jour.
- L'option « Modifications à l'antenne (facultatif) – Masquer, modifier, réafficher » n'existe plus : les modifications à l'antenne sont toujours écrites directement, après la pause définie sur la page de réglages.

# Premiers pas {#first-steps}

1. Dans UNO, ouvrez la Control App de l'overlay, **? → API Description**, et copiez le jeton : la partie de l'adresse entre `/controlapps/` et `/api`. Utilisez le jeton de contrôle, pas l'URL de sortie utilisée dans OBS.
2. Dans OpenDeck, faites glisser une action **UNO Overlays** sur une touche, collez le jeton dans **Jeton d'API** et cliquez sur **Connecter / Recharger**.
3. Choisissez l'overlay (la liste a une recherche et des ★ favoris) et ce que fait la touche. Les modifications du formulaire vont directement à UNO ; attendez **Enregistré dans UNO.**
4. Chaque champ a un **?** à côté : passez le pointeur dessus, ou atteignez-le avec Tab, pour lire ce que fait le champ. Échap ferme le texte.

![Inspecteur d'une touche Overlay](inspetor_overlay.jpg)

# Page de réglages {#settings-page}

Ce que partagent toutes les touches se trouve sur la page de réglages du plugin : dans OpenDeck, dans **Plugins**, sur la carte **UNO Overlays**, cliquez sur la roue dentée verte (**Settings**). La page s'ouvre dans le navigateur par défaut, n'accepte que les connexions de cet ordinateur et se ferme après 10 minutes sans utilisation.

![OpenDeck : la roue dentée du plugin UNO Overlays](engrenagem_plugins.jpg)

![Page de réglages du plugin](pagina_configuracoes.jpg)

{{settings}}

## Langues

Le plugin parle portugais (Brésil), anglais, espagnol, italien, allemand, japonais, chinois (simplifié), coréen et français. Avec **Automatique (langue d'OpenDeck)**, il suit la langue choisie dans les réglages d'OpenDeck ; une langue choisie sur la page de réglages est prioritaire. OpenDeck ne propose pas l'italien : l'italien se choisit donc uniquement sur la page de réglages. Quand la langue d'OpenDeck change, rouvrez un inspecteur ou la page de réglages pour que le plugin la lise.

## Déclencheurs

Un déclencheur exécute une fonction quand un événement se produit, comme les déclencheurs de vMix : afficher ou masquer un overlay après un délai pouvant aller jusqu'à 30 000 ms. Événements : une scène OBS passe au programme ou le quitte, le streaming commence ou s'arrête, l'enregistrement commence ou s'arrête, un overlay UNO passe à l'antenne ou la quitte (les enchaînements « Quand cet overlay passe à l'antenne / quitte l'antenne » de la version 1.0). Utilisez **Ajouter un déclencheur** pour en créer autant que nécessaire ; chacun peut être désactivé sans être supprimé.

Chaque déclencheur écrit dans le journal du plugin : l'événement reçu, la décision (déclenché ou ignoré, et pourquoi) et le résultat dans UNO, sans jeton.

## Groupes exclusifs

Les overlays d'un même groupe ne sont jamais à l'antenne ensemble : en afficher un masque les autres, y compris ceux dont la touche n'est pas à l'écran. Les touches Overlay choisissent leur groupe par son nom ; le temps et les membres se trouvent sur la page de réglages.

# Fonctionnement {#how-it-works}

- **File globale.** Toutes les touches, tous les knobs et inspecteurs de tous les appareils entrent dans une seule file : une opération UNO à la fois, dans l'ordre. Les rotations sur un même champ s'additionnent en une seule écriture.
- **Limites.** La file attend la fenêtre suivante quand elle atteint les limites annoncées par UNO. L'offre gratuite d'uno a un plafond quotidien de 10 000 appels à l'App API ; la touche État les compte.
- **Écritures.** Seul le serveur confirme une écriture ; rien n'est répété automatiquement après un délai dépassé.
- **Modifications à l'antenne.** Quand l'overlay est à l'antenne, une modification n'est envoyée qu'après une pause sans changement (1000 ms par défaut), pour que le public ne voie jamais un mot à moitié tapé. Fermer l'inspecteur, passer à un autre champ, appuyer sur une touche ou Panique l'envoient aussitôt.
- **Touches hors écran.** Les minuteries d'Auto Close et les appuis déjà faits continuent après un changement de profil ; seuls un vrai changement des réglages de la touche, Panique ou un nouvel appui les annulent.

# Limites {#limitations}

- **Viseur et knob.** Une touche Viseur et son knob ne fonctionnent que tant que les deux sont à l'écran : le knob garde ce qu'il est en train de choisir, et OpenDeck n'informe le plugin que des knobs du profil sélectionné.
- **Restaurer.** L'ensemble des overlays que Restaurer remet à l'antenne est gardé en mémoire : un redémarrage du plugin l'oublie.
- **Délais des déclencheurs.** Un délai de déclencheur déjà en cours survit aux modifications du déclencheur ; Panique l'annule.
- **Touches supprimées.** OpenDeck envoie le même événement quand une touche est supprimée et quand son profil change : un Auto Close déjà en cours se termine donc normalement (120 s au plus).
- **Migration.** Les déclencheurs de la version 1.0 ne passent dans la liste globale que lorsque leur touche apparaît au moins une fois.
- **Quiz.** Révéler la réponse est générique : choisissez le champ et les valeurs que votre overlay utilise pour révéler la réponse.

# Cas d'utilisation {#use-cases}

## Tableau de score

Des touches Champs numériques pour chaque équipe (la touche affiche +1, +2, +3…), une touche Affichage de valeur pour chaque score, Annuler, Verrou, Changement de côté quand les équipes changent de côté, Cycle pour la période et Réinitialiser maintenu 2 s à la fin.

## Quiz

Un knob Molette de slots avec le carrousel activé : chaque cran met la question suivante à l'antenne ; appuyer affiche ou masque l'overlay. Une touche Révéler la réponse révèle la réponse et copie la bonne option dans le champ de mise en valeur ; la question suivante la masque à nouveau d'elle-même.

## Horloge

Une touche Horloge dans un champ de texte : compte à rebours, chronomètre, heure du jour ou jusqu'à une heure de fin, avec des couleurs de fin. Sur un knob, tourner ajuste le temps et une touche Viseur l'affiche.

## Bandeau et listes

Une Source de données avec une liste saisie, un fichier .txt ou .csv, associée aux champs de l'overlay, avec Auto Next et Boucle.

## OBS Studio

Une touche OBS : scène change la scène de programme et peut afficher un overlay. Un déclencheur affiche le synthé de la caméra quand la scène « Webcam » passe au programme et le masque quand elle le quitte. OBS : actualiser le navigateur recharge plusieurs sources navigateur, ou toutes les sources navigateur d'une scène.

# Actions {#actions}

{{actions}}

# Dépannage {#troubleshooting}

- **« Saisissez le jeton d'API de contrôle, pas l'URL de sortie. »** Collez uniquement le jeton (lettres, chiffres, `_` et `-`).
- **« UNO HTTP 4xx ».** Le jeton est erroné ou a été révoqué : copiez-le à nouveau dans **API Description**.
- **« UNO HTTP 429 ».** Trop de requêtes : patientez un instant ; évitez les outils qui interrogent UNO avec le même jeton.
- **« OBS n'est pas connecté… ».** Configurez-le sur la page de réglages et vérifiez qu'OBS est ouvert.
- **La roue dentée n'ouvre rien.** Aucun navigateur par défaut n'est défini : `xdg-settings get default-web-browser` indique celui qu'utilise le système.
- **Une touche n'affiche qu'une alerte.** Le pupitre est verrouillé (Verrou du pupitre en rouge) ou la touche est hors des scènes OBS autorisées.
- **Un déclencheur ne s'est pas exécuté.** Consultez le journal du plugin : chaque déclencheur indique s'il s'est déclenché ou a été ignoré, et pourquoi. Journal : `~/.local/share/opendeck/logs/plugins/dev.br.consciencia.opendeck.uno-overlays.sdPlugin.log`

# Confidentialité et sécurité {#privacy}

Les noms et textes des overlays sont des données personnelles et sont envoyés à UNO. Le plugin n'envoie rien à ses auteurs et n'écrit aucun jeton dans les journaux. Les jetons sont conservés dans les réglages d'OpenDeck sur cet ordinateur ; la page de réglages ne réaffiche jamais un jeton ni le mot de passe d'OBS. Les scènes enregistrées et le journal peuvent être effacés sur demande (Supprimer la scène enregistrée, Effacer le journal). Pour exercer vos droits au titre de la LGPD brésilienne, ouvrez une issue dans le projet. Détails dans PRIVACY.md et SECURITY.md du plugin.
