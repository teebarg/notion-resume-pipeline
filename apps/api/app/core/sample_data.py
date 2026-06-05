from app.schemas.resume import ResumeData, Basics, Experience, Project, Education, Skill

def get_mock_resume_data() -> ResumeData:
    """Returns a highly detailed realistic sample profile matching ResumeData."""
    return ResumeData(
        basics=Basics(
            name="Alex Mercer",
            title="Senior Full-Stack Engineer",
            summary="Product-focused software engineer with 6+ years of experience specializing in high-performance Python backends, FastAPI architectures, and reactive frontend frameworks. Proven track record of scaling data-intensive applications.",
            email="alex.mercer@example.com",
            location="San Francisco, CA",
            website="https://alexmercer.dev",
            linkedin="https://linkedin.com/in/alex-mercer-demo",
            github="https://github.com/alex-mercer-demo",
            phone="+1 (555) 019-2834"
        ),
        experience=[
            Experience(
                company="TechScale Systems",
                role="Senior Backend Engineer",
                location="San Francisco, CA",
                startDate="2023-01",
                endDate="",
                current=True,
                highlights=[
                    "Architected a distributed event-driven data ingestion pipeline using FastAPI and Redis, handling over 10M daily requests.",
                    "Reduced database query latency by 42% by implementing structured cache layers and optimize database indexing.",
                    "Mentored 4 junior engineers and introduced strict code-review guidelines to boost codebase test coverage to 90%."
                ],
                stack=["Python", "FastAPI", "Redis", "PostgreSQL", "Docker", "AWS"]
            ),
            Experience(
                company="CloudSync Corp",
                role="Software Engineer II",
                location="Remote",
                startDate="2020-06",
                endDate="2022-12",
                current=False,
                highlights=[
                    "Designed and maintained core microservices responsible for syncing real-time collaborative document spaces.",
                    "Migrated a monolithic legacy application to a clean hexagonal service architecture, speeding up deployment velocity by 30%."
                ],
                stack=["Python", "Django", "Celery", "RabbitMQ", "React", "TypeScript"]
            )
        ],
        projects=[
            Project(
                name="FastCache Extra",
                description="An open-source performance monitoring plugin for ASGI frameworks providing localized stampede-protection and automatic cache-invalidation tags.",
                highlights=[
                    "Gained over 800 github stars and helped developers isolate cache stampedes in multi-tenant environments."
                ],
                stack=["Python", "FastAPI", "Redis", "Pytest"],
                link="https://github.com/example/fastcache-extra"
            )
        ],
        education=[
            Education(
                degree="Bachelor of Science",
                field="Computer Science",
                institution="State University",
                startDate="2016-09",
                endDate="2020-05"
            )
        ],
        skills=[
            Skill(name="Languages", stack=["Python", "TypeScript", "JavaScript", "SQL", "HTML/CSS"]),
            Skill(name="Frameworks & Tools", stack=["FastAPI", "Django", "React", "Next.js", "Node.js", "Docker", "TailwindCSS"]),
            Skill(name="Databases & Caching", stack=["PostgreSQL", "Redis", "MongoDB", "RabbitMQ"])
        ]
    )