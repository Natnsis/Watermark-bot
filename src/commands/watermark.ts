import { Telegraf, Context } from 'telegraf';

export const WatermarkCommand = (bot: Telegraf<Context>) => {
  bot.command('watermark', ctx => {
    ctx.reply('send your channel url');
  });
};
