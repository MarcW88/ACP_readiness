# AI Commerce Readiness Checker

Analysez votre feed pour optimiser votre visibilité dans l'AI Shopping (ACP Feed API 2026-04-17 ou Google Merchant Center).

## Fonctionnalités

- **ACP Feed API 2026-04-17**: Analyse conforme au nouveau standard ACP (format JSON, push model)
- **Google Merchant Center**: Compatibilité avec les feeds XML traditionnels
- **Analyse ACP (OpenAI)**: Vérifie la conformité pour les agents d'achat ChatGPT
- **Analyse Google AI Shopping**: Évalue la préparation pour AI Mode, Gemini et Shopping Graph
- **Rapport détaillé**: Analyse champ par champ avec couverture et priorités
- **Export JSON**: Téléchargez les données complètes pour analyse ultérieure

## Installation

### Avec Gradio

```bash
pip install -r requirements.txt
python app_gradio.py
```

L'application sera accessible sur http://localhost:7860

### Avec Streamlit

```bash
pip install -r requirements.txt
streamlit run app_streamlit.py
```

L'application sera accessible sur http://localhost:8501

## Utilisation

1. Téléchargez votre fichier:
   - **JSON**: Feed ACP Feed API 2026-04-17 (nouveau standard)
   - **XML**: Feed Google Merchant Center (compatibilité)
2. Cliquez sur "Analyser le Feed"
3. Consultez les résultats dans les différents onglets:
   - **Résumé Global**: Vue d'ensemble des scores ACP et Google AI avec format détecté
   - **ACP (OpenAI)**: Détails de la conformité selon le format (ACP Feed API ou GMC)
   - **Google AI Shopping**: Analyse pour AI Mode et Gemini
   - **Détail par Produit**: Analyse individuelle des produits
   - **Export JSON**: Téléchargement du rapport complet

## ACP Feed API 2026-04-17 (Nouveau Standard)

### Format
- **Type**: JSON
- **Modèle**: Push (merchants pushent vers agents via API)
- **Structure**: Product/Variant separation

### Product Fields (Requis)
- `id`: Identifiant stable du produit
- `title`: Titre du produit

### Product Fields (Recommandés)
- `description`: Description du produit
- `url`: URL du produit
- `media`: Images du produit

### Variant Fields (Requis)
- `id`: Identifiant de la variante (pour checkout)
- `price`: Prix de la variante
- `availability`: Disponibilité

### Variant Fields (Recommandés)
- `title, description, url, media`: Contexte variante
- `list_price`: Prix de référence pour promotions
- `categories`: Catégories pour filtrage
- `condition`: État de l'article
- `variant_options`: Options (taille, couleur, etc.)
- `seller`: Informations vendeur

## Google Merchant Center XML (Compatibilité)

### Core Fields (60% du score)
- title, description, image_link, price, currency
- availability, brand, link, product_category
- gtin ou mpn (au moins un requis)

### Enriched Fields (30% du score)
- additional_image_link, color, size, gender
- age_group, material, weight

## Déploiement

Ce projet est configuré pour être facilement déployé sur:
- **Streamlit Cloud**: Pour la version Streamlit
- **Hugging Face Spaces**: Pour la version Gradio

## Structure du projet

```
ACP Readiness/
├── app_gradio.py          # Version Gradio (ACP Feed API + GMC)
├── app_streamlit.py       # Version Streamlit (ACP Feed API + GMC)
├── requirements.txt      # Dépendances Python
├── README.md             # Documentation
├── .gitignore           # Configuration Git
└── .streamlit/          # Configuration Streamlit
```

## Licence

Ce projet est fourni à des fins éducatives et commerciales.
