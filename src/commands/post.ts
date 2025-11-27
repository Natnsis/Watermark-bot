import { Telegraf, Context, Markup } from 'telegraf';
import { prisma } from '../lib/prisma';

const waitingForPost: Record<string, boolean> = {};

export const PostCommand = (bot: Telegraf<Context>) => {
  bot.command('post', async ctx => {
    try {
      const user = ctx.from;
      if (!user) return ctx.reply('Unable to fetch user data');

      const userId = user.id.toString();

      // Ensure the user exists
      const userExists = await prisma.user.findUnique({ where: { telegramId: userId } });
      if (!userExists) {
        await prisma.user.create({
          data: { telegramId: userId, name: user.first_name ?? 'unknown' },
        });
      }

      const refinement = await prisma.refinement.findUnique({ where: { userId } });

      // Show current preferences
      const optionsText = `Your refinement options are:\n` +
        `• Funny: ${refinement?.funnyRef ? '✅ Yes' : '❌ No'}\n` +
        `• Grammar: ${refinement?.grammarRef ? '✅ Yes' : '❌ No'}\n` +
        `• Professional: ${refinement?.professional ? '✅ Yes' : '❌ No'}\n\n` +
        `Do you want to edit them or are they fine?`;

      await ctx.reply(
        optionsText,
        Markup.inlineKeyboard([
          Markup.button.callback('✏️ Edit Preferences', 'edit_pref_post'),
          Markup.button.callback('✅ Preferences are fine', 'confirm_pref_post'),
        ])
      );
    } catch (e) {
      console.error(e);
      await ctx.reply('An error occurred while processing your request.');
    }
  });

  // Handle "Edit Preferences" click
  bot.action('edit_pref_post', async actionCtx => {
    await actionCtx.answerCbQuery();
    await actionCtx.reply('Please use /preference to edit your preferences.');
  });

  // Handle "Preferences are fine" click
  bot.action('confirm_pref_post', async actionCtx => {
    const userId = actionCtx.from.id.toString();
    await actionCtx.answerCbQuery();
    await actionCtx.editMessageText('Great! Now send your message.');
    waitingForPost[userId] = true;
  });

  // Handle text messages
  bot.on('text', async ctx => {
    const userId = ctx.from?.id.toString();
    if (!userId || !waitingForPost[userId]) return;

    const message = ctx.message.text;
    await ctx.reply(`You have sent: ${message}`);

    // Clear the waiting state
    delete waitingForPost[userId];
  });
};
