import { Telegraf, Context } from 'telegraf';
import { prisma } from '../lib/prisma';

const waitingForPost: Record<string, boolean> = {};

export const PostCommand = (bot: Telegraf<Context>) => {
  bot.command('post', async ctx => {
    const user = ctx.from;
    if (!user) return ctx.reply('Unable to fetch user data');

    const userId = user.id.toString();

    const userExists = await prisma.user.findUnique({
      where: { telegramId: userId },
    });

    if (!userExists) {
      await prisma.user.create({
        data: {
          telegramId: userId,
          name: user.first_name ?? 'unknown',
        },
      });
    }

    const refinement = await prisma.refinement.findUnique({
      where: { userId },
    });

    const optionsText = `Your refinement options are:\n` +
      `• Funny: ${refinement?.funnyRef ? '✅ Yes' : '❌ No'}\n` +
      `• Grammar: ${refinement?.grammarRef ? '✅ Yes' : '❌ No'}\n` +
      `• Professional: ${refinement?.professional ? '✅ Yes' : '❌ No'}\n` +
      `If you want to change the options, use /preference command\n\n` +
      `Please send your message now.`;

    await ctx.reply(optionsText);
    waitingForPost[userId] = true;
  });

  bot.on('text', async ctx => {
    const userId = ctx.from?.id.toString();
    const message = ctx.message.text;

    if (!userId || !waitingForPost[userId]) return;

    if (message.startsWith('/')) {
      delete waitingForPost[userId];

      await ctx.reply('🚫 Post cancelled. You can run the command now.');
      return; // do not reply with "You have sent..."
    }

    await ctx.reply(`You have sent: ${message}`);
    delete waitingForPost[userId];
  });
};
