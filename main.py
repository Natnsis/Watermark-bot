import logging

from telegram.ext import Application, CallbackQueryHandler, CommandHandler

from config import get_settings
from db import create_table, get_session, init_db, run_statements
from handlers.channel_watermark import channel_post_handler, watermark_conversation
from handlers.progress import progress_handler, schedule_progress_posts
from handlers.stats import stats_handler
from handlers.start import expired_button, menu_callback, start
from handlers.week_count import count_conversation, recap_conversation, schedule_monday_prompt, week_screen_handler
from health import start_health_server
from models import ActivityLog, ChannelWatermark, ProgressStyle, RecapHeading, RecapHeadingUse, WeeklyCount
from recap_headings import COMPLETION_HEADINGS, PROGRESS_HEADINGS
from services import seed_recap_headings

# create_table() never alters an existing table, so columns added later go here.
PROGRESS_STYLE_MIGRATIONS = (
    "ALTER TABLE progress_styles ALTER COLUMN style DROP NOT NULL",
    "ALTER TABLE progress_styles ADD COLUMN IF NOT EXISTS schedule VARCHAR(20) NOT NULL DEFAULT 'off'",
    "ALTER TABLE progress_styles ADD COLUMN IF NOT EXISTS last_posted_percent INTEGER",
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


async def _setup(application: Application) -> None:
    settings = get_settings()
    init_db(settings.database_url, settings.db_require_ssl)
    await create_table(ChannelWatermark)
    await create_table(WeeklyCount)
    await create_table(RecapHeading)
    await create_table(RecapHeadingUse)
    await create_table(ProgressStyle)
    await create_table(ActivityLog)
    await run_statements(PROGRESS_STYLE_MIGRATIONS)
    async with get_session() as session:
        await seed_recap_headings(session, {"completion": COMPLETION_HEADINGS, "progress": PROGRESS_HEADINGS})
    schedule_monday_prompt(application)
    schedule_progress_posts(application)
    await start_health_server()


def main() -> None:
    settings = get_settings()
    application = Application.builder().token(settings.bot_token).post_init(_setup).build()

    application.add_handler(channel_post_handler, group=-1)
    application.add_handler(watermark_conversation)
    application.add_handler(count_conversation)
    application.add_handler(recap_conversation)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(week_screen_handler)
    application.add_handler(progress_handler)
    application.add_handler(stats_handler)
    application.add_handler(CallbackQueryHandler(menu_callback, pattern=r"^menu:"))
    application.add_handler(CallbackQueryHandler(expired_button))

    application.run_polling()


if __name__ == "__main__":
    main()
