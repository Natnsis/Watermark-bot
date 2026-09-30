import logging

from telegram.ext import Application, CallbackQueryHandler, CommandHandler

from config import get_settings
from db import create_table, init_db
from handlers.channel_watermark import channel_post_handler, watermark_conversation
from handlers.start import expired_button, menu_callback, start
from handlers.week_count import count_conversation, recap_conversation, schedule_monday_prompt, week_screen_handler
from models import ChannelWatermark, WeeklyCount

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


async def _setup(application: Application) -> None:
    settings = get_settings()
    init_db(settings.database_url, settings.db_require_ssl)
    await create_table(ChannelWatermark)
    await create_table(WeeklyCount)
    schedule_monday_prompt(application)


def main() -> None:
    settings = get_settings()
    application = Application.builder().token(settings.bot_token).post_init(_setup).build()

    application.add_handler(channel_post_handler, group=-1)
    application.add_handler(watermark_conversation)
    application.add_handler(count_conversation)
    application.add_handler(recap_conversation)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(week_screen_handler)
    application.add_handler(CallbackQueryHandler(menu_callback, pattern=r"^menu:"))
    application.add_handler(CallbackQueryHandler(expired_button))

    application.run_polling()


if __name__ == "__main__":
    main()
