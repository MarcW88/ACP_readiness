# AI Commerce Readiness Checker

Analysez votre feed Google Merchant Center pour optimiser votre visibilité dans l'AI Shopping (OpenAI ACP et Google AI Shopping).

## Fonctionnalités

- **Analyse ACP (OpenAI)**: Vérifie la conformité de votre feed pour les agents d'achat ChatGPT
- **Analyse Google AI Shopping**: Évalue la préparation pour AI Mode, Gemini et Shopping Graph
- **Rapport détaillé**: Analyse champ par champ avec couverture et priorités
- **Export JSON**: Téléchargez les données complètes pour analyse ultérieure

## Installation

### Avec Gradio (version originale)

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

1. Téléchargez votre fichier XML de feed Google Merchant Center
2. Cliquez sur "Analyser le Feed"
3. Consultez les résultats dans les différents onglets:
   - **Résumé Global**: Vue d'ensemble des scores ACP et Google AI
   - **ACP (OpenAI)**: Détails de la conformité pour les agents ChatGPT
   - **Google AI Shopping**: Analyse pour AI Mode et Gemini
   - **Détail par Produit**: Analyse individuelle des produits
   - **Export JSON**: Téléchargement du rapport complet

## Champs analysés

### ACP (OpenAI) - Champs requis
- `enable_search`: Permet aux agents IA de rechercher le produit
- `enable_checkout`: Permet aux agents IA d'effectuer l'achat
- `inventory_quantity`: Quantité en stock
- `seller_name`, `seller_url`: Informations sur le vendeur
- `return_policy`, `return_window`: Politique de retour

### Google AI Shopping - Core Fields (60% du score)
- title, description, image_link, price, currency
- availability, brand, link, product_category
- gtin ou mpn (au moins un requis)

### Google AI Shopping - Enriched Fields (30% du score)
- additional_image_link, color, size, gender
- age_group, material, weight

### Google AI Shopping - Agentic Fields (10% du score)
- inventory_quantity, item_group_id

## Déploiement sur GitHub

Ce projet est configuré pour être facilement déployé sur:
- **GitHub Pages**: Pour la version statique
- **Streamlit Cloud**: Pour la version Streamlit
- **Hugging Face Spaces**: Pour la version Gradio

## Structure du projet

```
ACP Readiness/
├── app_gradio.py          # Version Gradio
├── app_streamlit.py       # Version Streamlit
├── requirements.txt      # Dépendances Python
├── README.md             # Documentation
└── .github/              # Configuration GitHub (optionnel)
```

## Licence

Ce projet est fourni à des fins éducatives et commerciales.
