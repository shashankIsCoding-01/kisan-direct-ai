from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class MetricValue(BaseModel):
    value: int | float | Decimal | None
    unit: str | None = None
    source: str
    calculation: str


class AnalyticsDashboardResponse(BaseModel):
    actual: dict[str, MetricValue]
    demo: dict[str, MetricValue]
    estimates: dict[str, MetricValue]
    generated_at: str
    limitations: list[str]


class AnalyticsDefinitionsResponse(BaseModel):
    definitions: dict[str, str]
