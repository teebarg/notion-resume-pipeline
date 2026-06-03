from pathlib import Path
from typing import List, Dict, Any, Optional
from jinja2 import Environment, FileSystemLoader, select_autoescape, TemplateNotFound
from app.schemas.resume import ResumeData, Template, TemplateVariant, TemplateId

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
            "enhance": Template(
                id="enhance",
                name="Enhance",
                description="Clean and simple single-column layout focusing on typography.",
                preview="enhance.png"
            ),
             "ats-resume": Template(
                id="ats-resume",
                name="ATS Resume",
                description="Clean and simple single-column layout focusing on typography.",
                preview="ats-resume.png"
            ),
            "product-focused": Template(
                id="product-focused",
                name="Product Focused",
                description="Clean and simple single-column layout focusing on typography.",
                preview="product-focused.png"
            ),
            "engineer": Template(
                id="engineer",
                name="Engineer Resume",
                description="Clean and simple single-column layout focusing on typography.",
                preview="engineer.png"
            ),
            "meridian": Template(
                id="meridian",
                name="Meridian",
                description="Clean and simple single-column layout focusing on typography.",
                preview="meridian.png"
            ),
             "ats-meridian": Template(
                id="ats-meridian",
                name="ATS Meridian",
                description="Clean and simple single-column layout focusing on typography.",
                preview="ats-meridian.png"
            ),
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
                preview="modern.png",
            ),
            "classic": Template(
                id="classic",
                name="Classic",
                description="Traditional format preferred by recruiters",
                preview="classic.png",
            ),
            "developer-focus": Template(
                id="developer-focus",
                name="Developer Focus",
                description="Technical focus with skills emphasis",
                preview="developer-focus.png",
            ),
            "developer": Template(
                id="developer",
                name="Developer",
                description="Technical focus with skills emphasis",
                preview="developer.png",
            ),
            "executive": Template(
                id="executive",
                name="Executive Briefing",
                description="A premium, McKinsey-style layout engineered for senior leaders, emphasizing strategy, scale, and business outcomes.",
                preview="executive.png"
            ),
            "modern-canva": Template(
                id="modern-canva",
                name="Modern Canva",
                description="A premium, McKinsey-style layout engineered for senior leaders, emphasizing strategy, scale, and business outcomes.",
                preview="modern-canva.png"
            ),
             "bento-dark": Template(
                id="bento-dark",
                name="Bento Dark",
                description="A premium, McKinsey-style layout engineered for senior leaders, emphasizing strategy, scale, and business outcomes.",
                preview="bento-dark.png"
            ),
            "geometric-edge": Template(
                id="geometric-edge",
                name="Geometric Edge",
                description="A premium, McKinsey-style layout engineered for senior leaders, emphasizing strategy, scale, and business outcomes.",
                preview="geometric-edge.png"
            ),
            "split-onyx": Template(
                id="split-onyx",
                name="Split Onyx",
                description="A premium, McKinsey-style layout engineered for senior leaders, emphasizing strategy, scale, and business outcomes.",
                preview="split-onyx.png"
            ),
            "minimal-geometric-split": Template(
                id="minimal-geometric-split",
                name="Minimal Geometric Split",
                description="A premium, McKinsey-style layout engineered for senior leaders, emphasizing strategy, scale, and business outcomes.",
                preview="minimal-geometric-split.png"
            ),
            "modern-sidebar": Template(
                id="modern-sidebar",
                name="Modern Sidebar",
                description="A sleek, asymmetric two-column design optimized for impact.",
                preview="modern-sidebar.png",
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
