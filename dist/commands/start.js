"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.startCommand = void 0;
const startCommand = (bot) => {
    bot.start((ctx) => {
        ctx.replyWithPhoto("https://res.cloudinary.com/dp1o87p4c/image/upload/v1763707685/84b992d4-a5f2-4dfd-b4bb-3c3311b67bbb.png", {
            caption: `👋Hello I'm **Poster Boi**! \n\n` +
                `I help you turn your text into polished posts: \n` +
                `• Correct grammar and spelling   \n` +
                `• Refine style and improve readability \n` +
                `• Add custom improvements based on your preferences  \n` +
                `• After admin approval, automatically attach a watermark at the end whenever you post a message on your telegram channel \n \n` +
                `Perfect for creating clean posts for Telegram channels or social media! \n \n` +
                `Here is what i can do: \n` +
                `🌟 /start - Show this Welcome message \n` +
                `📋 /help - List all Commands \n` +
                `😸 /preference - Select your post refinment Preferences (grammar by default) \n` +
                `🔗 /watermark - Add a watermark to your messages in your channel \n` +
                `🤖 /post - To refine your messages with your preferences`,
            parse_mode: "Markdown",
        });
    });
};
exports.startCommand = startCommand;
