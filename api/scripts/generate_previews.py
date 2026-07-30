#!/usr/bin/env python
import argparse
import asyncio
import logging
import sys
from pathlib import Path
from app.services.resume_service import ResumeService
from playwright.async_api import async_playwright
from app.schemas.resume import ResumeData

# Setup basic logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Mock data to cleanly populate your templates during the snapshot process
MOCK_RESUME_DATA = {
    "basics": {
        "name": "Alex Morgan",
        "title": "Senior Staff Software Engineer",
        "email": "alex.morgan@dev.io",
        "phone": "+1 (555) 019-2834",
        "location": "San Francisco, CA",
        "summary": "Architectural leader with 8+ years of experience designing scalable distributed systems. Specialized in Python, TypeScript, and high-performance caching strategies. Passionate about clean code and developer tooling systems.",
        "website" : "https://portfolio.dev.io",
        "linkedin" : "https://www.linkedin.com/in/alex-b46724ba/",
        "github":  "https://github.com/alex"
    },
    "experience": [
        {
            "company": "CloudScale Systems",
            "role": "Tech Lead",
            "location": "EL Paso, Texas",
            "startDate": "2022-03",
            "endDate": "Present",
            "description": "Led an engineering team of 6 to rebuild core streaming pipelines, reducing overall compute costs by 35%. Implemented distributed caching mechanisms handling 50k+ requests per second.",
            "highlights": [
                "Built and maintained a customer-facing web application using React, Node.js, PostgreSQL, and AWS.",
                "Designed and implemented RESTful APIs to support mobile and web clients with consistent sub-200ms response times.",
                "Implemented caching strategies and database query optimizations to improve application throughput under load.",
                "Developed automated data processing pipelines to handle ingestion and transformation of large datasets.",
                "Built internal dashboards and admin tools for reporting, user management, and operational workflows.",
                "Integrated third-party services including payment gateways, email providers, and analytics platforms.",
                "Collaborated with cross-functional teams to deliver features across the full stack in an agile environment.",
                "Wrote unit and integration tests to maintain code quality and reduce regression risk.",
                "Contributed to system design discussions and technical documentation for key platform components."
            ]
        },
        {
            "company": "CoreTech Labs",
            "role": "Software Engineer II",
            "location": "NY, New York",
            "startDate": "2019-06",
            "endDate": "2022-02",
            "description": "Maintained internal developer APIs and optimized SQL queries, improving interface rendering times across consumer dashboards by 400ms.",
            "highlights": [
                "Worked on a scalable digital marketplace platform using modern web technologies including TypeScript, Python, PostgreSQL, and Redis.",
                "Built responsive product catalog and search experiences focused on performance and mobile usability.",
                "Implemented caching and backend optimizations to improve application speed and reduce server load.",
                "Developed intelligent automation tools for customer engagement and workflow assistance using AI-powered systems.",
                "Created bulk data import/export pipelines for managing large datasets efficiently.",
                "Built internal dashboards and management tools for operations, reporting, and inventory tracking.",
                "Integrated advanced search and filtering capabilities to improve product discovery.",
                "Designed background processing systems for notifications, indexing, and scheduled tasks.",
                "Improved frontend performance through server-side rendering, efficient data fetching, and lazy loading techniques."
            ]
        }
    ],
    "education": [
        {
            "institution": "University of Computing",
            "degree": "B.S. in Computer Science",
            "startDate": "2015",
            "endDate": "2019"
        }
    ],
    "skills": [
        {"name": "Frontend", "stack": ["TypeScript", "React"]},
        {"name": "Backend", "stack": ["Python", "FastAPI", "Redis", "Docker", "PostgreSQL", "System Design"]}
    ],
    "projects": [
        {
            "name": "Electric Vehicles",
            "description": "Full plug-in electric vehicles using cutting edge technology",
            "stack": ["Python", "FastAPI", "Redis", "Docker", "PostgreSQL", "System Design"],
            "link": ""
        },
         {
            "name": "AI Sales & Lead Qualification Platform",
            "description": "AI-driven sales automation platform for customer engagement, lead qualification, and intelligent scoring. Integrated LLM APIs for lead classification and scoring. Built conversational workflows for automated customer interactions. Developed backend APIs and data processing pipelines for sales workflows. Implemented lead scoring and analytics systems. Designed extensible architecture for future AI workflow expansion.",
            "stack": [],
            "link": None
        }
    ],
}


async def generate_template_snapshots(output_dir: Path, target_template: str | None = None):
    """Launches a headless browser to render HTML templates to static PNG snapshots."""
    resume_service = ResumeService()
    templates = resume_service.list_templates()
    
    validated_mock_data = ResumeData(**MOCK_RESUME_DATA)
    
    # Filter if user explicitly targeted one layout style
    if target_template:
        templates = [t for t in templates if t.id == target_template]
        if not templates:
            logger.error(f"Template '{target_template}' not found in registry.")
            sys.exit(1)

    # Ensure target output directory exists on disk
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"Starting snapshot generation engine for {len(templates)} layout profiles...")

    # Spin up Playwright context
    async with async_playwright() as p:
        # Launch headless browser instance
        browser = await p.chromium.launch(headless=True)
        
        # Define viewport matching standard A4 aspect ratio proportions (800x1130 px)
        context = await browser.new_context(
            viewport={"width": 800, "height": 1130},
            device_scale_factor=2  # High-DPI/Retina scale factor for ultra-sharp rendering
        )
        page = await context.new_page()

        for template_meta in templates:
            output_file = output_dir / f"{template_meta.id}.png"
            logger.info(f"Rendering blueprint canvas: [{template_meta.name}] -> {output_file.name}")
            
            try:
                html_content = resume_service.render(resume=validated_mock_data, template_id=template_meta.id)
                
                # Inject raw HTML string straight into the headless page DOM context
                await page.set_content(html_content)
                
                # Wait briefly for web fonts or dynamic layouts to structurally settle
                await page.wait_for_load_state("networkidle")
                
                # Take screenshot of the top half / full view
                await page.screenshot(
                    path=str(output_file),
                    type="png",
                    full_page=False # Keeps it constrained to viewport boundaries
                )
                logger.info(f"✅ Successfully captured snapshot for context: {template_meta.id}")
                
            except Exception as e:
                logger.error(f"❌ Failed rendering step for template '{template_meta.id}': {e}")

        await browser.close()
    logger.info("Process complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Automated Headless Blueprint Generator Engine.")
    parser.add_argument(
        "--output", 
        type=str, 
        default=str(Path(__file__).parent.parent / "app" / "static" / "previews"),
        help="Target output directory path for the generated PNG files."
    )
    parser.add_argument(
        "--template", 
        type=str, 
        default=None, 
        help="Optional: target a specific layout profile ID exclusively."
    )
    
    args = parser.parse_args()
    
    # Run the async loop engine cleanly
    asyncio.run(generate_template_snapshots(Path(args.output), args.template))