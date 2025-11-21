import { Telegraf, Context } from 'telegraf';

export const startCommand = (bot: Telegraf<Context>) => {
  bot.start(ctx => {
    ctx.replyWithPhoto(
      'https://res.cloudinary.com/dp1o87p4c/image/upload/f_auto,q_auto/v1763706378/Arcade_decay_red_zd9eqi.png',
      { caption: 'Welcome to the bot!' }
    );
  });
};
