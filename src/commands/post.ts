import { Telegraf, Context } from 'telegraf';
import { prisma } from '../lib/prisma';

export const PostCommand = (bot: Telegraf<Context>) => {
  bot.command('post', async ctx => {
    try {
      const user = ctx.from;
      if (!user) return ctx.reply('Unable to fetch user data');

      const userExists = await prisma.user.findUnique({
        where: { telegramId: user.id.toString() },
      });

      if (!userExists) {
        await prisma.user.create({
          data: {
            telegramId: user.id.toString(),
            name: user.first_name ?? 'unknown',
          },
        });
      }
      await ctx.reply('alright send your post text');
      bot.on('text', async (ctx) => {
        const message = ctx.message.text;
        await ctx.reply(`you have sent ${message}`)
      })

    } catch (e) {
      console.error(e);
      await ctx.reply('An error occurred while processing your request.');
    }
  });
};
