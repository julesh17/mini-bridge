# 📅 Mini-bridge : Exporter un .ics par enseignant

Cette application **Streamlit** permet de filtrer des fichiers d’emploi du temps au format `.ics` par enseignant.  

---

## ✨ Fonctionnalités

- Dépôt **d’un ou plusieurs fichiers `.ics`**.
- Détection automatique des **enseignants** (`NOM, Prénom`) dans le champ `DESCRIPTION`.
- Sélection d’un ou plusieurs enseignants pour générer un nouvel agenda personnalisé.
- Ajout d’informations supplémentaires dans le `SUMMARY` :
  - **Groupes** (`G1`, `G2`, …) extraits des descriptions.
  - **Promo** (`P1`, `P2`, …) et **Classe** (`A1` … `A6`) extraites du nom du fichier si présentes.
- Téléchargement du fichier `.ics` filtré, prêt à être importé dans Google Calendar, Outlook, iCalendar, etc.
- Aperçu des séances retenues avant export.


