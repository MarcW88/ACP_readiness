from typing import Dict, List, Any
from .models import ACPProduct, ACPVariant, Gap, ActionItem, MigrationReport


class MigrationAnalyzer:
    """Analyze migration readiness and generate action plans"""

    def analyze(self, products: List[ACPProduct]) -> MigrationReport:
        """Run full migration analysis"""
        if not products:
            return MigrationReport()

        total_products = len(products)
        total_variants = sum(len(p.variants) for p in products)

        gaps = self._find_gaps(products)
        action_plan = self._prioritize(gaps, total_products)

        required_gaps = [g for g in gaps if g.severity == "required"]
        recommended_gaps = [g for g in gaps if g.severity == "recommended"]

        required_coverage = 1.0 - (
            sum(1 - g.coverage for g in required_gaps) / len(required_gaps)
            if required_gaps else 0
        )
        recommended_coverage = 1.0 - (
            sum(1 - g.coverage for g in recommended_gaps) / len(recommended_gaps)
            if recommended_gaps else 0
        )

        # Readiness score: 70% required + 30% recommended
        readiness_score = round(required_coverage * 70 + recommended_coverage * 30, 1)

        return MigrationReport(
            total_products=total_products,
            total_variants=total_variants,
            required_coverage=round(required_coverage * 100, 1),
            recommended_coverage=round(recommended_coverage * 100, 1),
            gaps=gaps,
            action_plan=action_plan,
            readiness_score=readiness_score,
        )

    def _find_gaps(self, products: List[ACPProduct]) -> List[Gap]:
        """Find all gaps in ACP field coverage"""
        gaps = []
        total = len(products)
        if total == 0:
            return gaps

        # Product required fields
        product_required = {
            "product.id": lambda p: bool(p.id),
            "product.title": lambda p: bool(p.title),
        }

        # Product recommended fields
        product_recommended = {
            "product.description": lambda p: bool(p.description),
            "product.url": lambda p: bool(p.url),
            "product.media": lambda p: bool(p.media),
        }

        # Variant required fields
        variant_required = {
            "variant.id": lambda p: any(bool(v.id) for v in p.variants) if p.variants else False,
            "variant.price": lambda p: any(bool(v.price) for v in p.variants) if p.variants else False,
            "variant.availability": lambda p: any(bool(v.availability) for v in p.variants) if p.variants else False,
        }

        # Variant recommended fields
        variant_recommended = {
            "variant.title": lambda p: any(bool(v.title) for v in p.variants) if p.variants else False,
            "variant.description": lambda p: any(bool(v.description) for v in p.variants) if p.variants else False,
            "variant.url": lambda p: any(bool(v.url) for v in p.variants) if p.variants else False,
            "variant.media": lambda p: any(bool(v.media) for v in p.variants) if p.variants else False,
            "variant.list_price": lambda p: any(bool(v.list_price) for v in p.variants) if p.variants else False,
            "variant.categories": lambda p: any(bool(v.categories) for v in p.variants) if p.variants else False,
            "variant.condition": lambda p: any(bool(v.condition) for v in p.variants) if p.variants else False,
            "variant.variant_options": lambda p: any(bool(v.variant_options) for v in p.variants) if p.variants else False,
            "variant.seller": lambda p: any(bool(v.seller) for v in p.variants) if p.variants else False,
        }

        for field_name, check_fn in product_required.items():
            coverage = sum(1 for p in products if check_fn(p)) / total
            if coverage < 1.0:
                gaps.append(Gap(
                    acp_field=field_name,
                    severity="required",
                    coverage=round(coverage, 3),
                    source_available=coverage > 0,
                    suggestion=self._suggest_fix(field_name, coverage)
                ))

        for field_name, check_fn in product_recommended.items():
            coverage = sum(1 for p in products if check_fn(p)) / total
            if coverage < 1.0:
                gaps.append(Gap(
                    acp_field=field_name,
                    severity="recommended",
                    coverage=round(coverage, 3),
                    source_available=coverage > 0,
                    suggestion=self._suggest_fix(field_name, coverage)
                ))

        for field_name, check_fn in variant_required.items():
            coverage = sum(1 for p in products if check_fn(p)) / total
            if coverage < 1.0:
                gaps.append(Gap(
                    acp_field=field_name,
                    severity="required",
                    coverage=round(coverage, 3),
                    source_available=coverage > 0,
                    suggestion=self._suggest_fix(field_name, coverage)
                ))

        for field_name, check_fn in variant_recommended.items():
            coverage = sum(1 for p in products if check_fn(p)) / total
            if coverage < 1.0:
                gaps.append(Gap(
                    acp_field=field_name,
                    severity="recommended",
                    coverage=round(coverage, 3),
                    source_available=coverage > 0,
                    suggestion=self._suggest_fix(field_name, coverage)
                ))

        return sorted(gaps, key=lambda g: (0 if g.severity == "required" else 1, g.coverage))

    def _suggest_fix(self, field_name: str, coverage: float) -> str:
        """Generate a suggestion for fixing a gap"""
        suggestions = {
            "product.id": "Vérifiez que chaque produit a un identifiant unique et stable.",
            "product.title": "Ajoutez un titre descriptif à chaque produit.",
            "product.description": "Enrichissez vos descriptions pour une meilleure découvrabilité par les agents IA.",
            "product.url": "Ajoutez l'URL canonique de chaque produit.",
            "product.media": "Ajoutez au minimum une image par produit (URL directe).",
            "variant.id": "Chaque variante doit avoir un ID unique pour le checkout.",
            "variant.price": "Le prix est obligatoire pour le checkout agent.",
            "variant.availability": "Indiquez le statut de disponibilité (in_stock, out_of_stock).",
            "variant.title": "Utile pour les agents qui présentent des options au buyer.",
            "variant.description": "Description spécifique à la variante pour contexte.",
            "variant.url": "URL spécifique à la variante si différente du produit.",
            "variant.media": "Image spécifique à la variante (couleur, taille…).",
            "variant.list_price": "Prix barré / prix de référence pour afficher les promotions.",
            "variant.categories": "Catégories pour le filtrage et la découverte par agent.",
            "variant.condition": "État de l'article (new, used, refurbished).",
            "variant.variant_options": "Options de variante (taille, couleur) pour la sélection.",
            "variant.seller": "Infos vendeur (nom, URL) pour le contexte marketplace.",
        }
        base = suggestions.get(field_name, f"Complétez le champ {field_name}.")
        if 0 < coverage < 1.0:
            base += f" Actuellement rempli à {coverage*100:.0f}%."
        return base

    def _prioritize(self, gaps: List[Gap], total_products: int) -> List[ActionItem]:
        """Generate prioritized action plan from gaps"""
        actions = []

        # P1: Required fields with low coverage
        p1_gaps = [g for g in gaps if g.severity == "required" and g.coverage < 0.95]
        for g in p1_gaps:
            actions.append(ActionItem(
                priority="P1",
                field=g.acp_field,
                action=f"Ajouter {g.acp_field}" if g.coverage == 0 else f"Compléter {g.acp_field}",
                effort="low" if g.source_available else "medium",
                impact="critical",
                description=g.suggestion
            ))

        # P2: Recommended fields that improve discovery
        discovery_fields = ["product.description", "product.media", "variant.categories", "variant.variant_options"]
        p2_gaps = [g for g in gaps if g.acp_field in discovery_fields and g.coverage < 0.8]
        for g in p2_gaps:
            actions.append(ActionItem(
                priority="P2",
                field=g.acp_field,
                action=f"Enrichir {g.acp_field}",
                effort="medium",
                impact="high",
                description=g.suggestion
            ))

        # P3: Nice-to-have recommended fields
        p3_fields = ["variant.list_price", "variant.seller", "variant.condition", "variant.url", "variant.media"]
        p3_gaps = [g for g in gaps if g.acp_field in p3_fields and g.coverage < 0.5]
        for g in p3_gaps:
            actions.append(ActionItem(
                priority="P3",
                field=g.acp_field,
                action=f"Ajouter {g.acp_field}",
                effort="low" if g.source_available else "high",
                impact="medium",
                description=g.suggestion
            ))

        return actions

    def get_readiness_summary(self, report: MigrationReport) -> Dict[str, Any]:
        """Generate a human-readable readiness summary"""
        if report.readiness_score >= 80:
            status = "ready"
            message = "Votre feed est prêt pour un PoC ACP Feed API."
        elif report.readiness_score >= 50:
            status = "partial"
            message = "Votre feed nécessite quelques ajustements avant un PoC ACP."
        else:
            status = "not_ready"
            message = "Votre feed a besoin d'un travail significatif pour ACP."

        p1_count = len([a for a in report.action_plan if a.priority == "P1"])
        p2_count = len([a for a in report.action_plan if a.priority == "P2"])
        p3_count = len([a for a in report.action_plan if a.priority == "P3"])

        return {
            "status": status,
            "message": message,
            "score": report.readiness_score,
            "required_coverage": report.required_coverage,
            "recommended_coverage": report.recommended_coverage,
            "actions": {"P1": p1_count, "P2": p2_count, "P3": p3_count},
            "total_products": report.total_products,
            "total_variants": report.total_variants,
        }
