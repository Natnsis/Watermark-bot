import express from 'express';
import dotenv from 'dotenv';
import { bot } from './bot/main';
import { startCommand } from './commands/start';
import { helpCommand } from './commands/help';
import { WatermarkCommand } from './commands/watermark';
import { PreferenceCommand } from './commands/preference';
import { PostCommannd } from './commands/post';
dotenv.config();

//constants
const app = express();
const port = process.env.PORT;

startCommand(bot);
helpCommand(bot);
WatermarkCommand(bot);
PreferenceCommand(bot);
PostCommannd(bot);

bot.launch();

app.listen(port, () => {
  console.log(`🚀 Server ready at http://localhost:${port}`);
});
