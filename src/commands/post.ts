import { Telegraf, Context } from 'telegraf';
import { prisma } from '../lib/prisma';

type UserData = {
  id: string;
  first_name: string;
};

export const PostCommand = (bot: Telegraf<Context>) => {
  bot.command('post', async ctx => {
    try {
      const user: UserData = ctx.from;
      if (!user) return ctx.reply('unable to fetch user data');

      //check existance
      const exists = await prisma.user.findMany({
        where: { telegramId: user.id },
      });

      if (!exists) {
        await prisma.user.create({
          data: {
            telegramId: user.id,
            name: user.first_name ?? 'unknown',
          },
        });
        await ctx.reply(`user has been saved with id of ${user.id}`);
      }
    } catch (e) {
      console.log(e);
    }
  });
};
