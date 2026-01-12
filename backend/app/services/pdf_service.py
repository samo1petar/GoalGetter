"""
PDF generation service for exporting goals.
Uses ReportLab for PDF generation.
"""
import io
import re
from typing import Dict, Any, Optional
from datetime import datetime
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor, black, gray
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
    PageBreak,
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
import logging

logger = logging.getLogger(__name__)


class PDFService:
    """Service for generating PDF documents from goals."""

    # Brand colors
    PRIMARY_COLOR = HexColor("#4F46E5")  # Indigo
    SECONDARY_COLOR = HexColor("#059669")  # Emerald
    ACCENT_COLOR = HexColor("#DC2626")  # Red
    TEXT_COLOR = HexColor("#1F2937")  # Gray 800
    MUTED_COLOR = HexColor("#6B7280")  # Gray 500

    def __init__(self):
        """Initialize PDF service with custom styles."""
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()

    def _setup_custom_styles(self):
        """Setup custom paragraph styles."""
        # Title style
        self.styles.add(ParagraphStyle(
            name='GoalTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=self.PRIMARY_COLOR,
            spaceAfter=12,
            alignment=TA_CENTER,
        ))

        # Subtitle style
        self.styles.add(ParagraphStyle(
            name='GoalSubtitle',
            parent=self.styles['Normal'],
            fontSize=12,
            textColor=self.MUTED_COLOR,
            spaceAfter=20,
            alignment=TA_CENTER,
        ))

        # Section heading style
        self.styles.add(ParagraphStyle(
            name='SectionHeading',
            parent=self.styles['Heading2'],
            fontSize=14,
            textColor=self.PRIMARY_COLOR,
            spaceBefore=16,
            spaceAfter=8,
            borderPadding=(0, 0, 4, 0),
        ))

        # Body text style
        self.styles.add(ParagraphStyle(
            name='GoalBody',
            parent=self.styles['Normal'],
            fontSize=11,
            textColor=self.TEXT_COLOR,
            spaceAfter=12,
            alignment=TA_JUSTIFY,
            leading=16,
        ))

        # Metadata label style
        self.styles.add(ParagraphStyle(
            name='MetaLabel',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=self.MUTED_COLOR,
            spaceBefore=4,
            spaceAfter=2,
        ))

        # Metadata value style
        self.styles.add(ParagraphStyle(
            name='MetaValue',
            parent=self.styles['Normal'],
            fontSize=11,
            textColor=self.TEXT_COLOR,
            spaceAfter=8,
        ))

        # Milestone style
        self.styles.add(ParagraphStyle(
            name='MilestoneItem',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=self.TEXT_COLOR,
            leftIndent=20,
            spaceAfter=6,
        ))

        # Tag style
        self.styles.add(ParagraphStyle(
            name='TagStyle',
            parent=self.styles['Normal'],
            fontSize=9,
            textColor=self.SECONDARY_COLOR,
        ))

        # Footer style
        self.styles.add(ParagraphStyle(
            name='Footer',
            parent=self.styles['Normal'],
            fontSize=8,
            textColor=self.MUTED_COLOR,
            alignment=TA_CENTER,
        ))

    def _markdown_to_paragraphs(self, content: str) -> list:
        """
        Convert markdown content to ReportLab paragraphs.
        Handles basic markdown syntax.
        """
        elements = []

        if not content:
            return elements

        lines = content.split('\n')
        current_paragraph = []

        for line in lines:
            stripped_line = line.strip()

            # Empty line - flush current paragraph
            if not stripped_line:
                if current_paragraph:
                    para_text = ' '.join(current_paragraph)
                    elements.append(Paragraph(para_text, self.styles['GoalBody']))
                    current_paragraph = []
                continue

            # Heading 1 (#)
            if stripped_line.startswith('# '):
                if current_paragraph:
                    para_text = ' '.join(current_paragraph)
                    elements.append(Paragraph(para_text, self.styles['GoalBody']))
                    current_paragraph = []
                heading_text = stripped_line[2:]
                elements.append(Paragraph(heading_text, self.styles['SectionHeading']))
                continue

            # Heading 2 (##)
            if stripped_line.startswith('## '):
                if current_paragraph:
                    para_text = ' '.join(current_paragraph)
                    elements.append(Paragraph(para_text, self.styles['GoalBody']))
                    current_paragraph = []
                heading_text = stripped_line[3:]
                elements.append(Spacer(1, 8))
                elements.append(Paragraph(f"<b>{heading_text}</b>", self.styles['GoalBody']))
                continue

            # Heading 3 (###)
            if stripped_line.startswith('### '):
                if current_paragraph:
                    para_text = ' '.join(current_paragraph)
                    elements.append(Paragraph(para_text, self.styles['GoalBody']))
                    current_paragraph = []
                heading_text = stripped_line[4:]
                elements.append(Paragraph(f"<i><b>{heading_text}</b></i>", self.styles['GoalBody']))
                continue

            # Bullet point
            if stripped_line.startswith('- ') or stripped_line.startswith('* '):
                if current_paragraph:
                    para_text = ' '.join(current_paragraph)
                    elements.append(Paragraph(para_text, self.styles['GoalBody']))
                    current_paragraph = []
                bullet_text = stripped_line[2:]
                # Convert basic markdown formatting
                bullet_text = self._convert_inline_markdown(bullet_text)
                elements.append(Paragraph(f"  \u2022 {bullet_text}", self.styles['GoalBody']))
                continue

            # Numbered list
            if re.match(r'^\d+\.\s', stripped_line):
                if current_paragraph:
                    para_text = ' '.join(current_paragraph)
                    elements.append(Paragraph(para_text, self.styles['GoalBody']))
                    current_paragraph = []
                list_text = re.sub(r'^\d+\.\s', '', stripped_line)
                list_text = self._convert_inline_markdown(list_text)
                match = re.match(r'^(\d+)\.', stripped_line)
                num = match.group(1) if match else "1"
                elements.append(Paragraph(f"  {num}. {list_text}", self.styles['GoalBody']))
                continue

            # Horizontal rule
            if stripped_line in ['---', '***', '___']:
                if current_paragraph:
                    para_text = ' '.join(current_paragraph)
                    elements.append(Paragraph(para_text, self.styles['GoalBody']))
                    current_paragraph = []
                elements.append(Spacer(1, 8))
                elements.append(HRFlowable(width="100%", thickness=1, color=self.MUTED_COLOR))
                elements.append(Spacer(1, 8))
                continue

            # Regular text - add to current paragraph
            converted_line = self._convert_inline_markdown(stripped_line)
            current_paragraph.append(converted_line)

        # Flush remaining paragraph
        if current_paragraph:
            para_text = ' '.join(current_paragraph)
            elements.append(Paragraph(para_text, self.styles['GoalBody']))

        return elements

    def _convert_inline_markdown(self, text: str) -> str:
        """Convert inline markdown to ReportLab markup."""
        # Bold: **text** or __text__
        text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
        text = re.sub(r'__(.+?)__', r'<b>\1</b>', text)

        # Italic: *text* or _text_
        text = re.sub(r'\*(.+?)\*', r'<i>\1</i>', text)
        text = re.sub(r'_(.+?)_', r'<i>\1</i>', text)

        # Code: `text`
        text = re.sub(r'`(.+?)`', r'<font face="Courier">\1</font>', text)

        # Escape any remaining special characters for XML
        text = text.replace('&', '&amp;')
        # Don't escape < and > as they are used for markup

        return text

    def generate_goal_pdf(
        self,
        goal: Dict[str, Any],
        user_name: Optional[str] = None,
    ) -> bytes:
        """
        Generate a PDF document for a goal.

        Args:
            goal: Goal data dictionary
            user_name: Optional user name to include

        Returns:
            PDF file as bytes
        """
        buffer = io.BytesIO()

        # Create document
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=0.75*inch,
            leftMargin=0.75*inch,
            topMargin=0.75*inch,
            bottomMargin=0.75*inch,
        )

        elements = []

        # Title
        title = goal.get('title', 'Untitled Goal')
        elements.append(Paragraph(title, self.styles['GoalTitle']))

        # Subtitle with metadata
        subtitle_parts = []
        if goal.get('template_type'):
            template_name = goal['template_type'].upper()
            subtitle_parts.append(f"Template: {template_name}")
        if goal.get('phase'):
            phase_name = goal['phase'].replace('_', ' ').title()
            subtitle_parts.append(f"Status: {phase_name}")

        if subtitle_parts:
            elements.append(Paragraph(" | ".join(subtitle_parts), self.styles['GoalSubtitle']))

        # Horizontal rule
        elements.append(HRFlowable(width="100%", thickness=2, color=self.PRIMARY_COLOR))
        elements.append(Spacer(1, 20))

        # Metadata section
        metadata = goal.get('metadata', {})

        if metadata.get('deadline'):
            elements.append(Paragraph("Deadline", self.styles['MetaLabel']))
            deadline = metadata['deadline']
            if isinstance(deadline, str):
                try:
                    deadline = datetime.fromisoformat(deadline.replace('Z', '+00:00'))
                    deadline_str = deadline.strftime("%B %d, %Y")
                except ValueError:
                    deadline_str = deadline
            else:
                deadline_str = deadline.strftime("%B %d, %Y")
            elements.append(Paragraph(deadline_str, self.styles['MetaValue']))

        if metadata.get('tags'):
            elements.append(Paragraph("Tags", self.styles['MetaLabel']))
            tags_text = ", ".join(f"#{tag}" for tag in metadata['tags'])
            elements.append(Paragraph(tags_text, self.styles['TagStyle']))
            elements.append(Spacer(1, 8))

        # Main content
        content = goal.get('content', '')
        if content:
            elements.append(Spacer(1, 12))
            content_elements = self._markdown_to_paragraphs(content)
            elements.extend(content_elements)

        # Milestones section
        milestones = metadata.get('milestones', [])
        if milestones:
            elements.append(Spacer(1, 16))
            elements.append(HRFlowable(width="100%", thickness=1, color=self.MUTED_COLOR))
            elements.append(Spacer(1, 12))
            elements.append(Paragraph("Milestones", self.styles['SectionHeading']))

            for i, milestone in enumerate(milestones, 1):
                status_icon = "[x]" if milestone.get('completed') else "[ ]"
                milestone_title = milestone.get('title', f'Milestone {i}')
                elements.append(Paragraph(
                    f"{status_icon} {milestone_title}",
                    self.styles['MilestoneItem']
                ))

                if milestone.get('description'):
                    elements.append(Paragraph(
                        f"    {milestone['description']}",
                        self.styles['MilestoneItem']
                    ))

                if milestone.get('target_date'):
                    target_date = milestone['target_date']
                    if isinstance(target_date, str):
                        date_str = target_date
                    else:
                        date_str = target_date.strftime("%Y-%m-%d")
                    elements.append(Paragraph(
                        f"    Target: {date_str}",
                        self.styles['MilestoneItem']
                    ))

        # Footer
        elements.append(Spacer(1, 30))
        elements.append(HRFlowable(width="100%", thickness=1, color=self.MUTED_COLOR))
        elements.append(Spacer(1, 8))

        footer_text = f"Generated by GoalGetter on {datetime.utcnow().strftime('%B %d, %Y at %H:%M UTC')}"
        if user_name:
            footer_text = f"{user_name} | {footer_text}"
        elements.append(Paragraph(footer_text, self.styles['Footer']))

        # Build PDF
        doc.build(elements)

        # Get PDF bytes
        pdf_bytes = buffer.getvalue()
        buffer.close()

        return pdf_bytes

    def get_filename_for_goal(self, goal: Dict[str, Any]) -> str:
        """Generate a safe filename for a goal PDF."""
        title = goal.get('title', 'goal')
        # Sanitize title for filename
        safe_title = re.sub(r'[^\w\s-]', '', title)
        safe_title = re.sub(r'[-\s]+', '-', safe_title).strip('-')
        safe_title = safe_title[:50]  # Limit length

        timestamp = datetime.utcnow().strftime('%Y%m%d')
        return f"goal-{safe_title}-{timestamp}.pdf"


# Create singleton instance
pdf_service = PDFService()
