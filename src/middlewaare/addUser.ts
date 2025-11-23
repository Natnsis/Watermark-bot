import { Context, Telegraf } from 'telegraf';
import { prisma } from '../bot/prisma';

export const register = (bot: Telegraf<Context>) => {
  bot.use(async (ctx, next) => {
    if (ctx.from) {
      await prisma.user.upsert({
        where: { tgId: BigInt(ctx.from.id) },
        update: {},
        create: {
          tgId: BigInt(ctx.from.id),
          username: ctx.from.username,
          firstName: ctx.from.first_name,
          lastName: ctx.from.last_name,
        },
      });
    }
    return next();
  });
};
