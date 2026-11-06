# Vérifications réalisées

5 novembre 2026, environnement Linux, Python 3.12.14, Lupa 2.6 / Lua 5.1.

Version 0.2.3 : `python -m unittest discover -s tests -v`.
Résultat : **34 tests exécutés, 34 réussis**, aucun ignoré.

- Construction reproductible, références manquantes/ambiguës refusées, ordre
  Saluer/Provoquer et intégrité des graphes originaux avant ajout de la branche.
- Map R1/RB dédiée et pont ajouté après le script SinglePlayer original.
- Requêtes de chat homme/femme, double salutation puis délai, trois provocations
  et refus temporaire, indépendance des compteurs, disparition du PNJ, expiration.
- Exclusions de contexte, blocage après début de combat ou restriction de quête,
  absence d'acceptation automatique des conversations natives.
- Préservation des interactions ordinaires, reprise après erreur, diagnostics,
  résultats booléens natifs numériques 0/1.
- Chat simplement disponible et suivi disponible autorisés ; réponses attendues,
  requêtes natives lancées et conversations acceptées protégées.
- Désactivation de la map du mod à l'apparition d'une réponse native ; contrôle
  renouvelé lors de l'appui R1. Une disponibilité préexistante ne sert pas
  d'accusé de réception d'une nouvelle requête.

Construction sur les XML du miroir communautaire au commit
`9cb067543245ec5cf4e27b3d21e32485a35db518` ; contrôle des ZIP et PAK produits.

**Non exécutés** : chargement de cette version dans KCD2, validation Skald dans
les outils officiels, lecture audio, rendu, arbitrage des entrées manette et
conséquences de réputation. Le jeu et ses outils Windows sont absents ici.

Le journal utilisateur prouve que la v0.2.0 était chargée au menu sur KCD2
1.5.6, mais le joueur indique que l'interaction ne fonctionnait pas. Les versions
0.2.1 et 0.2.2 restent des versions de test dont le fonctionnement en jeu doit
être confirmé. Les réussites hors moteur ne constituent pas cette confirmation.

Vérifications de la v0.2.3 : clé HUD localisée et traduction française incluse,
conservation de la durée de la réplique d'Henry, retrait des références hors
namespace, conservation des pools de voix et de leurs filtres, rejet de scripts
de quête dans les pools copiés. Les callbacks réellement émis dans le graphe
sont exercés sur deux salutations puis un troisième essai refusé. Les quinze
secondes après provocation et la courte attente après annulation sont testées.
Cette simulation n'est pas une exécution du compilateur d'expressions KCD2.

Retour utilisateur sur la v0.2.2 : entrée visible mais mal affichée (`@` et
caractères incorrects), silence d'Henry et de Bára en VF ; l'option revient
après quinze secondes et un éloignement. Ces problèmes sont distincts du
chargement des mods, qui fonctionne. L'audio et le rendu du correctif restent
à vérifier dans la version de jeu du joueur.
