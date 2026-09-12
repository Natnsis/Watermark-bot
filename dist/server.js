"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const express_1 = __importDefault(require("express"));
const dotenv_1 = __importDefault(require("dotenv"));
dotenv_1.default.config();
const telegraf_1 = require("telegraf");
const prisma_1 = require("./lib/prisma");
const start_1 = require("./commands/start");
const post_1 = require("./commands/post");
const preference_1 = require("./commands/preference");
const watermark_1 = require("./commands/watermark");
const help_1 = require("./commands/help");
const settings_1 = require("./commands/settings");
const app = (0, express_1.default)();
const bot = new telegraf_1.Telegraf(process.env.BOT_TOKEN);
// Register commands
[start_1.startCommand, post_1.PostCommand, preference_1.PreferenceCommand, watermark_1.WatermarkCommand, help_1.helpCommand, settings_1.SettingsCommand].forEach((command) => command(bot));
// Helper function to safely get text or caption
const getPostContent = (post) => {
    if (!post)
        return null;
    if ("text" in post && typeof post.text === "string")
        return { type: "text", content: post.text };
    if ("caption" in post && typeof post.caption === "string")
        return { type: "caption", content: post.caption };
    return null;
};
// Handle channel posts and append watermark
bot.on("channel_post", async (ctx) => {
    const post = ctx.channelPost;
    const chat = post?.chat;
    if (!chat || !post)
        return;
    const telegramId = chat.id.toString();
    const messageId = post.message_id;
    if (!messageId)
        return;
    try {
        const channel = await prisma_1.prisma.channel.findUnique({ where: { telegramId } });
        if (!channel)
            return;
        const watermark = await prisma_1.prisma.watermark.findFirst({
            where: { channelId: channel.id },
            orderBy: { id: "desc" },
        });
        if (!watermark)
            return;
        const postContent = getPostContent(post);
        if (!postContent)
            return;
        if (postContent.type === "text") {
            await bot.telegram.editMessageText(chat.id, messageId, undefined, `${postContent.content}\n\n${watermark.text}`, {
                parse_mode: "Markdown",
            });
        }
        else if (postContent.type === "caption") {
            await bot.telegram.editMessageCaption(chat.id, messageId, undefined, `${postContent.content}\n\n${watermark.text}`, {
                parse_mode: "Markdown",
            });
        }
    }
    catch (error) {
        console.error("Unable to append watermark to channel post:", error);
    }
});
// Health check endpoint
app.get("/health", (_req, res) => {
    res.json({ message: "server is healthy" });
});
bot.launch();
app.listen(process.env.PORT, () => {
    console.log(`Server running on port ${process.env.PORT}`);
});
