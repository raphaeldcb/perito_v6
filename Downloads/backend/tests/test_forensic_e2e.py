"""
End-to-End tests for forensic analysis complete workflow (upload → analyze → laudo DOCX/PDF).
Tests the full pipeline: file upload → analysis completion → DOCX generation → PDF generation.
"""
import pytest
import time
import os
from pathlib import Path
from io import BytesIO
import requests


class TestForensicAnalysisE2E:
    """E2E test suite for forensic analysis workflow."""

    # Base URL - defaults to localhost:8000, override with FORENSIC_API_URL env var
    BASE_URL = os.getenv("FORENSIC_API_URL", "http://localhost:8000")

    # API paths
    UPLOAD_ENDPOINT = f"{BASE_URL}/api/v1/forensic/upload"
    LAUDO_DOCX_ENDPOINT_TEMPLATE = f"{BASE_URL}/api/v1/forensic/{{analysis_id}}/laudo-docx"
    LAUDO_PDF_ENDPOINT_TEMPLATE = f"{BASE_URL}/api/v1/forensic/{{analysis_id}}/laudo-pdf"

    # Test auth token (override with FORENSIC_TOKEN env var)
    AUTH_TOKEN = os.getenv("FORENSIC_TOKEN", "test-token")

    @pytest.fixture
    def auth_headers(self):
        """Return authorization headers for API requests."""
        return {
            "Authorization": f"Bearer {self.AUTH_TOKEN}",
            "Content-Type": "application/json"
        }

    @pytest.fixture
    def sample_test_file(self, tmp_path):
        """Create a minimal test image file for upload."""
        # Create a small PNG test file (100x100 pixels, 8-bit RGB)
        # PNG signature + minimal IHDR + minimal image data
        png_bytes = (
            b'\x89PNG\r\n\x1a\n'  # PNG signature
            b'\x00\x00\x00\rIHDR\x00\x00\x00d\x00\x00\x00d'  # IHDR: 100x100
            b'\x08\x02\x00\x00\x00\xf6\x18\'\xdbIDAT\x08\x99'  # color type RGB
            b'\x01\x01\x00\xfe\xfe\x00\x00\x00\x00\x00\x00IEND\xaeB`\x82'
        )
        test_file = tmp_path / "test_image.png"
        test_file.write_bytes(png_bytes)
        return test_file

    @pytest.fixture
    def sample_small_image(self, tmp_path):
        """Create a small test JPEG for upload (minimal valid JPEG)."""
        # Minimal valid JPEG file
        jpeg_bytes = (
            b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00'
            b'\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c'
            b'\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c'
            b'\x1c $.\' ",#\x1c\x1c(7),01444\x1f\'9=82<.342\xff\xc0\x00\x0b\x08\x00'
            b'\x01\x00\x01\x01\x11\x00\xff\xc4\x00\x14\x00\x01\x00\x00\x00\x00\x00\x00'
            b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xda\x00\x08\x01\x01\x00\x00'
            b'?\x00\x01\x00\xff\xd9'
        )
        test_file = tmp_path / "test_image.jpg"
        test_file.write_bytes(jpeg_bytes)
        return test_file

    def test_forensic_api_health(self):
        """Test that the forensic API is reachable."""
        try:
            response = requests.get(f"{self.BASE_URL}/health", timeout=5)
            # Health endpoint may not exist, but we check reachability
            assert response.status_code in [200, 404, 405], f"API not reachable: {response.status_code}"
        except requests.exceptions.ConnectionError:
            pytest.skip(f"Forensic API not available at {self.BASE_URL}")

    def test_forensic_upload_returns_analysis_id(self, auth_headers, sample_test_file):
        """Test file upload and verify analysis ID is returned."""
        with open(sample_test_file, 'rb') as f:
            files = {'file': (sample_test_file.name, f, 'image/png')}
            response = requests.post(
                self.UPLOAD_ENDPOINT,
                files=files,
                headers={k: v for k, v in auth_headers.items() if k != "Content-Type"}
            )

        # Accept 200 or 201
        assert response.status_code in [200, 201], f"Upload failed: {response.status_code} - {response.text}"

        data = response.json()
        assert 'id' in data, f"Response missing 'id' field: {data}"
        assert isinstance(data['id'], str), "Analysis ID should be a string"
        assert len(data['id']) > 0, "Analysis ID should not be empty"

        return data['id']

    def test_forensic_analysis_complete_laudo_workflow(self, auth_headers, sample_test_file):
        """
        E2E: Complete forensic workflow from upload to DOCX and PDF generation.

        Steps:
        1. Upload a test file
        2. Wait for analysis completion (5 seconds)
        3. Fetch DOCX laudo
        4. Fetch PDF laudo
        5. Validate both formats and sizes
        """
        # Step 1: Upload file
        print("\n[Step 1] Uploading test file...")
        with open(sample_test_file, 'rb') as f:
            files = {'file': (sample_test_file.name, f, 'image/png')}
            upload_response = requests.post(
                self.UPLOAD_ENDPOINT,
                files=files,
                headers={k: v for k, v in auth_headers.items() if k != "Content-Type"},
                timeout=10
            )

        assert upload_response.status_code in [200, 201], \
            f"Upload failed: {upload_response.status_code} - {upload_response.text}"

        analysis_data = upload_response.json()
        analysis_id = analysis_data['id']
        print(f"[Step 1] ✓ File uploaded, analysis_id={analysis_id}")

        # Step 2: Wait for analysis completion
        print("[Step 2] Waiting 5 seconds for analysis to complete...")
        time.sleep(5)
        print("[Step 2] ✓ Analysis wait time completed")

        # Step 3: Get DOCX laudo
        print("[Step 3] Fetching DOCX laudo...")
        docx_url = self.LAUDO_DOCX_ENDPOINT_TEMPLATE.format(analysis_id=analysis_id)
        docx_response = requests.get(
            docx_url,
            headers=auth_headers,
            timeout=30
        )

        assert docx_response.status_code == 200, \
            f"DOCX endpoint failed: {docx_response.status_code} - {docx_response.text}"

        # Verify DOCX content type
        content_type = docx_response.headers.get('Content-Type', '')
        assert 'application/vnd.openxmlformats' in content_type or 'application/vnd.ms-word' in content_type, \
            f"Invalid DOCX content type: {content_type}"

        docx_bytes = docx_response.content
        assert len(docx_bytes) > 1000, \
            f"DOCX too small: {len(docx_bytes)} bytes (expected > 1000)"

        # Verify DOCX is a valid ZIP (DOCX files are ZIP archives)
        assert docx_bytes[:2] == b'PK', \
            f"DOCX is not a valid ZIP archive (invalid magic bytes)"

        print(f"[Step 3] ✓ DOCX generated successfully ({len(docx_bytes)} bytes)")

        # Step 4: Get PDF laudo
        print("[Step 4] Fetching PDF laudo...")
        pdf_url = self.LAUDO_PDF_ENDPOINT_TEMPLATE.format(analysis_id=analysis_id)
        pdf_response = requests.get(
            pdf_url,
            headers=auth_headers,
            timeout=30
        )

        assert pdf_response.status_code == 200, \
            f"PDF endpoint failed: {pdf_response.status_code} - {pdf_response.text}"

        # Verify PDF content type
        content_type = pdf_response.headers.get('Content-Type', '')
        assert 'application/pdf' in content_type, \
            f"Invalid PDF content type: {content_type}"

        pdf_bytes = pdf_response.content
        assert len(pdf_bytes) > 10000, \
            f"PDF too small: {len(pdf_bytes)} bytes (expected > 10000)"

        # Verify PDF is valid (starts with %PDF)
        assert pdf_bytes[:4] == b'%PDF', \
            f"PDF is not a valid PDF (invalid magic bytes)"

        print(f"[Step 4] ✓ PDF generated successfully ({len(pdf_bytes)} bytes)")

        # Step 5: Validate both formats
        print("[Step 5] Validating document formats...")

        # Verify DOCX can be parsed
        try:
            from docx import Document
            doc = Document(BytesIO(docx_bytes))
            paragraph_count = len(doc.paragraphs)
            assert paragraph_count > 0, "DOCX has no paragraphs"
            print(f"[Step 5] ✓ DOCX is valid ({paragraph_count} paragraphs)")
        except Exception as e:
            pytest.fail(f"Failed to parse DOCX: {e}")

        # Verify PDF file structure (basic checks)
        pdf_text = pdf_bytes.decode('latin-1', errors='ignore')
        assert '%%EOF' in pdf_text or 'endobj' in pdf_text, \
            "PDF structure appears invalid (missing PDF objects)"
        print("[Step 5] ✓ PDF structure is valid")

        print("\n✓✓✓ E2E workflow PASSED ✓✓✓")
        return {
            'analysis_id': analysis_id,
            'docx_size': len(docx_bytes),
            'pdf_size': len(pdf_bytes),
            'docx_valid': True,
            'pdf_valid': True
        }

    def test_forensic_laudo_docx_endpoint_not_found(self, auth_headers):
        """Test that laudo-docx endpoint returns 404 for non-existent analysis."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        docx_url = self.LAUDO_DOCX_ENDPOINT_TEMPLATE.format(analysis_id=fake_id)

        response = requests.get(
            docx_url,
            headers=auth_headers,
            timeout=10
        )

        assert response.status_code == 404, \
            f"Expected 404 for non-existent analysis, got {response.status_code}"

    def test_forensic_laudo_pdf_endpoint_not_found(self, auth_headers):
        """Test that laudo-pdf endpoint returns 404 for non-existent analysis."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        pdf_url = self.LAUDO_PDF_ENDPOINT_TEMPLATE.format(analysis_id=fake_id)

        response = requests.get(
            pdf_url,
            headers=auth_headers,
            timeout=10
        )

        assert response.status_code == 404, \
            f"Expected 404 for non-existent analysis, got {response.status_code}"


# Module-level test for quick validation
def test_forensic_endpoints_reachable():
    """Quick smoke test to verify endpoints are reachable."""
    base_url = os.getenv("FORENSIC_API_URL", "http://localhost:8000")
    try:
        response = requests.head(f"{base_url}/api/v1/forensic/dummy", timeout=3)
        # We expect 401, 404, or similar - just verifying the server responds
        assert response.status_code < 500, f"Server error: {response.status_code}"
    except requests.exceptions.ConnectionError:
        pytest.skip(f"API endpoint not available at {base_url}")
