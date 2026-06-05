import json

from app.schemas.notion import NotionImportRequest, NotionImportResponse
from app.schemas.resume import Basics, Experience, ResumeData, Skill


def test_resume_data_defaults() -> None:
    resume = ResumeData()
    assert resume.basics.name == ""
    assert resume.experience == []
    assert resume.education == []
    assert resume.skills == []
    assert resume.projects == []


def test_resume_data_json_roundtrip(sample_resume: ResumeData) -> None:
    payload = sample_resume.model_dump(mode="json")
    restored = ResumeData.model_validate(payload)
    assert restored.basics.name == sample_resume.basics.name
    assert restored.experience[0].company == sample_resume.experience[0].company
    assert restored.skills[0].stack == sample_resume.skills[0].stack


def test_resume_data_serializes_to_json_string(sample_resume: ResumeData) -> None:
    raw = sample_resume.model_dump_json()
    parsed = json.loads(raw)
    assert parsed["basics"]["name"] == "Jane Smith"
    assert parsed["experience"][0]["highlights"] == ["Led API redesign"]


def test_notion_import_request_normalizes_bare_id() -> None:
    req = NotionImportRequest(page_id="a1b2c3d4e5f6789012345678abcdef01")
    assert req.page_id == "a1b2c3d4-e5f6-7890-1234-5678abcdef01"


def test_notion_import_request_normalizes_notion_url() -> None:
    req = NotionImportRequest(
        page_id="https://www.notion.so/My-Resume-a1b2c3d4e5f6789012345678abcdef01"
    )
    assert req.page_id == "a1b2c3d4-e5f6-7890-1234-5678abcdef01"


def test_notion_import_response_shape(sample_resume: ResumeData) -> None:
    response = NotionImportResponse(
        page_id="test-page",
        message="ok",
        resume=sample_resume,
    )
    data = response.model_dump(mode="json")
    assert data["page_id"] == "test-page"
    assert data["resume"]["basics"]["email"] == "jane@example.com"


def test_skill_model_accepts_named_categories() -> None:
    resume = ResumeData(skills=[Skill(name="Backend", stack=["Python"])])
    assert resume.skills[0].name == "Backend"
    assert resume.skills[0].stack == ["Python"]
