"""Generate realistic meeting minutes for the business simulation."""

from __future__ import annotations

import logging
import random
from datetime import timedelta
from pathlib import Path
from typing import Iterable

from faker import Faker

DOCS_DIR = Path(__file__).parent / "docs"
MINUTES_DIR = DOCS_DIR / "meeting_minutes"

logger = logging.getLogger(__name__)


def _write_minutes(filepath: Path, lines: Iterable[str]) -> None:
    """Persist meeting minutes content to disk."""

    filepath.write_text("\n".join(lines), encoding="utf-8")


def generate_meeting_minutes(total_documents: int = 50) -> None:
    """Generate realistic meeting minutes documents into the docs directory."""

    fake = Faker()
    MINUTES_DIR.mkdir(exist_ok=True)

    # Meeting types and their typical topics
    meeting_types = {
        "Weekly Sales Review": [
            "sales performance",
            "pipeline updates",
            "customer feedback",
            "market trends",
            "quarterly targets",
            "lead generation",
            "competitor analysis",
            "pricing strategy",
        ],
        "Product Development": [
            "feature roadmap",
            "user testing results",
            "technical challenges",
            "release timeline",
            "bug fixes",
            "performance improvements",
            "customer requirements",
            "design updates",
        ],
        "Board Meeting": [
            "financial performance",
            "strategic initiatives",
            "market expansion",
            "risk management",
            "regulatory compliance",
            "partnership opportunities",
            "investment decisions",
            "governance",
        ],
        "Operations Review": [
            "supply chain",
            "inventory management",
            "process improvements",
            "quality control",
            "vendor relationships",
            "cost optimization",
            "capacity planning",
            "efficiency metrics",
        ],
        "HR Committee": [
            "employee satisfaction",
            "recruitment",
            "training programs",
            "performance reviews",
            "compensation",
            "company culture",
            "diversity initiatives",
            "retention strategies",
        ],
        "Marketing Strategy": [
            "campaign performance",
            "brand awareness",
            "digital marketing",
            "content strategy",
            "social media",
            "customer acquisition",
            "market research",
            "advertising budget",
        ],
        "Finance Committee": [
            "budget review",
            "cash flow",
            "financial projections",
            "cost analysis",
            "investment portfolio",
            "audit findings",
            "tax planning",
            "expense management",
        ],
    }

    departments = ["Sales", "Marketing", "Finance", "Operations", "HR", "Product", "IT"]
    action_verbs = [
        "review",
        "implement",
        "analyze",
        "optimize",
        "develop",
        "improve",
        "monitor",
        "evaluate",
    ]
    business_terms = [
        "ROI",
        "KPIs",
        "market share",
        "customer retention",
        "operational efficiency",
        "revenue growth",
        "cost reduction",
        "process improvement",
        "digital transformation",
    ]

    for i in range(total_documents):
        # Choose meeting type and related topics
        meeting_type = random.choice(list(meeting_types.keys()))
        topics = meeting_types[meeting_type]

        # Generate meeting date (last 6 months)
        meeting_date = fake.date_between(start_date="-6m", end_date="today")

        # Generate attendees (3-8 people)
        attendees = [fake.name() for _ in range(random.randint(3, 8))]
        chair = random.choice(attendees)

        # Start building the document
        content = []
        content.append(f"# {meeting_type}")
        content.append(f"**Date:** {meeting_date.strftime('%B %d, %Y')}")
        content.append(
            f"**Time:** {random.randint(9, 16)}:00 - {random.randint(10, 17)}:00"
        )
        content.append(f"**Chair:** {chair}")
        content.append(f"**Attendees:** {', '.join(attendees)}")
        content.append("")

        # Agenda items (3-6 items)
        content.append("## Agenda")
        agenda_items = random.sample(topics, random.randint(3, 6))
        for j, item in enumerate(agenda_items, 1):
            content.append(f"{j}. {item.title()}")
        content.append("")

        # Discussion points
        content.append("## Discussion Summary")

        for item in agenda_items:
            content.append(f"### {item.title()}")

            # Generate 2-4 discussion points per agenda item
            discussion_points = []
            for _ in range(random.randint(2, 4)):
                department = random.choice(departments)
                action = random.choice(action_verbs)
                term = random.choice(business_terms)

                point_templates = [
                    f"{department} team reported {random.randint(5, 25)}% improvement in {term} compared to last quarter.",
                    f"Discussion on how to {action} {term} through better coordination with {random.choice(departments)}.",
                    f"Concerns raised about {item} impact on overall {term} and customer satisfaction.",
                    f"Proposal to {action} current {item} processes by Q{random.randint(2, 4)} {random.randint(2024, 2025)}.",
                    f"{random.choice(attendees)} presented analysis showing {random.randint(10, 30)}% variance in {term}.",
                    f"Need to {action} {item} strategy to align with company's focus on {term}.",
                    f"Budget allocation of ${random.randint(10, 500)}K approved for {item} improvements.",
                ]

                discussion_points.append(random.choice(point_templates))

            for point in discussion_points:
                content.append(f"- {point}")
            content.append("")

        # Action items (2-5 items)
        content.append("## Action Items")
        for j in range(random.randint(2, 5)):
            assignee = random.choice(attendees)
            due_date = meeting_date + timedelta(days=random.randint(7, 30))
            action = random.choice(action_verbs)
            topic = random.choice(agenda_items)

            action_templates = [
                f"**{assignee}** to {action} {topic} metrics and report back by {due_date.strftime('%m/%d/%Y')}",
                f"**{assignee}** to coordinate with {random.choice(departments)} team on {topic} by {due_date.strftime('%m/%d/%Y')}",
                f"**{assignee}** to prepare {topic} proposal for next meeting ({due_date.strftime('%m/%d/%Y')})",
                f"**{assignee}** to {action} current {topic} process and present findings by {due_date.strftime('%m/%d/%Y')}",
            ]

            content.append(f"{j+1}. {random.choice(action_templates)}")

        content.append("")
        content.append("## Next Meeting")
        next_meeting_date = meeting_date + timedelta(weeks=random.randint(1, 4))
        content.append(f"**Date:** {next_meeting_date.strftime('%B %d, %Y')}")
        content.append(
            f"**Focus:** Follow-up on action items and {random.choice(topics)} review"
        )

        # Save the meeting minutes
        filename = f"meeting_{i+1:02d}_{meeting_type.lower().replace(' ', '_')}_{meeting_date.strftime('%Y%m%d')}.md"
        filepath = MINUTES_DIR / filename

        _write_minutes(filepath, content)
        logger.info("Generated meeting minutes: %s", filename)

    logger.info(
        "Generated %s meeting minutes in %s", total_documents, MINUTES_DIR
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    generate_meeting_minutes()
