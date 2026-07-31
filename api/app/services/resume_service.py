from pathlib import Path
from typing import List, Dict, Any, Optional
from app.core.sample_data import get_mock_resume_data
from jinja2 import Environment, FileSystemLoader, select_autoescape, TemplateNotFound
from app.schemas.resume import ResumeData, Template, TemplateId

class ResumeService:
    def __init__(self, templates_dir: Optional[Path] = None):
        self.templates_dir = templates_dir or (Path(__file__).parent.parent / "templates" / "resume")
        self._env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            autoescape=select_autoescape(["html"]),
        )

        # Centralized Template Registry
        self._templates: Dict[TemplateId, Template] = {
            "enhance": Template(
                id="enhance",
                name="Enhance",
                description="An elegant, polished layout designed to elevate standard resumes with enhanced visual hierarchy.",
                preview="enhance.png"
            ),
             "ats-meridian": Template(
                id="ats-meridian",
                name="ATS Meridian",
                description="Strictly optimized for Applicant Tracking Systems with a clean, highly scannable single-column structure.",
                preview="ats-meridian.png"
            ),
            "minimal": Template(
                id="minimal",
                name="Minimal",
                description="A stripped-back, distraction-free single-column layout focusing purely on crisp typography and whitespace.",
                preview="minimal.png"
            ),
            "modern": Template(
                id="modern",
                name="Modern",
                description="A contemporary, stylish layout with subtle accents and a fresh aesthetic for modern industries.",
                preview="modern.png",
            ),
            "classic": Template(
                id="classic",
                name="Classic",
                description="The time-tested, traditional format preferred by conservative industries and executive recruiters.",
                preview="classic.png",
            ),
            "developer": Template(
                id="developer",
                name="Developer",
                description="A technical, data-dense layout designed to prominently feature core skills, languages, and project repositories.",
                preview="developer.png",
            ),
            "modern-canva": Template(
                id="modern-canva",
                name="Modern Canva",
                description="A premium, McKinsey-style layout engineered for senior leaders, emphasizing strategy, scale, and business outcomes.",
                preview="modern-canva.png"
            ),
        }

    def get_sample_resume(self) -> ResumeData:
        """
        Retrieves a default populated resume schema for client-side testing
        and template configuration visual workflows.
        """
        return get_mock_resume_data()

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
            raise FileNotFoundError(f"Template file '{template_id}.html' missing from disk.")
