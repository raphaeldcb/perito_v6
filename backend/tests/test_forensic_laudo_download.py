"""
Tests for forensic laudo download endpoint.

Tests:
- Download DOCX successfully (200)
- Download PDF successfully (200)
- Return 404 if laudo not generated
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime


def test_download_laudo_docx_returns_200():
    """Test downloading DOCX laudo returns 200 OK."""
    from fastapi.testclient import TestClient
    from main import app

    client = TestClient(app)

    # Mock database session
    mock_db_session = MagicMock()

    # Mock analysis object
    mock_analysis = MagicMock()
    mock_analysis.id = 1
    mock_analysis.arquivo_nome = "test.jpg"
    mock_analysis.resultado_json = {"codigo_laudo": "L20260807ABC123"}
    mock_analysis.laudo_docx_url = "https://onedrive.com/file.docx"
    mock_analysis.laudo_pdf_url = None

    # Setup query mock chain
    mock_query_result = MagicMock()
    mock_query_result.first.return_value = mock_analysis
    mock_db_session.query.return_value.filter.return_value = mock_query_result

    # Mock OneDrive client
    mock_docx_bytes = b"PK\x03\x04mock"

    with patch("app.routes.forensic_analysis.SessionLocal") as mock_session_local:
        mock_session_local.return_value = mock_db_session
        with patch("app.routes.forensic_analysis.OneDriveClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_client.download_file.return_value = mock_docx_bytes

            response = client.get("/api/v1/forensic/1/laudo-download?format=docx")

    assert response.status_code == 200
    assert "application/vnd.openxmlformats-officedocument.wordprocessingml.document" in response.headers.get("content-type", "")
    assert "attachment" in response.headers.get("content-disposition", "")
    assert ".docx" in response.headers.get("content-disposition", "")


def test_download_laudo_pdf_returns_200():
    """Test downloading PDF laudo returns 200 OK."""
    from fastapi.testclient import TestClient
    from main import app

    client = TestClient(app)

    # Mock database session
    mock_db_session = MagicMock()

    # Mock analysis object
    mock_analysis = MagicMock()
    mock_analysis.id = 2
    mock_analysis.arquivo_nome = "test.jpg"
    mock_analysis.resultado_json = {"codigo_laudo": "L20260807DEF456"}
    mock_analysis.laudo_docx_url = None
    mock_analysis.laudo_pdf_url = "https://onedrive.com/file.pdf"

    # Setup query mock chain
    mock_query_result = MagicMock()
    mock_query_result.first.return_value = mock_analysis
    mock_db_session.query.return_value.filter.return_value = mock_query_result

    # Mock OneDrive client
    mock_pdf_bytes = b"%PDF-1.4mock"

    with patch("app.routes.forensic_analysis.SessionLocal") as mock_session_local:
        mock_session_local.return_value = mock_db_session
        with patch("app.routes.forensic_analysis.OneDriveClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_client.download_file.return_value = mock_pdf_bytes

            response = client.get("/api/v1/forensic/2/laudo-download?format=pdf")

    assert response.status_code == 200
    assert "application/pdf" in response.headers.get("content-type", "")
    assert "attachment" in response.headers.get("content-disposition", "")
    assert ".pdf" in response.headers.get("content-disposition", "")


def test_download_laudo_not_generated_returns_404():
    """Test returning 404 if laudo not generated."""
    from fastapi.testclient import TestClient
    from main import app

    client = TestClient(app)

    # Mock database session
    mock_db_session = MagicMock()

    # Mock analysis object without laudo URLs
    mock_analysis = MagicMock()
    mock_analysis.id = 3
    mock_analysis.arquivo_nome = "test.jpg"
    mock_analysis.resultado_json = {"codigo_laudo": "L20260807GHI789"}
    mock_analysis.laudo_docx_url = None
    mock_analysis.laudo_pdf_url = None

    # Setup query mock chain
    mock_query_result = MagicMock()
    mock_query_result.first.return_value = mock_analysis
    mock_db_session.query.return_value.filter.return_value = mock_query_result

    with patch("app.routes.forensic_analysis.SessionLocal") as mock_session_local:
        mock_session_local.return_value = mock_db_session

        response = client.get("/api/v1/forensic/3/laudo-download?format=docx")

    assert response.status_code == 404
    assert "laudo" in response.json()["detail"].lower()


def test_download_laudo_analysis_not_found_returns_404():
    """Test returning 404 if analysis not found."""
    from fastapi.testclient import TestClient
    from main import app

    client = TestClient(app)

    # Mock database session that returns None
    mock_db_session = MagicMock()
    mock_query_result = MagicMock()
    mock_query_result.first.return_value = None
    mock_db_session.query.return_value.filter.return_value = mock_query_result

    with patch("app.routes.forensic_analysis.SessionLocal") as mock_session_local:
        mock_session_local.return_value = mock_db_session

        response = client.get("/api/v1/forensic/9999/laudo-download?format=docx")

    assert response.status_code == 404
    assert "análise" in response.json()["detail"].lower() or "não encontrada" in response.json()["detail"].lower()
