import { Telegraf, Context, Markup } from 'telegraf';
import { prisma } from '../lib/prisma';

const tempChoices: Record<string, { grammar?: boolean; funny?: boolean; professional?: boolean }> = {};

export const PreferenceCommand = (bot: Telegraf<Context>) => {

  bot.command('preference', async ctx => {
    const userId = ctx.from?.id.toString();
    if (!userId) return;

    console.log('/preference command triggered', userId);

    const existingRefinement = await prisma.refinement.findUnique({ where: { userId } });
    if (existingRefinement) {
      await ctx.reply(
        `🎯 You already have saved preferences:\n` +
        `• Fix Grammar: ${existingRefinement.grammarRef ? '✅ Yes' : '❌ No'}\n` +
        `• Make it Funny: ${existingRefinement.funnyRef ? '✅ Yes' : '❌ No'}\n` +
        `• Make it Professional: ${existingRefinement.professional ? '✅ Yes' : '❌ No'}\n\n` +
        `Send /preference again if you want to update them.`
      );
      return;
    }

    tempChoices[userId] = {};

    await ctx.reply(
      '📖 Do you want me to fix the grammar?',
      Markup.inlineKeyboard([
        Markup.button.callback('✅ Yes', 'grammar_yes'),
        Markup.button.callback('❌ No', 'grammar_no'),
      ])
    );
  });

  bot.action(/grammar_(yes|no)/, async actionCtx => {
    const userId = actionCtx.from.id.toString();
    tempChoices[userId].grammar = actionCtx.match[1] === 'yes';
    await actionCtx.answerCbQuery();

    await actionCtx.editMessageText(
      '😹 Do you want me to make it funnier?',
      Markup.inlineKeyboard([
        Markup.button.callback('✅ Yes', 'funny_yes'),
        Markup.button.callback('❌ No', 'funny_no'),
      ])
    );
  });

  bot.action(/funny_(yes|no)/, async actionCtx => {
    const userId = actionCtx.from.id.toString();
    tempChoices[userId].funny = actionCtx.match[1] === 'yes';
    await actionCtx.answerCbQuery();

    await actionCtx.editMessageText(
      '☝️ Do you want me to make it professional (more formal)?',
      Markup.inlineKeyboard([
        Markup.button.callback('✅ Yes', 'prof_yes'),
        Markup.button.callback('❌ No', 'prof_no'),
      ])
    );
  });

  bot.action(/prof_(yes|no)/, async actionCtx => {
    const userId = actionCtx.from.id.toString();
    tempChoices[userId].professional = actionCtx.match[1] === 'yes';
    await actionCtx.answerCbQuery();

    const choices = tempChoices[userId];

    try {
      await prisma.refinement.upsert({
        where: { userId },
        update: {
          funnyRef: choices.funny!,
          grammarRef: choices.grammar!,
          professional: choices.professional!,
        },
        create: {
          userId,
          funnyRef: choices.funny!,
          grammarRef: choices.grammar!,
          professional: choices.professional!,
        },
      });
    } catch (e) {
      console.error(e);
      await actionCtx.reply('❌ Something went wrong while saving your preferences.');
    }

    await actionCtx.editMessageText(
      `🎯 Your preferences have been saved/updated!\n\n` +
      `• Fix Grammar: ${choices.grammar ? '✅ Yes' : '❌ No'}\n` +
      `• Make it Funny: ${choices.funny ? '✅ Yes' : '❌ No'}\n` +
      `• Make it Professional: ${choices.professional ? '✅ Yes' : '❌ No'}\n\n` +
      `Now send /post to refine your text!`
    );

    delete tempChoices[userId];
  });
};
