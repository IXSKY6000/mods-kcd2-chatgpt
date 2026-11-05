# Sources, constatations et limites

Consultées le 5 novembre 2026. Aucun binaire, script original complet ni doublage
du jeu n'est versionné dans ce dépôt.

- [Guide officiel de structure des mods](https://warhorse.youtrack.cloud/articles/KM-A-3/Structure-of-a-Mod)
  et [Skald](https://warhorse.youtrack.cloud/articles/KM-A-18/Skald), lus via
  [le miroir communautaire](https://github.com/muyuanjin/kcd2-mod-docs).
- Miroir inspecté au commit `9cb067543245ec5cf4e27b3d21e32485a35db518`.
  `Scripts/Scripts/GameRules/SinglePlayer.lua` expose `IsUsableForChat` et
  `OnChatUsableMessage`, avec `player:AddLuaActions`.
- `Scripts/Scripts/Entities/AI/Shared/BasicAIActions.lua` montre les actions
  `chat_init_with_focus`, `chat_init_interactor_press`, la map
  `chat_init_interactor`, `inr_chatFollow`, `AHC_CHAT`, ainsi que `DoChat`,
  `AcceptChatRequest` et `OpenChat`. Ces noms sont observés, pas inventés.
- `Scripts/Scripts/Utils/InteractorAction.lua` donne la structure des actions.
- `Scripts/Scripts/Utils/DialogUtils.lua` et `Scripts/AI/speech/chat.xml`
  établissent le format de `dialog:chatRequest`, `table.MakeFromType` et
  `XGenAIModule.SendMessageToEntityData`.
- `Scripts/AI/npc/basic/switch/handlechat.xml` rejette les chats génériques
  si `metarole ~= 'NPC_ZDRAVI_HRACE'`. Le prototype conserve cette métarôle
  et adresse des décisions par alias. Cette combinaison requiert un essai moteur.
- Les graphes génériques `zjednodusena_varianta_zdraveni` et sa variante `_1`
  sont de type `chat` et emploient les rôles `HRAC`, `NPC_ZDRAVI_HRACE_MUZ`
  et `NPC_ZDRAVI_HRACE_ZENA`. Leur wrapper existe déjà dans le graphe du monde.
- Le graphe de Kuběnka démontre `ChatPosition="First"`, et le chat de combat
  des choix positionnés. Le choix bas utilise `Second` ; rendu exact non testé.
- Les réponses sont copiées par référence de texte/voix depuis les données locales.
  Henry salue avec « Pochválen buď! » et provoque avec « Na mě nemáš! » dans les
  textes de conception tchèques. La localisation installée doit résoudre ces clés.

## Non établis

R1/RB est choisi explicitement par le joueur et déclaré dans une map séparée.
Il n’est pas supposé libre. Pas de preuve actuelle d’enregistrement des nouveaux
alias par le moteur, de résolution des voix déplacées entre graphes, ni de couverture
des PNJ nommés. Les tests hors jeu ne répondent pas à ces questions. Le prototype
n'ajoute ni synthèse vocale ni services ChatGPT ; ils ne sont pas nécessaires à la demande.

La map additionnelle utilise `xi_shoulderr`. Le chargement additif de maps et
le format ont aussi été confrontés à `CryAction/ActionMapManager.cpp` de
[la source CryEngine de référence](https://github.com/ValtoGameEngines/CryEngine).
Cela ne prouve pas le comportement du fork KCD2 : l’arbitrage des maps et
les réponses de quête doivent toujours être testés dans le jeu.
