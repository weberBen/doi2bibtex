# Mode Interactif avec Contrôles VIM - Guide d'utilisation

## Démarrage

Pour lancer le mode interactif, exécutez simplement le script sans argument:

```bash
python run.py
```

ou si vous avez installé le package:

```bash
d2b
```

## Fonctionnalités

### Modes VIM

Le script utilise les contrôles VIM avec deux modes:

- **INSERT mode** : Pour taper du texte (mode par défaut au démarrage)
- **NORMAL mode** : Pour les commandes (navigation, suppression, recherche)

**Indicateur de mode** : En bas de l'écran vous verrez `-- INSERT --` ou `-- NORMAL --`

### Recherche par titre (texte)

1. Lancez le script sans argument (démarre en **INSERT mode**)
2. Tapez ou collez le titre de l'article que vous recherchez
3. Appuyez sur **ESC** pour passer en **NORMAL mode**
4. Appuyez sur **Enter** pour lancer la recherche
5. Naviguez dans les résultats avec les flèches **↑** et **↓**
6. Appuyez sur **Espace** pour afficher l'abstract du résultat sélectionné
7. Appuyez sur **Entrée** pour sélectionner le résultat et obtenir le BibTeX
8. Appuyez sur **Echap** pour revenir en arrière

### Recherche par image (OCR depuis le clipboard)

1. Copiez une image contenant le titre de l'article (Ctrl+C sur une capture d'écran par exemple)
2. Lancez le script sans argument (démarre en **INSERT mode**)
3. Dans la console, appuyez sur **Ctrl+V** pour coller
4. L'image sera **automatiquement détectée** et l'OCR se lance avec une animation
5. Le texte extrait s'affiche dans la console (en **INSERT mode**)
6. Corrigez le texte si nécessaire, puis appuyez sur **ESC** pour passer en **NORMAL mode**
7. Appuyez sur **Enter** pour lancer la recherche
8. Suivez les mêmes étapes que pour la recherche par titre

## Contrôles VIM

### Mode INSERT (édition de texte):
- **ESC** : Passer en NORMAL mode
- **Ctrl+V** : Coller (détecte automatiquement les images pour OCR)
- **Ctrl+C** : Quitter
- Tous les autres caractères : Saisie normale

### Mode NORMAL (commandes):
- **Enter** : Lancer la recherche
- **i** : Retour en INSERT mode (à la position du curseur)
- **I** : Retour en INSERT mode (début de ligne)
- **a** : Retour en INSERT mode (après le curseur)
- **A** : Retour en INSERT mode (fin de ligne)
- **o** : Nouvelle ligne en dessous et INSERT mode
- **O** : Nouvelle ligne au dessus et INSERT mode
- **dd** : Supprimer la ligne courante
- **yy** : Copier la ligne courante
- **p** : Coller après le curseur
- **gg** : Aller au début du texte
- **G** : Aller à la fin du texte
- **v** : Mode visuel (sélection)
- **V** : Mode visuel ligne
- **ggVG** : Sélectionner tout
- **h/j/k/l** : Navigation (gauche/bas/haut/droite)
- **w/b** : Mot suivant/précédent
- **0/$** : Début/fin de ligne

### Navigation dans les résultats:
- **↑/↓** : Naviguer entre les résultats
- **Espace** : Afficher l'abstract du résultat sélectionné
- **Entrée** : Sélectionner le résultat et obtenir le BibTeX
- **Echap** : Revenir à l'écran précédent ou annuler

Depuis l'affichage de l'abstract:
- **Echap** : Retour aux résultats

Depuis les résultats:
- **Echap** : Retour à la console de recherche

## Informations affichées

Pour chaque résultat, vous verrez:
- Le titre de l'article
- Les auteurs (max 3 premiers)
- L'année de publication
- Le journal/venue

## Dépendances pour l'OCR

Pour utiliser la fonctionnalité OCR avec les images, vous devez avoir:

### Option 1: pytesseract (recommandé)
```bash
pip install pytesseract Pillow
```

Et installer Tesseract OCR sur votre système:
- **Ubuntu/Debian**: `sudo apt-get install tesseract-ocr`
- **macOS**: `brew install tesseract`
- **Windows**: Télécharger depuis https://github.com/UB-Mannheim/tesseract/wiki

### Option 2: easyocr (alternative)
```bash
pip install easyocr Pillow
```

## Exemples

### Recherche simple
```
-- INSERT --
quantum computing review
[ESC]
-- NORMAL --
[Enter]
→ Navigation dans les résultats
→ [Espace] pour voir l'abstract
→ [Entrée] pour sélectionner
```

### Recherche multiline (ajout de ligne en mode INSERT)
```
-- INSERT --
Attention is all you need
[o]  (ouvre nouvelle ligne en dessous et reste en INSERT)
transformers for neural networks
[ESC]
-- NORMAL --
[Enter]
→ Recherche lancée avec le titre sur 2 lignes
```

### Édition avec commandes VIM
```
-- INSERT --
quantum computing review
[ESC]
-- NORMAL --
[0]  (début de ligne)
[w]  (mot suivant)
[w]  (encore un mot)
[dw] (supprime "review")
[i]  (retour en INSERT)
machine learning
[ESC]
-- NORMAL --
[Enter]
→ Recherche pour "quantum computing machine learning"
```

### Recherche avec image depuis le clipboard
```
1. Copiez une capture d'écran contenant le titre (Ctrl+C ou outil de capture)
2. Lancez python run.py
-- INSERT --
3. Appuyez sur Ctrl+V
→ "Image detected!"
→ OCR en cours... (avec animation)
→ Texte extrait affiché
-- INSERT --
→ Corriger le texte si nécessaire (commandes VIM disponibles après ESC)
[ESC]
-- NORMAL --
[Enter]
→ Navigation dans les résultats
→ [Entrée] pour sélectionner
```

## Notes

- La recherche utilise l'API CrossRef pour trouver les articles
- Les résultats sont classés par pertinence
- Vous pouvez toujours utiliser l'ancienne méthode en passant un DOI ou arXiv ID directement:
  ```bash
  python run.py 10.1234/example
  ```
