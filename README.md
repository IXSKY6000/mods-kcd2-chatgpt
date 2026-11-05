# Street Talk — KCD2

Prototype expérimental pour **KCD2 sur PC, à la manette**. Ce dépôt était vide.
Il contient le code, le générateur de mod et les tests hors jeu.

[Télécharger la version de test v0.2.2 sur GitHub](https://github.com/IXSKY6000/mods-kcd2-chatgpt/raw/refs/heads/main/downloads/street_talk-v0.2.2-diagnostic.zip)

La v0.2.0 est détectée chez le joueur mais son interaction ne fonctionne pas.
La v0.2.1 corrige des fragilités de démarrage, ajoute le chemin d’interaction
ordinaire et des traces de diagnostic. Son fonctionnement en jeu reste à confirmer.
**Ce n'est pas encore une version validée dans KCD2.**

Comportement visé : regarder un PNJ proche, ouvrir un chat bref en restant libre
de marcher, puis choisir **Saluer en haut** ou **Provoquer en bas**. Henry parle,
le PNJ répond avec une réplique du jeu. Aucun doublage généré, aucune IA distante,
aucune clé API. Le mod ne lance pas la fenêtre de dialogue complet.

## Ce qui est implémenté

- Intégration Lua aux interactions natives de chat de `SinglePlayer`.
- Requête XGEN `dialog:chatRequest`, puis confirmation par l'invite native de chat.
- Génération de décisions Skald `Type="chat"`, `ChatPosition="First"` pour
  Saluer et `Second` pour Provoquer, avec références vocales originales.
- Variantes génériques homme/femme. Les réponses natives actives et les
  conversations déjà engagées gardent la priorité. Un chat simplement disponible
  ou une option « Suivre » ne bloque plus le mod. Les animaux, morts, inconscients, combats et dialogues occupés
  sont exclus, ainsi que les réponses natives en attente, y compris d’un autre PNJ
  proche. La disponibilité est revérifiée lors de l’appui sur R1.
- Deux salutations consécutives autorisées par PNJ, puis 90 secondes de délai.
  Une courte protection de deux secondes empêche les doubles appuis ; les
  conversations occupées restent bloquées pendant leur déroulement.
- Provocations espacées de 15 secondes. Trois provocations dans une fenêtre de
  trois minutes déclenchent une réponse plus vexée, une pénalité de relation
  supplémentaire et un refus du chat de trois minutes. Pas de combat forcé.
- La petite pénalité native `greeting_decrease` reste appliquée à chaque provocation.
  Les compteurs sont propres à la session de jeu, sans persistance de sauvegarde.
- Archives `.pak` ZIP sans compression et archive d'installation reproductible.

Les appels sont fondés sur des scripts publiquement consultables du jeu, mais
l'enregistrement des alias, les voix et le rendu restent à tester en jeu.
La couverture de presque tous les PNJ est un objectif, pas un résultat vérifié.

## Construire

Python 3.10+ suffit ; aucun paquet Python n'est nécessaire pour construire.
Extraire **son propre** `Data/Scripts.pak` avec les outils de modding ou un outil
ZIP, dans un dossier contenant `Quests/`. Les fichiers extraits ne sont pas
versionnés dans ce dépôt. Le générateur vérifie les répliques attendues et
s'arrête si les données sont incompatibles.

```powershell
python tools/build.py --scripts-root "C:\KCD2-extracted\Scripts"
```

Résultat : `dist/street_talk-prototype.zip`. Lire impérativement
[la procédure de validation](docs/VALIDATION.md) avant un essai.
La présence d'un ZIP ne signifie pas que le mod fonctionne dans le moteur.

Le générateur ajoute une branche inaccessible au parcours normal dans deux
graphes de salutations existants. Le chat du mod vise ses alias directement.
Il conserve les graphes de base pour leur enregistrement et leurs rôles vocaux.
La v0.2.1 ajoute aussi un pont en fin de `Scripts/GameRules/SinglePlayer.lua`
pour installer les callbacks dès la définition de la classe, avant leur éventuelle
mise en cache par le moteur. Tout autre mod remplaçant ce fichier nécessite une fusion.
Les fichiers du jeu sur disque ne sont jamais modifiés : seuls des remplacements
sont écrits dans le `.pak` du mod. Un autre mod remplaçant ces mêmes graphes
nécessite une fusion ; voir le rapport du build pour leurs chemins.

## Manette

**R1 sur PlayStation / RB sur Xbox** (`xi_shoulderr`) ouvre le chat du mod.
Une map `street_talk` distincte est chargée ; les bindings de réponses rapides
natives ne sont pas remplacés. La map du mod n'est activée que lorsqu'une cible
admissible reçoit ses invites. Elle est désactivée si une réponse native est
prioritaire ou si la cible n'est plus admissible. L'appui est revérifié côté Lua.

Le mod refuse aussi de s'ouvrir si un PNJ proche attend déjà une réponse,
si le joueur est en dialogue/monologue, en combat ou en situation tendue,
assis, couché ou en train de voler à la tire. Les bindings manquants désactivent
l'interaction. L'absence de conflit dans le moteur KCD2 reste à tester.

Une seconde confirmation native peut être nécessaire après la requête initiale.
Les choix à l'intérieur du chat conservent leurs commandes natives.

Pour préparer la recherche d'une commande inutilisée à pied :

```powershell
python tools/audit_controls.py "C:\KCD2\Data\GameData.pak" "C:\MonProfil\actionmaps.xml"
```

Fournir les archives contenant réellement `Libs/Config/` et les XML de profil
existants. L'audit recense les boutons et leurs actions sans modifier de fichier.
« Absent des fichiers fournis » ne garantit pas qu'un bouton est libre : il faut
vérifier les appuis courts/longs et les différents contextes dans le jeu.

## Tests hors jeu

```sh
python -m pip install -r tests/requirements.txt
python -m unittest discover -s tests -v
```

Les tests Lua utilisent Lua 5.1 via Lupa et des doublures des interfaces moteur.
Ils valident la logique et les structures produites, pas le moteur KCD2.

## Références

Voir [les sources et hypothèses d'intégration](docs/RESEARCH.md).

## Diagnostic v0.2.2

Remplacer l'ancien dossier `Mods/street_talk` par celui de la nouvelle archive.
Garder `street_talk` dans `mod_order.txt` s'il existe. Fermer complètement le jeu,
le relancer, charger une sauvegarde et regarder un PNJ admissible avant de tester R1.

Le fichier `kcd.log` doit annoncer `[StreetTalk] Script loaded: 0.2.2 diagnostic`.
Les traces suivantes distinguent l'attente du joueur, l'installation des callbacks,
la disponibilité d'une cible, l'affichage de l'invite R1 et l'envoi de la requête.
Une erreur de binding et les contrôles de disponibilité manquants sont signalés
une seule fois par cause, sans exposer de données d'authentification.
La boucle réessaie après une erreur au lieu de s'arrêter définitivement.

Le journal fourni pour la v0.2.0 prouve le chargement du script au menu. Il ne
prouve pas la cause de l'échec d'interaction dans une partie ; ne pas présenter
ces changements comme une correction moteur confirmée avant un nouvel essai.

## Disponibilité et conversation active (v0.2.2)

La présence d'un dialogue de quête, de commerce ou de chat disponible n'exclut
plus le PNJ. `CanChat` et un résultat non vide de `GetChatActions` ne servent
plus de preuves d'une réponse actuellement attendue. L'entrée R1 du mod peut
être proposée dans ce contexte ; l'interaction ordinaire de dialogue reste intacte.
L'invite native de simple démarrage de chat ou de suivi cède sa place à l'entrée
du mod sur ce chemin tant que le PNJ est admissible.

En revanche, `IsWaitingForDialogueReply`, une requête `HasChatRequest` déjà lancée,
une conversation `HasAcceptedChat`, un dialogue/monologue en cours ou une
restriction de quête continuent d'interdire l'ouverture. Une demande native en
attente est protégée même avant que son invite soit visible : elle a déjà été
lancée par le jeu. Le simple fait de posséder un dialogue n'est pas une demande.

Cette distinction est appliquée à l'affichage, au maintien de la map R1 et lors
de l'appui. Une restriction de quête apparue après l'ouverture bloque aussi les
choix du mod. La disponibilité antérieure d'un chat n'est plus interprétée comme
un accusé de réception de la requête du mod. Tout ceci nécessite encore un essai
dans le moteur KCD2, notamment l'arbitrage réel des maps de commandes.
