# Vérifications réalisées

5 novembre 2026, environnement Linux, Python 3.12.14, Lupa 2.6 / Lua 5.1.

Commande : `python -m unittest discover -s tests -v`.
Résultat : **18 tests exécutés, 18 réussis**, aucun ignoré.

- Requêtes natives de chat et alias homme/femme.
- Exclusions de contexte, priorité des actions natives, installation unique du hook.
- Délai entre interactions, expiration, disparition du PNJ et erreur d'envoi.
- Aucune acceptation automatique d'un chat potentiellement issu d'une quête.
- Structure du paquet, ordre First/Second, conservation de la décision originale,
  références manquantes ou ambiguës refusées et construction reproductible.
- Audit des maps manette et refus de conclure lorsque les données sont absentes.

Construction supplémentaire sur les XML du miroir communautaire au commit
`9cb067543245ec5cf4e27b3d21e32485a35db518` : réussie, archive
`dist/street_talk-prototype.zip` produite. Archives ZIP et PAK vérifiées sans erreur.
Les graphes originaux restent structurellement identiques après retrait de la seule
branche ajoutée. Les empreintes des deux fichiers source correspondent au rapport.

**Non exécutés** : chargement du mod dans KCD2, validation Skald dans les outils
officiels, lecture audio, commandes manette, rendu et conséquences de réputation.
Le jeu, ses outils Windows et le profil réel du joueur ne sont pas présents ici.
Ces vérifications sont nécessaires avant de considérer le mod comme fonctionnel.

Version 0.2.0 : tests supplémentaires pour les deux salutations autorisées puis
le délai de 90 secondes, les trois provocations et le refus temporaire, la
décroissance et l’indépendance des compteurs, la réponse d’un autre PNJ,
l’apparition tardive d’une réponse native et le début du combat après ouverture.
Le paquet contient une map dédiée R1/RB ; son activation et l’arbitrage réel des
entrées restent à valider dans KCD2.
