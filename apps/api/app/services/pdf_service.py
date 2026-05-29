import asyncio
from app.services.notion_service import NotionService
from app.core.logging import get_logger
from playwright.sync_api import sync_playwright
from playwright.async_api import async_playwright
from app.schemas.resume import TemplateId
from app.services.resume_service import ResumeService

logger = get_logger(__name__)

class PDFService:
    def __init__(self, resume_service: ResumeService, notion_service: NotionService):
        self.resume_service = resume_service
        self.notion_service = notion_service

    def _html_to_pdf_sync(self, html: str) -> bytes:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.set_content(html, wait_until="networkidle")
            pdf_bytes = page.pdf(
                format="A4",
                print_background=True,
                margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
            )
            browser.close()
        return pdf_bytes

    async def _html_to_pdf(self, html: str) -> bytes:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._html_to_pdf_sync, html)

    async def generate_resume_pdf(
        self, 
        page_id: str, 
        template: TemplateId, 
        variant: str | None = None
    ) -> bytes:
        resume = await self.notion_service.get_cached_resume(page_id=page_id)
        html = self.resume_service.render(
            resume=resume, 
            template_id=template, 
            variant_id=variant
        )
        pdf_bytes = await self._html_to_pdf(html)
        return pdf_bytes
