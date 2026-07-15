from datetime import date
from html import escape
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


ROWS = [
    ["Subject", "Score", "Exam Date"],
    ["English", 82, str(date.today())],
    ["Mathematics", 91, str(date.today())],
    ["Civic Education", 75, str(date.today())],
    ["Physics", 88, str(date.today())],
    ["Chemistry", 84, str(date.today())],
    ["Biology", 80, str(date.today())],
    ["Computer Science", 95, str(date.today())],
    ["Geography", 72, str(date.today())],
]


def cell_ref(row_idx, col_idx):
    return f"{chr(ord('A') + col_idx)}{row_idx}"


def cell_xml(row_idx, col_idx, value):
    ref = cell_ref(row_idx, col_idx)
    if isinstance(value, (int, float)):
        return f'<c r="{ref}"><v>{value}</v></c>'
    return f'<c r="{ref}" t="inlineStr"><is><t>{escape(str(value))}</t></is></c>'


def build_sheet_xml():
    sheet_rows = []
    for row_idx, row in enumerate(ROWS, start=1):
        cells = "".join(cell_xml(row_idx, col_idx, value) for col_idx, value in enumerate(row))
        sheet_rows.append(f'<row r="{row_idx}">{cells}</row>')

    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <dimension ref="A1:C{len(ROWS)}"/>
  <sheetViews><sheetView workbookViewId="0"/></sheetViews>
  <sheetFormatPr defaultRowHeight="15"/>
  <cols>
    <col min="1" max="1" width="22" customWidth="1"/>
    <col min="2" max="2" width="10" customWidth="1"/>
    <col min="3" max="3" width="16" customWidth="1"/>
  </cols>
  <sheetData>{''.join(sheet_rows)}</sheetData>
</worksheet>'''


def write_xlsx(path):
    files = {
        "[Content_Types].xml": '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>''',
        "_rels/.rels": '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>''',
        "xl/workbook.xml": '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Current Grades" sheetId="1" r:id="rId1"/></sheets></workbook>''',
        "xl/_rels/workbook.xml.rels": '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>''',
        "xl/worksheets/sheet1.xml": build_sheet_xml(),
    }

    with ZipFile(path, "w", ZIP_DEFLATED) as archive:
        for name, content in files.items():
            archive.writestr(name, content)


def write_csv(path):
    Path(path).write_text("\n".join(",".join(map(str, row)) for row in ROWS), encoding="utf-8")


if __name__ == "__main__":
    write_xlsx("sample_grades.xlsx")
    write_csv("sample_grades.csv")
    print("Created sample_grades.xlsx and sample_grades.csv")
