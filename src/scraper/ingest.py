import logging
from src.scraper.fetcher import DpBossFetcher
from src.scraper.parser import DpBossParser
from src.storage.database import MatkaDatabase
from src.config import POPULAR_MARKETS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Ingestion")

def run_ingestion():
    fetcher = DpBossFetcher()
    parser = DpBossParser()
    db = MatkaDatabase()

    logger.info("Fetching homepage from dpboss.tax...")
    home_html = fetcher.fetch_home()
    if home_html:
        # 1. Ingest live status
        live_results = parser.parse_live_results(home_html)
        logger.info(f"Parsed {len(live_results)} live market results.")
        db.save_live_results(live_results)

        # 2. Ingest free game zone
        free_guesses = parser.parse_free_game_zone(home_html)
        logger.info(f"Parsed {len(free_guesses)} free game zone tips.")
        # store tips
        with db.get_connection() as conn:
            cursor = conn.cursor()
            for tip in free_guesses:
                cursor.execute("""
                INSERT INTO free_game_tips (market, fix_ank, recommended_panas, recommended_jodis, updated_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (
                    tip["market"],
                    tip["fix_ank"],
                    "-".join(tip["recommended_panas"]),
                    "-".join(tip["recommended_jodis"])
                ))
            conn.commit()

    # 3. Ingest historical panel charts for popular markets
    for market in POPULAR_MARKETS:
        slug = market["slug"]
        name = market["name"]
        logger.info(f"Fetching panel chart for {name} ({slug})...")
        chart_html = fetcher.fetch_panel_chart(slug)
        if chart_html:
            records = parser.parse_panel_chart(chart_html, name)
            inserted = db.save_historical_records(records)
            logger.info(f"Saved {inserted} historical records for {name}.")
        else:
            logger.warning(f"Could not fetch panel chart for {name}.")

    logger.info("Data ingestion completed successfully!")

if __name__ == "__main__":
    run_ingestion()
