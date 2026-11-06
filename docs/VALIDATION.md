# Prototype : validation KCD2 indispensable

Statut au 5 novembre 2026 : aucune exécution du jeu dans cet environnement Linux.
Les scripts consultés correspondent à un miroir communautaire `release_1_5`.
Le build produit un candidat de test, pas une version jouable certifiée.

## Hypothèses à vérifier avec les outils officiels

1. Skald charge les deux graphes de remplacement sans erreur. Les alias
   `streettalk_male` / `streettalk_female` doivent pouvoir entrer directement dans
   une décision imbriquée sous une branche dont l'entrée normale vaut `false`.
   Si ce n'est pas possible, enregistrer un graphe propre avec les outils Skald ;
   ne pas rendre la branche accessible aux salutations ordinaires pour contourner.
2. Le moteur expose le PNJ au chat interactor après `IsUsableForChat`. Vérifier
   que `CanInteractWith` et les restrictions de dialogue conviennent à pied.
3. La requête de salutation peut viser ces alias pour des PNJ génériques. Le moteur
   choisit bien les rôles homme/femme. Un PNJ nommé peut ne pas avoir les voix
   génériques nécessaires : ne pas lui substituer la voix d'un autre personnage.
4. Les `StringName` réutilisés retrouvent à la fois l'audio et les sous-titres de
   la langue du jeu, même déplacés depuis un autre graphe/namespace vocal.
   Une clé existante prouve une référence, pas la résolution effective du doublage.
5. Les conditions et scripts de choix accèdent au global Lua `StreetTalk`. Vérifier
   les deux salutations autorisées, le blocage du troisième salut pendant 90 secondes,
   puis le déblocage. Vérifier le troisième affront, la réponse vexée et le refus
   pendant trois minutes.
   `First` est affiché au-dessus de `Second` et les invites françaises sont lues.
6. La confirmation manuelle via l'invite native ouvre le chat attendu. Aucune
   acceptation automatique n'est tentée : l'API publique ne permet pas de corréler
   sûrement une demande de chat à un identifiant. Tester l'arrivée d'une demande
   de quête concurrente avant la confirmation.

## Essai local

- Sur une installation PC avec les Modding Tools, garder une sauvegarde de test.
- Extraire le ZIP dans `KingdomComeDeliverance2/Mods/` : on doit obtenir
  `Mods/street_talk/mod.manifest` et `Mods/street_talk/Data/street_talk.pak`.
- Si `Mods/mod_order.txt` existe, y ajouter `street_talk` en conservant ses entrées.
- Relever les erreurs `[StreetTalk]` et Skald dans les journaux du jeu.
- Essayer d'abord un homme puis une femme génériques, dans chacune des deux régions.
  Ouvrir le chat, tester Saluer, puis Provoquer après 15 secondes.
- Vérifier Henry puis le PNJ, les voix correspondant au personnage, les sous-titres,
  l'ordre des choix, la liberté de mouvement et l'absence de caméra de dialogue.
- Vérifier que s'éloigner, annuler ou laisser expirer la demande ne bloque rien.
- Tester ensuite commerçants, gardes et PNJ nommés. Relever les exclusions ; aucune
  promesse de couverture universelle avant ces essais.
- Tester R1 avec une réponse rapide native sur la cible ET sur un autre PNJ proche.
  Le mod doit retirer sa map et laisser le dialogue original intact. Tester aussi
  une réponse native apparue entre le rendu de l’invite et l’appui sur R1.
- Tester combat, furtivité, PNJ inconscient, conversation de quête avec Hans et
  trajet en charrette : les chats de l'histoire doivent garder la priorité.
- Vérifier la manette en marche, course, à cheval, en combat et dans les menus,
  avec appuis courts et longs, avant de choisir un nouveau raccourci.
- Recharger une sauvegarde et vérifier le rétablissement des hooks.

Pour retirer le prototype, supprimer son dossier et son entrée éventuelle dans
`mod_order.txt`. Les compteurs du mod restent en mémoire pendant la session. Le code ne les
enregistre pas dans la sauvegarde.
La réputation native éventuellement modifiée par Provoquer appartient toutefois
à la progression du jeu ; utiliser la sauvegarde de test pour revenir en arrière.

## Version de diagnostic 0.2.1

Le journal utilisateur confirme le chargement de la v0.2.0 sur KCD2
`1.5.6-15693-release_1_5`, mais cette version ne fonctionne pas chez le joueur.
Le journal disponible s'arrête au menu et ne révèle pas la cause dans le monde.
La version 0.2.1 ajoute une installation des hooks au chargement de la classe
SinglePlayer, une entrée via les interactions ordinaires et une boucle résistante
aux exceptions. Vérifier les conflits avec les mods remplaçant SinglePlayer.lua.

Après un essai, chercher `[StreetTalk]` et les erreurs Lua dans `kcd.log`.
Dans la version actuelle, la ligne `Script loaded: 0.2.2 diagnostic` doit être présente dès le démarrage.
Le diagnostic ne désactive aucun contrôle de combat ou de réponse native pour
forcer l'apparition de l'invite.

## Distinction de la v0.2.2 à vérifier en jeu

- Sur un commerçant ou un PNJ possédant un dialogue de quête disponible, R1 doit
  proposer le mod si aucune conversation n'est engagée et aucune demande lancée.
- Un chat disponible (`CanChat`) ou une option « Suivre » disponible ne doit pas
  exclure le PNJ. L'interaction ordinaire de dialogue doit toujours être présente.
- Une réponse native effectivement attendue doit rétablir le gestionnaire natif,
  y compris si elle apparaît après l'affichage de l'invite du mod.
- Une demande native déjà lancée/acceptée reste protégée, même avant une invite.
- Déclencher une restriction de quête après l'ouverture doit empêcher les choix
  du mod. Combat, incapacités et délais doivent toujours être respectés.
- Vérifier que le moteur n'exécute pas les deux actions R1 simultanément quand
  la disponibilité native et l'entrée du mod coexistent : les tests Lua ne
  valident pas l'arbitrage des maps dans le moteur.

## Vérifications de la v0.2.3 (VF)

- L'invite R1/RB affiche « Parler » sans arobase ni clé de traduction brute.
- Après un premier salut et la fin du chat, un deuxième salut doit être possible
  dès la courte protection de deux secondes écoulée. Le troisième doit attendre
  90 secondes. Une annulation d'ouverture ne compte pas comme salutation.
- Vérifier les traces `Choice committed: greet` et `Choice committed: antagonize`.
  Une trace `Choice callback rejected` indique un contrôle de session à examiner.
- Écouter Henry sur Saluer et Provoquer, puis Bára sur les deux choix. Comparer
  avec un homme et une autre femme génériques. La sélection vocale native est
  conservée, mais sa résolution des fichiers VF n'est pas vérifiable hors jeu.
- Confirmer dans Skald/moteur les appels `CallScriptFunctionInTable` dans les
  conditions, l'exécution d'`ExitScript` avant la décision de réaction suivante,
  et la remise à disposition des choix déjà utilisés (`GrayOutIfSequencesUsed=Never`).
- Si une voix reste muette, recueillir le log après l'essai : ne pas attribuer
  une autre voix au PNJ ni distribuer des fichiers VF pour masquer l'erreur.
