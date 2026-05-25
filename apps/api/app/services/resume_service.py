from app.schemas.resume import Template, TemplateId

from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape
from app.schemas.resume import ResumeData, TemplateId

TEMPLATES_DIR = Path(__file__).parent.parent / "templates" / "resume"

_env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=select_autoescape(["html"]),
)

def render_resume_html(resume: ResumeData, template_id: TemplateId = "minimal") -> str:
    template = _env.get_template(f"{template_id}.html")
    return template.render(resume=resume)


class ResumeService:
    TEMPLATES: list[Template] = [
        Template(
            id="minimal",
            name="Minimal",
            description="Clean and simple design with focus on content",
            preview="minimal",
        ),
        Template(
            id="modern",
            name="Modern",
            description="Contemporary layout with subtle accents",
            preview="modern",
        ),
        Template(
            id="classic",
            name="Classic",
            description="Traditional format preferred by recruiters",
            preview="classic",
        ),
        Template(
            id="developer",
            name="Developer",
            description="Technical focus with skills emphasis",
            preview="developer",
        ),
    ]

    def list_templates(self) -> list[Template]:
        return list(self.TEMPLATES)

    def get_template(self, template_id: TemplateId) -> Template | None:
        return next((t for t in self.TEMPLATES if t.id == template_id), None)
