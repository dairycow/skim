"""Unit tests for ASX announcement scanner parsing."""

from unittest.mock import Mock

from skim.scanners.asx_announcements import ASXAnnouncementScanner


def test_fetch_price_sensitive_tickers_parses_pricesens_rows(mocker):
    scanner = ASXAnnouncementScanner()
    html = """
    <table>
      <tr class="pricesens"><td>BHP</td><td>Headline</td></tr>
      <tr><td>RIO</td><td>Ignored</td></tr>
      <tr class="pricesens"><td>FMG</td><td>Update</td></tr>
    </table>
    """
    response = Mock()
    response.text = html
    response.raise_for_status = Mock()
    mocker.patch("requests.get", return_value=response)

    tickers = scanner.fetch_price_sensitive_tickers()

    assert tickers == {"BHP", "FMG"}


def test_fetch_price_sensitive_tickers_handles_request_errors(mocker):
    scanner = ASXAnnouncementScanner()
    mocker.patch("requests.get", side_effect=Exception("network"))

    tickers = scanner.fetch_price_sensitive_tickers()

    assert tickers == set()
