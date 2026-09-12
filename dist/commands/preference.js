"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.PreferenceCommand = void 0;
const telegraf_1 = require("telegraf");
const prisma_1 = require("../lib/prisma");
const tempChoices = {};
const PreferenceCommand = (bot) => {
    bot.command("preference", async (ctx) => {
        const userId = ctx.from?.id.toString();
        if (!userId)
            return;
        console.log("/preference command triggered", userId);
        const existingRefinement = await prisma_1.prisma.refinement.findUnique({
            where: { userId },
        });
        if (existingRefinement) {
            await ctx.reply(`🎯 You already have saved preferences:\n` +
                `• Fix Grammar: ${existingRefinement.grammarRef ? "✅ Yes" : "❌ No"}\n` +
                `• Make it Funny: ${existingRefinement.funnyRef ? "✅ Yes" : "❌ No"}\n` +
                `• Make it Professional: ${existingRefinement.professional ? "✅ Yes" : "❌ No"}\n\n` +
                `Would you like to update them or keep them as they are?`, telegraf_1.Markup.inlineKeyboard([
                telegraf_1.Markup.button.callback("✏️ Update Preferences", "update_pref"),
                telegraf_1.Markup.button.callback("✅ Keep preferences", "keep_pref"),
            ]));
            return;
        }
        tempChoices[userId] = {};
        await ctx.reply("📖 Do you want me to fix the grammar?", telegraf_1.Markup.inlineKeyboard([
            telegraf_1.Markup.button.callback("✅ Yes", "grammar_yes"),
            telegraf_1.Markup.button.callback("❌ No", "grammar_no"),
        ]));
    });
    bot.action(/grammar_(yes|no)/, async (actionCtx) => {
        const userId = actionCtx.from.id.toString();
        tempChoices[userId].grammar = actionCtx.match[1] === "yes";
        await actionCtx.answerCbQuery();
        await actionCtx.editMessageText("😹 Do you want me to make it funnier?", telegraf_1.Markup.inlineKeyboard([
            telegraf_1.Markup.button.callback("✅ Yes", "funny_yes"),
            telegraf_1.Markup.button.callback("❌ No", "funny_no"),
        ]));
    });
    bot.action(/funny_(yes|no)/, async (actionCtx) => {
        const userId = actionCtx.from.id.toString();
        tempChoices[userId].funny = actionCtx.match[1] === "yes";
        await actionCtx.answerCbQuery();
        await actionCtx.editMessageText("☝️ Do you want me to make it professional (more formal)?", telegraf_1.Markup.inlineKeyboard([
            telegraf_1.Markup.button.callback("✅ Yes", "prof_yes"),
            telegraf_1.Markup.button.callback("❌ No", "prof_no"),
        ]));
    });
    bot.action(/prof_(yes|no)/, async (actionCtx) => {
        const userId = actionCtx.from.id.toString();
        tempChoices[userId].professional = actionCtx.match[1] === "yes";
        await actionCtx.answerCbQuery();
        const choices = tempChoices[userId];
        try {
            // Upsert to create or update preferences
            await prisma_1.prisma.refinement.upsert({
                where: { userId },
                update: {
                    funnyRef: choices.funny,
                    grammarRef: choices.grammar,
                    professional: choices.professional,
                },
                create: {
                    userId,
                    funnyRef: choices.funny,
                    grammarRef: choices.grammar,
                    professional: choices.professional,
                },
            });
        }
        catch (e) {
            console.error(e);
            await actionCtx.reply("❌ Something went wrong while saving your preferences.");
        }
        await actionCtx.editMessageText(`🎯 Your preferences have been saved/updated!\n\n` +
            `• Fix Grammar: ${choices.grammar ? "✅ Yes" : "❌ No"}\n` +
            `• Make it Funny: ${choices.funny ? "✅ Yes" : "❌ No"}\n` +
            `• Make it Professional: ${choices.professional ? "✅ Yes" : "❌ No"}\n\n` +
            `Now send /post to refine your text!`);
        // Cleanup temporary choices
        delete tempChoices[userId];
    });
    bot.action("keep_pref", async (ctx) => {
        await ctx.answerCbQuery();
        await ctx.editMessageText("Okay — your preferences remain unchanged.");
    });
    bot.action("update_pref", async (ctx) => {
        await ctx.answerCbQuery();
        const userId = ctx.from.id.toString();
        const existingRefinement = await prisma_1.prisma.refinement.findUnique({
            where: { userId },
        });
        if (!existingRefinement) {
            await ctx.reply("No preferences found to update. Send /preference to create them.");
            return;
        }
        tempChoices[userId] = {
            grammar: existingRefinement.grammarRef,
            funny: existingRefinement.funnyRef,
            professional: existingRefinement.professional,
        };
        await ctx.editMessageText("📖 Do you want me to fix the grammar?", telegraf_1.Markup.inlineKeyboard([
            telegraf_1.Markup.button.callback("✅ Yes", "grammar_yes"),
            telegraf_1.Markup.button.callback("❌ No", "grammar_no"),
        ]));
    });
};
exports.PreferenceCommand = PreferenceCommand;
