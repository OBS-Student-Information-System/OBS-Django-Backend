"""
Unit tests for StudentFileScraper._parse_grid() and _extract_updatepanel_html().

Run with:
    python -m pytest tests/test_student_file_parser.py -v
"""
import pytest
from modules.student_file.scraper import StudentFileScraper


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

EMPTY_TABLE_HTML = """
<html><body>
  <table class="grdStyle">
    <tr><th>Birim</th><th>Program</th></tr>
  </table>
</body></html>
"""

NO_RECORD_TABLE_HTML = """
<html><body>
  <table class="grdStyle">
    <tr><th>Birim</th><th>Program</th></tr>
    <tr><td>Kayıt bulunamadı</td><td></td></tr>
  </table>
</body></html>
"""

NO_RECORD_TABLE_HTML_VARIANT = """
<html><body>
  <table class="grdStyle">
    <tr><th>Ceza Nedeni</th><th>Verilen Ceza</th></tr>
    <tr><td colspan="2">kayıt bulunamadı</td><td></td></tr>
  </table>
</body></html>
"""

VALID_TABLE_HTML = """
<html><body>
  <table class="grdStyle">
    <tr><th>Birim</th><th>Program</th><th>Durum</th></tr>
    <tr><td>Mühendislik</td><td>Bilgisayar</td><td>Aktif</td></tr>
    <tr><td>Fen Bilimleri</td><td>Yazılım</td><td>Mezun</td></tr>
  </table>
</body></html>
"""

NBSP_ROW_TABLE_HTML = """
<html><body>
  <table class="grdStyle">
    <tr><th>Birim</th><th>Program</th></tr>
    <tr><td>&nbsp;</td><td>&nbsp;</td></tr>
    <tr><td>Mühendislik</td><td>Bilgisayar</td></tr>
  </table>
</body></html>
"""

NO_TABLE_HTML = """
<html><body>
  <p>No table here.</p>
</body></html>
"""

UPDATEPANEL_DELTA_RESPONSE = (
    "280|updatePanel|ctl00_ContentPlaceHolder1_UpdatePanel1|"
    "<table class='grdStyle'><tr><th>Konu</th></tr>"
    "<tr><td>Test Semineri</td></tr></table>|"
    "0|hiddenField|__VIEWSTATE|abc123|"
)


# ---------------------------------------------------------------------------
# _parse_grid tests
# ---------------------------------------------------------------------------

class TestParseGrid:
    scraper = StudentFileScraper()

    def test_empty_table_returns_empty_list(self):
        result = self.scraper._parse_grid(EMPTY_TABLE_HTML)
        assert result == [], "Header-only table must return an empty list"

    def test_no_record_row_returns_empty_list(self):
        result = self.scraper._parse_grid(NO_RECORD_TABLE_HTML)
        assert result == [], "'Kayıt bulunamadı' row must be filtered out"

    def test_no_record_row_variant_returns_empty_list(self):
        result = self.scraper._parse_grid(NO_RECORD_TABLE_HTML_VARIANT)
        assert result == [], "Lowercase 'kayıt bulunamadı' must also be filtered"

    def test_valid_table_returns_correct_rows(self):
        result = self.scraper._parse_grid(VALID_TABLE_HTML)
        assert len(result) == 2
        assert result[0]["birim"] == "Mühendislik"
        assert result[0]["program"] == "Bilgisayar"
        assert result[0]["durum"] == "Aktif"
        assert result[1]["birim"] == "Fen Bilimleri"

    def test_nbsp_rows_are_skipped(self):
        result = self.scraper._parse_grid(NBSP_ROW_TABLE_HTML)
        assert len(result) == 1, "Non-breaking space rows must be skipped"
        assert result[0]["birim"] == "Mühendislik"

    def test_no_table_returns_empty_list(self):
        result = self.scraper._parse_grid(NO_TABLE_HTML)
        assert result == [], "HTML without grdStyle table must return empty list"

    def test_header_normalization(self):
        """Column names must be normalized to snake_case ASCII."""
        html = """
        <table class="grdStyle">
          <tr><th>Öğretim Yılı</th><th>Dönemi</th></tr>
          <tr><td>2024-2025</td><td>Güz</td></tr>
        </table>
        """
        result = self.scraper._parse_grid(html)
        assert len(result) == 1
        assert "ogretim_yili" in result[0]
        assert "donemi" in result[0]


# ---------------------------------------------------------------------------
# _extract_updatepanel_html tests
# ---------------------------------------------------------------------------

class TestExtractUpdatePanelHtml:

    def test_extracts_html_from_delta_response(self):
        html = StudentFileScraper._extract_updatepanel_html(UPDATEPANEL_DELTA_RESPONSE)
        assert "grdStyle" in html, "Must extract the table HTML from delta response"
        assert "Test Semineri" in html

    def test_returns_full_html_when_no_delta(self):
        full_html = "<html><body><table class='grdStyle'></table></body></html>"
        result = StudentFileScraper._extract_updatepanel_html(full_html)
        assert "grdStyle" in result, "Must return full HTML when no delta segments found"


# ---------------------------------------------------------------------------
# _extract_viewstate tests
# ---------------------------------------------------------------------------

class TestExtractViewstate:
    from bs4 import BeautifulSoup

    def test_extracts_hidden_fields(self):
        from bs4 import BeautifulSoup
        html = """
        <form>
          <input type="hidden" name="__VIEWSTATE" value="abc123" />
          <input type="hidden" name="__VIEWSTATEGENERATOR" value="def456" />
          <input type="text" name="visible_field" value="should_be_ignored" />
        </form>
        """
        soup = BeautifulSoup(html, 'html.parser')
        result = StudentFileScraper._extract_viewstate(soup)
        assert result.get("__VIEWSTATE") == "abc123"
        assert result.get("__VIEWSTATEGENERATOR") == "def456"
        assert "visible_field" not in result

    def test_returns_empty_dict_when_no_hidden_fields(self):
        from bs4 import BeautifulSoup
        html = "<form><input type='text' name='foo' /></form>"
        soup = BeautifulSoup(html, 'html.parser')
        result = StudentFileScraper._extract_viewstate(soup)
        assert result == {}
