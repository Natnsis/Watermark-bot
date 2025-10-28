import express from 'express';
import dotenv from 'dotenv';
import { bot } from './bot/middlewares/telegraph.middleware';

dotenv.config();

//constants
const app = express();
const port = process.env.PORT;

bot.start(ctx => {
  ctx.replyWithPhoto('https://placekitten.com/600/300', {
    caption: `
🌊 *Welcome to Poster Boi!* 🧢  
This bot helps you auto-style, watermark, and polish your posts before sharing.

Choose what you want to do:
    `,
    parse_mode: 'Markdown',
    reply_markup: {
      inline_keyboard: [
        [{ text: '🖋 Add Watermark', callback_data: 'add_watermark' }],
        [{ text: '🎨 Style Options', callback_data: 'style_options' }],
        [{ text: 'ℹ️ About', callback_data: 'about' }],
      ],
    },
  });
});

bot.action('add_watermark', ctx => {
  ctx.reply('Please send me your watermark text 🩶');
});

bot.action('style_options', ctx => {
  ctx.reply(
    'Choose a style:\n\n1️⃣ Funny\n2️⃣ Serious\n3️⃣ Professional\n4️⃣ Playful'
  );
});

bot.action('about', ctx => {
  ctx.reply('👋 Poster Boi — built with ❤️ using TypeScript and Telegraf!');
});

bot.launch();

app.listen(port, () => {
  console.log(`🚀 Server ready at http://localhost:${port}`);
});
