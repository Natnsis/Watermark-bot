"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.helpCommand = void 0;
const helpCommand = (bot) => {
    bot.help((ctx) => {
        ctx.reply(`🌟 *Poster Boi — Your Post Refinement Assistant* \n\n` +
            `I help you craft polished, publish-ready posts and optionally attach a watermark to posts in your channels. Use the commands below to get started.` +
            `\n\n*Quick commands:*\n` +
            `• /start — Welcome message and quick overview\n` +
            `• /help — This message\n` +
            `• /preference — Choose how I refine posts (grammar, funny, professional)\n` +
            `• /post — Compose a post and get a polished result from the AI\n` +
            `• /watermark — Register a channel and set a watermark to automatically attach to channel posts\n\n` +
            `---\n*How /post works* 🤖\n` +
            `1) Send \/post in private chat — I'll show your current preferences.\n` +
            `2) Confirm or edit preferences.\n` +
            `3) When prompted, send the text you want refined.\n` +
            `4) I’ll show a loading indicator, call the AI (Gemini), and return the refined text.\n` +
            `_Example:_\nOriginal: "i is running around yesterday, then a dog bit me"\nRefined: "I was walking yesterday when a dog came up to me and bit me. The neighbors helped me get away."\n\n` +
            `---\n*How /watermark works* 🔖\n` +
            `1) Send \/watermark in private chat.\n` +
            `2) Forward any message from your channel OR send the channel username (eg. @mychannel) so I can find and save the channel ID.\n` +
            `3) I’ll ask for the watermark text (short signature or caption) and save it.\n` +
            `4) Add me to the channel as admin with permission to edit messages — this is required for me to append the watermark to messages posted in that channel.\n` +
            `_Note:_ Watermarking works by editing channel posts; if the bot doesn’t have edit rights, it won’t be able to attach the watermark.\n\n` +
            `---\n*Tips & Troubleshooting* ⚠️\n` +
            `• Use \/settings to test your AI model connection (Gemini) and confirm your API key is valid.\n` +
            `• If you see your original text returned unchanged, the AI key may be missing or invalid — check \.env and run \/settings.\n` +
            `• For professional posts, choose the "Professional" preference to avoid emojis; for lighter/funny posts, select "Funny".\n\n` +
            `If you need help, send /help or message the bot owner. Happy posting!`, { parse_mode: "Markdown" });
    });
};
exports.helpCommand = helpCommand;
