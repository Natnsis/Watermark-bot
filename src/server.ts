import express from 'express';
import dotenv from 'dotenv';
dotenv.config();

import { Telegraf } from 'telegraf';
import { startCommand } from './commands/start';
import { PostCommand } from './commands/post';
import { PreferenceCommand } from './commands/preference';
import { WatermarkCommand } from './commands/watermark';
import { helpCommand } from './commands/help';

const app = express();

const bot = new Telegraf(process.env.BOT_TOKEN!);

startCommand(bot);
PostCommand(bot);
PreferenceCommand(bot);
WatermarkCommand(bot);
helpCommand(bot);

bot.launch();

app.listen(process.env.PORT, () => {
  console.log(`server running on port ${process.env.PORT}`);
});
