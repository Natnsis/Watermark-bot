import { Telegraf, Context } from 'telegraf';

export const PreferenceCommand = (bot: Telegraf<Context>) => {
  bot.command('preference', ctx => {
    ctx.reply('choose a reference:');
  });
};
