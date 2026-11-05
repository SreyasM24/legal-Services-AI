"""
Pytest configuration and shared synthetic legal fixtures.
"""

import io
import sys
from pathlib import Path
import pytest
import pypdf
import docx

# Ensure backend root is on sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.storage import document_store


SAMPLE_LEGAL_CONTRACT = """CONFIDENTIALITY AND NON-DISCLOSURE AGREEMENT

This Confidentiality Agreement ("Agreement") is made effective as of October 15, 2024, by and between Nexus Corp ("Disclosing Party"), a Delaware corporation with offices at contact@nexuscorp.com, and Apex Solutions LLC ("Receiving Party"), with registered office at legal@apexsolutions.com.

1. Definition of Confidential Information
"Confidential Information" refers to any proprietary information, technical data, trade secrets, operational methods, customer lists, or business strategies disclosed by Disclosing Party to Receiving Party, whether orally or in writing.

2. Obligations of Non-Disclosure
Receiving Party agrees to maintain the strict confidentiality of all Confidential Information using the highest reasonable standard of care. Receiving Party shall not disclose, publish, or disseminate Confidential Information to any third party without prior written consent.

3. Term and Termination
This Agreement shall commence on the Effective Date and continue for a period of three (3) years. Either party may terminate this Agreement immediately upon written notice of termination if the other party commits a material breach and fails to cure such event of default within thirty (30) days.

4. Indemnification and Hold Harmless
Receiving Party shall defend, indemnify, and hold harmless Disclosing Party, its directors, officers, and employees against any third-party claims, liabilities, losses, damages, costs, and reasonable attorneys' fees arising from unauthorized disclosure.

5. Limitation of Liability
In no event shall either party's aggregate liability exceed the total sum of $150,000 USD paid under this agreement. Neither party shall be liable for indirect, incidental, special, or consequential damages.

6. Governing Law and Arbitration
This Agreement shall be governed by and construed in accordance with the laws of the State of Delaware. Any dispute resolution proceeding shall be settled by binding arbitration administered by the American Arbitration Association under exclusive jurisdiction in New Castle County.

7. Warranties and Representations
Each party represents and warrants that it has the full corporate power and authority to enter into this Agreement. The deliverables are provided as is without express or implied warranties of merchantability or fitness for a particular purpose.

8. Force Majeure
Neither party shall be held liable for failure to perform any obligation due to acts of God, natural disasters, epidemic, war, terrorism, or other unforeseeable circumstances beyond reasonable control.

9. Intellectual Property Rights
All intellectual property, patents, copyrights, trademarks, and proprietary rights in the materials remain the exclusive property of Disclosing Party. Nothing herein constitutes a work made for hire or license grant.

IN WITNESS WHEREOF, the parties hereto have executed this Agreement on October 15, 2024.
Disclosing Party Fee: $50,000 payable upon execution.
"""


@pytest.fixture(autouse=True)
def clean_storage():
    """Clear in-memory document store before each test."""
    document_store.clear()
    yield
    document_store.clear()


@pytest.fixture
def sample_contract_text() -> str:
    return SAMPLE_LEGAL_CONTRACT


@pytest.fixture
def sample_pdf_bytes() -> bytes:
    """Generate a minimal valid PDF with extractable text."""
    pdf_raw = b"""%PDF-1.4
1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj
2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj
3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >> endobj
4 0 obj << /Length 200 >>
stream
BT
/F1 12 Tf
72 712 Td
(CONFIDENTIALITY AND NON-DISCLOSURE AGREEMENT) Tj
0 -24 Td
(Either party may terminate this Agreement immediately upon written notice.) Tj
0 -24 Td
(The Receiving Party agrees to indemnify and hold harmless the Disclosing Party.) Tj
ET
endstream
endobj
5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj
xref
0 6
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000244 00000 n 
0000000495 00000 n 
trailer << /Size 6 /Root 1 0 R >>
startxref
571
%%EOF"""
    return pdf_raw


@pytest.fixture
def sample_docx_bytes() -> bytes:
    """Generate a valid DOCX file containing legal agreement text."""
    doc = docx.Document()
    doc.add_heading("Master Services Agreement", level=1)
    doc.add_paragraph(
        "This Agreement is entered into on 2024-11-01 between Company A and Company B for $75,000 USD."
    )
    doc.add_paragraph(
        "Section 1. Confidentiality: Each party agrees not to disclose proprietary information."
    )
    doc.add_paragraph(
        "Section 2. Termination: Either party may terminate upon material breach."
    )
    doc.add_paragraph(
        "Section 3. Governing Law: This contract is governed by the laws of the State of New York."
    )
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


@pytest.fixture
def empty_pdf_bytes() -> bytes:
    """Generate a blank PDF with 0 extractable text to test scanned PDF detection."""
    writer = pypdf.PdfWriter()
    writer.add_blank_page(width=300, height=300)
    stream = io.BytesIO()
    writer.write(stream)
    return stream.getvalue()
