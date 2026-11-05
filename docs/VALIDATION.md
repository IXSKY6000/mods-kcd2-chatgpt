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
