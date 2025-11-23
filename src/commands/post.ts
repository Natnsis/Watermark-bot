import { Telegraf, Context } from 'telegraf';

export const PostCommannd = (bot: Telegraf<Context>) => {
  bot.command('post', ctx => {
    ctx.reply('posts');
  });
};
