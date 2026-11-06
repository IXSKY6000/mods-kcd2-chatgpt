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

## Constats de la v0.2.3

`open_world/bff_pozdravy_a_rozlouceni.xml` et
`open_world/reakce_na_stav_hrace.xml` déclarent chacun `VoiceNamespace=true` ;
le dialogue de taunt de combat déclare également son propre namespace.
La v0.2.3 conserve les réponses d'Henry dans `reakce_na_stav_hrace` et garde
`ReferenceLength` quand présent. La salutation provient du chat de garde,
clé neutre `npc__henry_bud_zdrav_KYdF`. La provocation provient de la variante
homme/femme du chat générique, « Starej se o svý! ».

Les réponses PNJ viennent du pool neutre `dec57` et du pool vexé `dec2`.
Leurs attributs `VoiceoverReductionMaxSequences`, `VoiceoverReductionRole`,
`VoiceCategory` et `VoiceCategoryRoles` sont conservés. La table
`skald_character.xml` identifie `char_TULACKA_BARBORA` avec la voix 68 et les
catégories `generic christian`. Cela ne constitue pas un inventaire de ses
fichiers VF disponibles : ils sont absents de l'environnement.

Les séquences sources utilisent `ExitScript` et non `EntryScript`. Le pont
`CallScriptFunctionInTable` est attesté dans `Libs/Tables/text/dialogue_functions.xml`,
notamment pour `DialogUtils.IsWealthyCustomer`. Les conditions du mod passent
désormais par ce pont plutôt que par des appels Lua directs dans une expression
Skald. La compatibilité finale du moteur reste à valider sur le jeu installé.
