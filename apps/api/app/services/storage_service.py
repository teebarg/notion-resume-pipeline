from app.config import settings
from app.core.logging import get_logger
from supabase import AsyncClient, create_client

logger = get_logger(__name__)

class StorageService:
    def __init__(self):
        if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
            logger.warning("Supabase credentials missing. PDF synchronization will fail.")
        self.supabase: AsyncClient = create_client(
            settings.SUPABASE_URL, 
            settings.SUPABASE_SERVICE_ROLE_KEY
        )
        self.bucket_name = settings.SUPABASE_BUCKET_NAME

    async def upload_resume_pdf(self, page_id: str, pdf_bytes: bytes) -> str:
        """
        Uploads or overwrites the resume PDF file in Supabase storage bucket.
        Returns the public download/view link.
        """
        file_path = f"{page_id}/resume.pdf"
        
        try:
            # 'x-upsert': 'true' ensures existing files are rewritten instantly
            self.supabase.storage.from_(self.bucket_name).upload(
                path=file_path,
                file=pdf_bytes,
                file_options={"content-type": "application/pdf", "x-upsert": "true"}
            )
            logger.info(f"Successfully uploaded PDF to Supabase storage for page: {page_id}")
        except Exception as e:
            if "already exists" in str(e).lower():
                self.supabase.storage.from_(self.bucket_name).update(
                    path=file_path,
                    file=pdf_bytes,
                    file_options={"content-type": "application/pdf"}
                )
                logger.info(f"Successfully updated existing PDF in Supabase storage for page: {page_id}")
            else:
                logger.error(f"Failed to push PDF to Supabase storage: {e}", exc_info=True)
                raise e

        public_url = f"{settings.SUPABASE_URL}/storage/v1/object/public/{self.bucket_name}/{file_path}"
        return public_url