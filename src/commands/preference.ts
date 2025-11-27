import { Telegraf, Context, Markup } from 'telegraf';
import { prisma } from '../lib/prisma';

export const PreferenceCommand = (bot: Telegraf<Context>) => {
  bot.command('preference', async ctx => {
    const userChoices: {
      grammar?: boolean;
      funny?: boolean;
      professional?: boolean;
    } = {};

    await ctx.reply(
      'Do you want me to fix the grammar?📖',
      Markup.inlineKeyboard([
        Markup.button.callback('Yes', 'grammar_yes'),
        Markup.button.callback('No', 'grammar_no'),
      ])
    );

    bot.action(/grammar_(yes|no)/, async actionCtx => {
      userChoices.grammar = actionCtx.match[1] === 'yes' ? true : false;
      await actionCtx.answerCbQuery();

      await actionCtx.editMessageText(
        'Do you want me to make it funnier?😹',
        Markup.inlineKeyboard([
          Markup.button.callback('Yes', 'funny_yes'),
          Markup.button.callback('No', 'funny_no'),
        ])
      );
    });

    bot.action(/funny_(yes|no)/, async actionCtx => {
      userChoices.funny = actionCtx.match[1] === 'yes' ? true : false;
      await actionCtx.answerCbQuery();

      await actionCtx.editMessageText(
        'Do you want me to make it professional?(too formal)☝️',
        Markup.inlineKeyboard([
          Markup.button.callback('Yes', 'prof_yes'),
          Markup.button.callback('No', 'prof_no'),
        ])
      );
    });

    bot.action(/prof_(yes|no)/, async actionCtx => {
      userChoices.professional = actionCtx.match[1] === 'yes' ? true : false;
      await actionCtx.answerCbQuery();
      const user = ctx.from;
      await prisma.refinement.create({
        data: {
          userId: user.id.toString(),
          funnyRef: userChoices.funny!,
          grammarRef: userChoices.grammar!,
          professional: userChoices.professional!,
        }
      })
      await actionCtx.editMessageText(
        `Your choices:\n- Fix Grammar: ${userChoices.grammar}\n- Make it Funny: ${userChoices.funny}\n- Make it Professional: ${userChoices.professional}\n \n /post so i can refine your text now`
      );
    });
  });
};

/*
  userId       Int
  description  String?
  funnyRef     Boolean
  grammarRef   Boolean
  professional Boolean
*/
