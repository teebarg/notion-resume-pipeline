from pydantic import BaseModel
from app.schemas.resume import TemplateId

class ShareSettings(BaseModel):
    is_public: bool
    share_slug: str | None = None
    share_url: str | None = None

class SharedResumeConfig(BaseModel):
    notion_page_id: str
    template_id: TemplateId = "minimal"
    variant_id: str | None = None