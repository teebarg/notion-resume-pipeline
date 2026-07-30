import secrets
from app.services.resume_service import ResumeService
from fastapi import HTTPException
from redis.asyncio import Redis
from app.schemas.share import ShareSettings, SharedResumeConfig
from app.schemas.resume import ResumeData
from app.services.notion_service import NotionService

class ShareService:
    def __init__(self, redis_client: Redis, notion_service: NotionService, resume_service: ResumeService):
        self.redis = redis_client
        self.notion_service = notion_service
        self.resume_service = resume_service

    def _get_slug_key(self, slug: str) -> str:
        return f"share:slug:{slug}"

    def _get_user_key(self, page_id: str) -> str:
        # Maps a unique Notion page_id to its active public slug
        return f"share:page:{page_id}"

    async def generate_share_link(
        self, page_id: str, base_url: str, template_id: str = "minimal", variant_id: str | None = None
    ) -> ShareSettings:
        """Generates a secure, persistent slug and sets it inside Redis."""
        # Check if they already have an active link to avoid polluting Redis keys
        user_key = self._get_user_key(page_id)
        existing_slug = await self.redis.get(user_key)
        
        if existing_slug:
            share_slug = existing_slug
        else:
            share_slug = secrets.token_urlsafe(12)

        config_payload = SharedResumeConfig(
            notion_page_id=page_id,
            template_id=template_id,
            variant_id=variant_id
        )

        # Multi-key atomic mapping using a pipeline
        async with self.redis.pipeline(transaction=True) as pipe:
            # 1. Map slug -> configuration data (No expiration time so links remain persistent)
            pipe.set(self._get_slug_key(share_slug), config_payload.model_dump_json())
            # 2. Map page_id -> slug (helps trace back or deactivate)
            pipe.set(user_key, share_slug)
            await pipe.execute()

        return ShareSettings(
            is_public=True,
            share_slug=share_slug,
            share_url=f"{base_url.rstrip('/')}/share/{share_slug}"
        )

    async def revoke_share_link(self, page_id: str) -> ShareSettings:
        """Deletes the keys from Redis, instantly deactivating the public link."""
        user_key = self._get_user_key(page_id)
        share_slug = await self.redis.get(user_key)

        if share_slug:
            async with self.redis.pipeline(transaction=True) as pipe:
                pipe.delete(self._get_slug_key(share_slug))
                pipe.delete(user_key)
                await pipe.execute()

        return ShareSettings(is_public=False, share_slug=None, share_url=None)

    async def get_resume_by_slug(self, slug: str) -> tuple[ResumeData, str, str | None]:
        """Fetches the configuration from Redis, and leverages your Notion pipeline."""
        raw_config = await self.redis.get(self._get_slug_key(slug))
        if not raw_config:
            raise HTTPException(status_code=404, detail="This shared resume link is invalid or expired.")

        config = SharedResumeConfig.model_validate_json(raw_config)
        
        # Pulls parsed document directly via your existing cache-backed pipeline
        resume_data = await self.notion_service.get_cached_resume(page_id=config.notion_page_id)
        return resume_data, config.template_id, config.variant_id