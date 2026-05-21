from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any


@dataclass
class ACPVariant:
    """ACP Feed API 2026-04-17 Variant model"""
    id: str
    price: str
    availability: str
    title: Optional[str] = None
    description: Optional[str] = None
    url: Optional[str] = None
    media: Optional[List[str]] = None
    list_price: Optional[str] = None
    categories: Optional[List[str]] = None
    condition: Optional[str] = None
    variant_options: Optional[Dict[str, str]] = None
    seller: Optional[Dict[str, str]] = None

    def to_dict(self) -> Dict[str, Any]:
        d = {}
        for k, v in self.__dict__.items():
            if v is not None:
                d[k] = v
        return d

    def get_missing_required(self) -> List[str]:
        missing = []
        if not self.id:
            missing.append("variant.id")
        if not self.price:
            missing.append("variant.price")
        if not self.availability:
            missing.append("variant.availability")
        return missing

    def get_missing_recommended(self) -> List[str]:
        missing = []
        recommended = ["title", "description", "url", "media", "list_price",
                       "categories", "condition", "variant_options", "seller"]
        for f in recommended:
            if getattr(self, f) is None:
                missing.append(f"variant.{f}")
        return missing


@dataclass
class ACPProduct:
    """ACP Feed API 2026-04-17 Product model"""
    id: str
    title: str
    description: Optional[str] = None
    url: Optional[str] = None
    media: Optional[List[str]] = None
    variants: List[ACPVariant] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        d = {}
        for k, v in self.__dict__.items():
            if k == "variants":
                if v:
                    d["variants"] = [var.to_dict() for var in v]
            elif v is not None:
                d[k] = v
        return d

    def get_missing_required(self) -> List[str]:
        missing = []
        if not self.id:
            missing.append("product.id")
        if not self.title:
            missing.append("product.title")
        return missing

    def get_missing_recommended(self) -> List[str]:
        missing = []
        if not self.description:
            missing.append("product.description")
        if not self.url:
            missing.append("product.url")
        if not self.media:
            missing.append("product.media")
        return missing


@dataclass
class MappingRule:
    """A rule mapping a source field to an ACP field"""
    acp_field: str
    source_field: Optional[str] = None
    transform: str = "direct"
    params: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        d = {"acp_field": self.acp_field, "source_field": self.source_field, "transform": self.transform}
        if self.params:
            d["params"] = self.params
        return d


@dataclass
class ParseResult:
    """Result of parsing a feed file"""
    products: List[Dict[str, Any]]
    format: str  # "gmc_xml", "shopify_json", "csv", "unknown"
    total_products: int = 0
    available_fields: Dict[str, float] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        self.total_products = len(self.products)


@dataclass
class Gap:
    """A missing or incomplete field in the migration"""
    acp_field: str
    severity: str  # "required", "recommended"
    coverage: float  # 0.0 to 1.0
    source_available: bool
    suggestion: str = ""


@dataclass
class ActionItem:
    """A prioritized action for migration"""
    priority: str  # "P1", "P2", "P3"
    field: str
    action: str
    effort: str  # "low", "medium", "high"
    impact: str  # "critical", "high", "medium", "low"
    description: str = ""


@dataclass
class MigrationReport:
    """Complete migration analysis report"""
    total_products: int = 0
    total_variants: int = 0
    required_coverage: float = 0.0
    recommended_coverage: float = 0.0
    gaps: List[Gap] = field(default_factory=list)
    action_plan: List[ActionItem] = field(default_factory=list)
    readiness_score: float = 0.0
