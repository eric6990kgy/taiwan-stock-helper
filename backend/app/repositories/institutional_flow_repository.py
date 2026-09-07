from app.models.institutional_flow import InstitutionalFlow
from app.repositories.asset_date_repository import AssetDateRepository


class InstitutionalFlowRepository(AssetDateRepository[InstitutionalFlow]):
    model = InstitutionalFlow
