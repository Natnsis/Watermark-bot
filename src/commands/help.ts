import { Telegraf, Context } from 'telegraf';

export const helpCommand = (bot: Telegraf<Context>) => {
  bot.help(ctx => {
    ctx.reply('help yourself🙂‍↔️');
  });
};
