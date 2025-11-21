import { Telegraf, Context } from 'telegraf';

export const PostCommand = (bot: Telegraf<Context>) => {
  bot.command('post', ctx => {
    ctx.reply('send the text you want to refine');
  });
};
