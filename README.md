# ACP Migration Assistant

Transformez votre feed produit existant en **ACP Feed API 2026-04-17** — le standard ouvert pour le commerce agentique (OpenAI ChatGPT, Stripe).

## Concept

Plutôt qu'un simple checker de champs, cet outil est un **assistant de migration actif** :
- Upload votre feed → détection automatique du format
- Mapping guidé des champs source vers ACP
- Génération du JSON ACP prêt à pusher
- Plan d'action priorisé (P1/P2/P3)
- Checklist Checkout readiness (cadrage)

## Installation

```bash
pip install -r requirements.txt
streamlit run app.py
```

L'application sera accessible sur http://localhost:8501

## Les 4 étapes

### 1. Upload & Détection
- Formats supportés : **XML** (Google Merchant Center), **JSON** (Shopify, ACP), **CSV/TSV**
- Auto-détection du format et résumé des champs disponibles

### 2. Mapping vers ACP
- Presets pré-configurés (GMC → ACP, Shopify → ACP)
- Mapping visuel avec sélecteurs et transformations
- Preview en temps réel de la couverture

### 3. JSON ACP + Plan d'action
- Génération du feed ACP Feed API 2026-04-17 complet
- Download du JSON prêt à pusher
- Plan d'action priorisé :
  - **P1** : Indispensable pour PoC ACP (id, title, price, availability)
  - **P2** : Améliore la discovery (description, media, categories)
  - **P3** : Nice to have (seller, list_price, variant_options)

### 4. Checklist Checkout Readiness
- Cadrage PSP (Stripe, Adyen, Checkout.com)
- Checklist des 5 endpoints ACP Checkout
- Capabilities & sécurité

## ACP Feed API 2026-04-17

| Layer | Champs | Obligation |
|-------|--------|-----------|
| Product | `id`, `title` | Required |
| Product | `description`, `url`, `media` | Recommended |
| Variant | `id`, `price`, `availability` | Required |
| Variant | `title`, `categories`, `seller`, `variant_options`, `condition` | Recommended |

## Architecture

```
ACP Readiness/
├── app.py                 # Entry point Streamlit
├── core/
│   ├── models.py          # Dataclasses (ACPProduct, ACPVariant, MappingRule)
│   ├── parser.py          # Multi-format feed parser
│   ├── mapper.py          # Mapping engine avec transforms
│   ├── generator.py       # ACP JSON feed generator
│   └── analyzer.py        # Gap analysis + action plan
├── ui/
│   ├── step_upload.py     # Écran 1: Upload & détection
│   ├── step_mapping.py    # Écran 2: Mapping interactif
│   ├── step_output.py     # Écran 3: JSON + plan d'action
│   └── step_checklist.py  # Écran 4: Checkout readiness
├── presets/
│   ├── gmc_to_acp.json    # Mapping GMC → ACP
│   └── shopify_to_acp.json # Mapping Shopify → ACP
├── requirements.txt
└── README.md
```

## Ressources

- [ACP Documentation](https://www.agenticcommerce.dev/docs)
- [ACP GitHub](https://github.com/agentic-commerce-protocol/agentic-commerce-protocol)
- [Stripe Agentic Commerce](https://docs.stripe.com/agentic-commerce)

## Licence

Ce projet est fourni à des fins éducatives et commerciales.
