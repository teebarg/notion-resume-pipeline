from app.schemas.resume import ResumeData, Template, TemplateVariant, TemplateId

from pathlib import Path
from typing import List, Dict, Any, Optional
from jinja2 import Environment, FileSystemLoader, select_autoescape, TemplateNotFound

TEMPLATES_DIR = Path(__file__).parent.parent / "templates" / "resume"

_env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=select_autoescape(["html"]),
)

def render_resume_html(resume: ResumeData, template_id: TemplateId = "minimal") -> str:
    template = _env.get_template(f"{template_id}.html")
    return template.render(resume=resume)


# Mocking schemas for self-contained context
TemplateId = str

class ResumeService:
    def __init__(self, templates_dir: Optional[Path] = None):
        self.templates_dir = templates_dir or (Path(__file__).parent.parent / "templates" / "resume")
        self._env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            autoescape=select_autoescape(["html"]),
        )

        # Centralized Template Registry
        # In a massive app, this could be loaded dynamically from YAML/JSON files in the template directories
        self._templates: Dict[TemplateId, Template] = {
            "minimal": Template(
                id="minimal",
                name="Minimal",
                description="Clean and simple single-column layout focusing on typography.",
                preview="minimal.png"
            ),
            "modern": Template(
                id="modern",
                name="Modern",
                description="Contemporary layout with subtle accents",
                preview="modern",
            ),
            "classic": Template(
                id="classic",
                name="Classic",
                description="Traditional format preferred by recruiters",
                preview="classic",
            ),
            "developer": Template(
                id="developer",
                name="Developer",
                description="Technical focus with skills emphasis",
                preview="developer",
            ),
            "modern-sidebar": Template(
                id="modern-sidebar",
                name="Modern Sidebar",
                description="A sleek, asymmetric two-column design optimized for impact.",
                preview="modern_sidebar.png",
                has_sidebar=True,
                variants=[
                    TemplateVariant(id="classic-slate", name="Slate", primary_color="slate-900", text_color="slate-600"),
                    TemplateVariant(id="emerald-pro", name="Emerald", primary_color="emerald-900", text_color="emerald-700")
                ]
            )
        }

    def list_templates(self) -> List[Template]:
        """Returns all available resume templates."""
        return list(self._templates.values())

    def get_template(self, template_id: TemplateId) -> Optional[Template]:
        """Retrieves metadata for a specific template."""
        return self._templates.get(template_id)

    def render(self, resume: Any, template_id: TemplateId, variant_id: Optional[str] = None) -> str:
        """
        Renders the resume HTML safely with fallback mechanics and variant overrides.
        """
        template_meta = self.get_template(template_id)
        if not template_meta:
            raise ValueError(f"Template '{template_id}' is not registered.")

        # Determine design variant tokens if passed
        variant = None
        if variant_id and template_meta.variants:
            variant = next((v for v in template_meta.variants if v.id == variant_id), template_meta.variants[0])

        try:
            template = self._env.get_template(f"{template_id}.html")
            return template.render(
                resume=resume,
                meta=template_meta,
                variant=variant
            )
        except TemplateNotFound:
            # Fallback handling or specialized alerting
            raise FileNotFoundError(f"Template file '{template_id}.html' missing from disk.")
