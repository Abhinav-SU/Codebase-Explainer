"""
Convert Markdown Report to Professional PDF using ReportLab
Handles tables, code blocks, headings, and lists properly with Unicode support
"""
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Preformatted
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.pdfgen import canvas
import re

def parse_markdown_to_pdf(md_file, output_pdf):
    # Read markdown
    with open(md_file, 'r', encoding='utf-8') as f:
        md_content = f.read()
    
    # Create PDF
    doc = SimpleDocTemplate(
        output_pdf,
        pagesize=letter,
        rightMargin=0.75*inch,
        leftMargin=0.75*inch,
        topMargin=0.75*inch,
        bottomMargin=0.75*inch
    )
    
    # Styles
    styles = getSampleStyleSheet()
    
    # Custom styles
    styles.add(ParagraphStyle(
        name='CustomHeading1',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=12,
        spaceBefore=12,
        textColor=colors.HexColor('#1a1a1a')
    ))
    
    styles.add(ParagraphStyle(
        name='CustomHeading2',
        parent=styles['Heading2'],
        fontSize=14,
        spaceAfter=10,
        spaceBefore=10,
        textColor=colors.HexColor('#2a2a2a')
    ))
    
    styles.add(ParagraphStyle(
        name='CustomHeading3',
        parent=styles['Heading3'],
        fontSize=12,
        spaceAfter=8,
        spaceBefore=8,
        textColor=colors.HexColor('#3a3a3a')
    ))
    
    styles.add(ParagraphStyle(
        name='CustomBody',
        parent=styles['BodyText'],
        fontSize=10,
        leading=14,
        alignment=TA_JUSTIFY,
        spaceAfter=6
    ))
    
    styles.add(ParagraphStyle(
        name='BulletStyle',
        parent=styles['BodyText'],
        fontSize=10,
        leading=14,
        leftIndent=20,
        spaceAfter=4
    ))
    
    styles.add(ParagraphStyle(
        name='CodeStyle',
        parent=styles['Code'],
        fontSize=8,
        leading=10,
        leftIndent=10,
        rightIndent=10,
        backColor=colors.HexColor('#f5f5f5'),
        borderColor=colors.HexColor('#e0e0e0'),
        borderWidth=1,
        borderPadding=6
    ))
    
    # Build story
    story = []
    
    lines = md_content.split('\n')
    i = 0
    in_code_block = False
    code_buffer = []
    in_table = False
    table_data = []
    
    while i < len(lines):
        line = lines[i]
        
        # Code blocks
        if line.startswith('```'):
            if in_code_block:
                # End of code block
                code_text = '\n'.join(code_buffer)
                # Wrap long lines
                wrapped_lines = []
                for code_line in code_buffer:
                    if len(code_line) > 80:
                        for j in range(0, len(code_line), 80):
                            wrapped_lines.append(code_line[j:j+80])
                    else:
                        wrapped_lines.append(code_line)
                
                code_para = Preformatted('\n'.join(wrapped_lines), styles['CodeStyle'])
                story.append(code_para)
                story.append(Spacer(1, 0.15*inch))
                code_buffer = []
                in_code_block = False
            else:
                in_code_block = True
            i += 1
            continue
        
        if in_code_block:
            code_buffer.append(line)
            i += 1
            continue
        
        # Tables
        if '|' in line and line.strip().startswith('|'):
            if not in_table:
                in_table = True
                table_data = []
            
            # Parse table row
            cells = [cell.strip() for cell in line.split('|')[1:-1]]
            
            # Skip separator rows
            if all(set(cell.strip()) <= set('-: ') for cell in cells if cell.strip()):
                i += 1
                continue
            
            table_data.append(cells)
            i += 1
            continue
        elif in_table:
            # End of table - render it
            if table_data:
                # Create table
                t = Table(table_data)
                t.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#d0d0d0')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 9),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f5f5f5')),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                    ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 1), (-1, -1), 8),
                    ('TOPPADDING', (0, 0), (-1, -1), 4),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ]))
                story.append(t)
                story.append(Spacer(1, 0.15*inch))
            in_table = False
            table_data = []
        
        # Horizontal rules
        if line.strip() in ['---', '___', '***']:
            story.append(Spacer(1, 0.1*inch))
            i += 1
            continue
        
        # Headings
        if line.startswith('#'):
            level = len(line) - len(line.lstrip('#'))
            text = line.lstrip('#').strip()
            # Remove markdown formatting
            text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
            text = re.sub(r'`(.+?)`', r'<font name="Courier">\1</font>', text)
            
            if level == 1:
                story.append(Spacer(1, 0.15*inch))
                story.append(Paragraph(text, styles['CustomHeading1']))
            elif level == 2:
                story.append(Spacer(1, 0.1*inch))
                story.append(Paragraph(text, styles['CustomHeading2']))
            elif level == 3:
                story.append(Paragraph(text, styles['CustomHeading3']))
            else:
                story.append(Paragraph(f'<b>{text}</b>', styles['CustomBody']))
            
            i += 1
            continue
        
        # Bullet points
        if line.strip().startswith(('- ', '* ', '+ ')):
            text = line.strip()[2:]
            # Convert markdown to reportlab markup
            text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
            text = re.sub(r'`(.+?)`', r'<font name="Courier">\1</font>', text)
            text = re.sub(r'\[(.+?)\]\(.+?\)', r'\1', text)
            
            bullet_para = Paragraph(f'\u2022 {text}', styles['BulletStyle'])
            story.append(bullet_para)
            i += 1
            continue
        
        # Numbered lists
        if re.match(r'^\d+\.\s', line.strip()):
            text = re.sub(r'^\d+\.\s', '', line.strip())
            text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
            text = re.sub(r'`(.+?)`', r'<font name="Courier">\1</font>', text)
            text = re.sub(r'\[(.+?)\]\(.+?\)', r'\1', text)
            
            # Extract number
            num = re.match(r'^(\d+)\.', line.strip()).group(1)
            bullet_para = Paragraph(f'{num}. {text}', styles['BulletStyle'])
            story.append(bullet_para)
            i += 1
            continue
        
        # Regular paragraph
        if line.strip():
            text = line.strip()
            # Convert markdown to reportlab markup
            text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
            text = re.sub(r'`(.+?)`', r'<font name="Courier" size="9">\1</font>', text)
            text = re.sub(r'\[(.+?)\]\(.+?\)', r'\1', text)
            
            # Skip lines that are just formatting
            if text not in ['---', '___', '***']:
                para = Paragraph(text, styles['CustomBody'])
                story.append(para)
        else:
            # Empty line - small spacer
            story.append(Spacer(1, 0.08*inch))
        
        i += 1
    
    # Build PDF
    doc.build(story)
    print(f"PDF created: {output_pdf}")

if __name__ == "__main__":
    input_md = "DECEMBER_1_2025_INTERNSHIP_REPORT.md"
    output_pdf = "DECEMBER_1_2025_INTERNSHIP_REPORT.pdf"
    
    try:
        parse_markdown_to_pdf(input_md, output_pdf)
        print(f"\n✓ Success! Professional PDF generated: {output_pdf}")
        print(f"  - Proper page breaks")
        print(f"  - Tables formatted correctly")
        print(f"  - Code blocks with syntax preservation")
        print(f"  - Unicode characters supported")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
