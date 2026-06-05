import pytest

from app.schemas.resume import ResumeData
from app.services.resume_service import ResumeService


@pytest.fixture
def resume_service() -> ResumeService:
    return ResumeService()


def test_list_templates_returns_seven(resume_service: ResumeService) -> None:
    templates = resume_service.list_templates()
    assert len(templates) == 7
    assert all(t.preview.endswith(".png") for t in templates)


def test_get_template_known(resume_service: ResumeService) -> None:
    template = resume_service.get_template("minimal")
    assert template is not None
    assert template.id == "minimal"
    assert template.name == "Minimal"


def test_get_template_unknown(resume_service: ResumeService) -> None:
    assert resume_service.get_template("nonexistent") is None  # type: ignore[arg-type]


def test_render_minimal_includes_name(resume_service: ResumeService, sample_resume: ResumeData) -> None:
    html = resume_service.render(resume=sample_resume, template_id="minimal")
    assert "Jane Smith" in html
    assert "<" in html and ">" in html


@pytest.mark.parametrize(
    "template_id",
    ["enhance", "ats-meridian", "minimal", "modern", "classic", "developer", "modern-canva"],
)
def test_render_all_registered_templates(
    resume_service: ResumeService,
    sample_resume: ResumeData,
    template_id: str,
) -> None:
    html = resume_service.render(resume=sample_resume, template_id=template_id)  # type: ignore[arg-type]
    assert len(html) > 100
    assert "Jane Smith" in html


def test_render_unknown_template_raises(resume_service: ResumeService, sample_resume: ResumeData) -> None:
    with pytest.raises(ValueError, match="not registered"):
        resume_service.render(resume=sample_resume, template_id="unknown")  # type: ignore[arg-type]
