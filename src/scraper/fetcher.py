import httpx
import logging
from typing import Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,hi;q=0.8",
}

class DpBossFetcher:
    def __init__(self, base_url: str = "https://dpboss.tax", timeout: int = 15):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def fetch_url(self, url: str) -> Optional[str]:
        try:
            with httpx.Client(headers=HEADERS, timeout=self.timeout, follow_redirects=True, verify=False) as client:
                response = client.get(url)
                if response.status_code == 200:
                    return response.text
                logger.warning(f"Failed to fetch {url}, status code: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Error fetching URL {url}: {e}")
            return None

    def fetch_home(self) -> Optional[str]:
        return self.fetch_url(f"{self.base_url}/")

    def fetch_panel_chart(self, slug: str) -> Optional[str]:
        url = f"{self.base_url}/panel-chart-record/{slug}.php"
        return self.fetch_url(url)

    def fetch_jodi_chart(self, slug: str) -> Optional[str]:
        url = f"{self.base_url}/jodi-chart-record/{slug}.php"
        return self.fetch_url(url)
