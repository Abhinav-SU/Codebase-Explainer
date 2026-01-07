"""
Convert Markdown Report to Professional PDF
Handles tables, code blocks, headings, and lists properly
"""
from fpdf import FPDF
import markdown
from bs4 import BeautifulSoup
import re

class ReportPDF(FPDF):
    def __init__(self):
        super().__init__()
        self.add_font('DejaVu', '', 'DejaVuSans.ttf')
        self.add_font('DejaVu', 'B', 'DejaVuSans-Bold.ttf')
        self.add_font('DejaVuMono', '', 'DejaVuSansMono.ttf')
        self.set_auto_page_break(auto=True, margin=15)
        
    def header(self):
        if self.page_no() > 1:
            self.set_font('DejaVu', '', 8)
            self.cell(0, 10, 'AI-Powered Codebase Explainer - December 1, 2025', 0, 0, 'R')
            self.ln(15)
    
    def footer(self):
        self.set_y(-15)
        self.set_font('DejaVu', '', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')
    
    def add_heading(self, text, level):
        self.ln(5)
        if level == 1:
            self.set_font('DejaVu', 'B', 16)
            self.multi_cell(0, 10, text)
            self.ln(2)
        elif level == 2:
            self.set_font('DejaVu', 'B', 14)
            self.multi_cell(0, 8, text)
            self.ln(1)
        elif level == 3:
            self.set_font('DejaVu', 'B', 12)
            self.multi_cell(0, 7, text)
            self.ln(1)
        else:
            self.set_font('DejaVu', 'B', 11)
            self.multi_cell(0, 6, text)
    
    def add_paragraph(self, text):
        self.set_font('DejaVu', '', 10)
        # Clean up extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        if text:
            self.multi_cell(0, 5, text)
            self.ln(2)
    
    def add_code_block(self, code):
        self.set_fill_color(240, 240, 240)
        self.set_font('DejaVuMono', '', 8)
        
        # Split code into lines and handle long lines
        lines = code.split('\n')
        for line in lines:
            if len(line) > 90:
                # Wrap long lines
                words = line.split(' ')
                current_line = ''
                for word in words:
                    if len(current_line) + len(word) + 1 <= 90:
                        current_line += word + ' '
                    else:
                        if current_line:
                            self.cell(0, 4, current_line.rstrip(), 0, 1, '', True)
                        current_line = '  ' + word + ' '
                if current_line:
                    self.cell(0, 4, current_line.rstrip(), 0, 1, '', True)
            else:
                self.cell(0, 4, line, 0, 1, '', True)
        self.ln(3)
    
    def add_bullet(self, text, level=0):
        self.set_font('DejaVu', '', 10)
        indent = 10 + (level * 5)
        self.set_x(indent)
        bullet = '•' if level == 0 else '◦'
        text = re.sub(r'\s+', ' ', text).strip()
        self.multi_cell(0, 5, f'{bullet} {text}')
    
    def add_table_row(self, cells, is_header=False):
        col_widths = [50, 30, 35, 45]  # Adjust based on content
        
        if is_header:
            self.set_font('DejaVu', 'B', 9)
            self.set_fill_color(200, 200, 200)
        else:
            self.set_font('DejaVu', '', 9)
            self.set_fill_color(245, 245, 245)
        
        # Calculate row height based on content
        max_lines = 1
        for i, cell in enumerate(cells):
            cell_text = str(cell).strip()
            lines = len(cell_text) // (col_widths[i] // 2) + 1
            max_lines = max(max_lines, lines)
        
        row_height = 5 * max_lines
        
        for i, cell in enumerate(cells):
            if i >= len(col_widths):
                break
            cell_text = str(cell).strip()
            self.cell(col_widths[i], row_height, cell_text[:40], 1, 0, 'L', True)
        
        self.ln()
    
    def add_horizontal_line(self):
        self.ln(2)
        self.set_draw_color(200, 200, 200)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(2)

def parse_markdown_to_pdf(md_file, output_pdf):
    # Read markdown
    with open(md_file, 'r', encoding='utf-8') as f:
        md_content = f.read()
    
    pdf = ReportPDF()
    pdf.add_page()
    
    # Process line by line for better control
    lines = md_content.split('\n')
    i = 0
    in_code_block = False
    code_buffer = []
    in_table = False
    table_rows = []
    
    while i < len(lines):
        line = lines[i]
        
        # Code blocks
        if line.startswith('```'):
            if in_code_block:
                # End of code block
                pdf.add_code_block('\n'.join(code_buffer))
                code_buffer = []
                in_code_block = False
            else:
                # Start of code block
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
                table_rows = []
            
            # Parse table row
            cells = [cell.strip() for cell in line.split('|')[1:-1]]
            
            # Skip separator rows
            if all(set(cell.strip()) <= set('-: ') for cell in cells if cell.strip()):
                i += 1
                continue
            
            table_rows.append(cells)
            i += 1
            continue
        elif in_table:
            # End of table - render it
            if table_rows:
                is_first = True
                for row in table_rows:
                    pdf.add_table_row(row, is_header=is_first)
                    is_first = False
                pdf.ln(3)
            in_table = False
            table_rows = []
        
        # Horizontal rules
        if line.strip() in ['---', '___', '***']:
            pdf.add_horizontal_line()
            i += 1
            continue
        
        # Headings
        if line.startswith('#'):
            level = len(line) - len(line.lstrip('#'))
            text = line.lstrip('#').strip()
            # Remove markdown bold/italic markers
            text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
            pdf.add_heading(text, level)
            i += 1
            continue
        
        # Bullet points
        if line.strip().startswith(('- ', '* ', '+ ')):
            text = line.strip()[2:]
            # Remove markdown formatting
            text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
            text = re.sub(r'`(.+?)`', r'\1', text)
            pdf.add_bullet(text)
            i += 1
            continue
        
        # Numbered lists
        if re.match(r'^\d+\.\s', line.strip()):
            text = re.sub(r'^\d+\.\s', '', line.strip())
            text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
            text = re.sub(r'`(.+?)`', r'\1', text)
            pdf.add_bullet(text)
            i += 1
            continue
        
        # Regular paragraph
        if line.strip():
            # Remove markdown formatting
            text = re.sub(r'\*\*(.+?)\*\*', r'\1', line)
            text = re.sub(r'`(.+?)`', r'\1', text)
            text = re.sub(r'\[(.+?)\]\(.+?\)', r'\1', text)  # Links
            pdf.add_paragraph(text)
        else:
            # Empty line - just add small space
            if pdf.get_y() < pdf.h - 20:  # Don't add space at bottom
                pdf.ln(2)
        
        i += 1
    
    # Save PDF
    pdf.output(output_pdf)
    print(f"PDF created: {output_pdf}")

if __name__ == "__main__":
    input_md = "DECEMBER_1_2025_INTERNSHIP_REPORT.md"
    output_pdf = "DECEMBER_1_2025_INTERNSHIP_REPORT.pdf"
    
    parse_markdown_to_pdf(input_md, output_pdf)
    print(f"\nSuccess! Professional PDF generated: {output_pdf}")
