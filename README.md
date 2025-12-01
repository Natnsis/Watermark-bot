# Watermark Bot 🤖🖼️

**Automated Watermark & AI Text Refinement Bot for Telegram Channels**

![Watermark Bot Demo](https://raw.githubusercontent.com/Natnsis/Watermark-bot/main/assets/demo-watermarked.jpg)

Watermark Bot helps Telegram channel owners **automatically add watermarks** to media files and **refine text using AI (Gemini API)** before posting.  
It stores your preferences using **Prisma ORM + Neon PostgreSQL** — smooth, fast, and persistent.

## ✨ Features

### 🖼️ Automatic Watermarking
- Adds watermarks to **photos , videos & texts**
- Save your **default watermark** (one per user)

### 🤖 AI Text Refinement (Google Gemini)
Choose your style:
- Grammar Correction ✍️
- Professional Rewrite 💼
- Funnier Text 📝
- Emoji-Friendly Caption 😎✨

### 💾 Database Persistence
- Powered by **Neon PostgreSQL** + **Prisma ORM**
- Saves:
  - Default watermark URL
  - Preferred text style

### 🔁 Seamless Telegram Workflow
- Forward media → bot adds watermark → returns ready-to-post version
- Forward text → bot refines with AI → get polished caption
- Fast. Simple. Reliable.

## 🧰 Tech Stack

| Layer               | Technology                  |
|---------------------|-----------------------------|
| Bot Engine          | Node.js + Telegraf          |
| AI Processing       | Google Gemini API           |
| Database            | Neon PostgreSQL             |
| ORM                 | Prisma                      |
| Media Processing    | FFmpeg                      |
| Runtime             | Node.js 18+                 |

## 📥 Installation & Setup

```bash
# 1. Clone
git clone https://github.com/Natnsis/Watermark-bot.git
cd Watermark-bot

# 2. Install
npm install

# 3. Create .env
cp .env.example .env
# Then edit .env with your keys
BOT_TOKEN=your_telegram_bot_token
GEMINI_API_KEY=your_gemini_api_key
DATABASE_URL="postgresql://user:pass@ep-cool-name.us-east-2.aws.neon.tech/db?sslmode=require"
DIRECT_URL="postgresql://user:pass@ep-cool-name.us-east-2.aws.neon.tech/db?sslmode=require"
# 4. Install FFmpeg
# Linux
sudo apt install ffmpeg

# Windows: Download from https://ffmpeg.org and add to PATH

# 5. Prisma setup
npx prisma migrate deploy
npx prisma generate

# 6. Run
npm start

```
## 📌 Usage

### 🖼️ Add Watermark to Photos & Videos
1. Send anything containig image on your channel for post
2. The bot instantly applies your **default watermark**  

### 📝 Refine Text with AI (Gemini)
1. Send or forward any text/caption  
2. Choose one of the styles from the menu:  
   • Grammar Correction ✍️  
   • Professional Rewrite 💼  
   • Funnier Version 📝  
3. Get a perfectly polished caption in seconds!

### ⚙️ Set Your Defaults (Saved Forever)

#### Set Default Watermark
- Forward a post from the channel so that the bot can pick your channel 
- Send the water mark to be added on posts (bot must be admin in your chanel with edit permisson for it to wor)
- 
→ Saved in the database and used automatically from now on.

#### Change Preferred AI Style
- Only Grammar by default
- The bot remembers it for all future text refinements  
→ No need to choose every time!


### 🚀 Bonus Commands
| Command              | Description                              |
|----------------------|------------------------------------------|
| `/start`             | Show welcome message & quick guide       |
| `/help`              | List all features & commands             |
| `/watermark`         | Set default watermark to be sent on the channel |
| `/post`           | Send text that you want to be refined |
| `/preferences`    | Apply preferred refinement method            |

That’s it — no complicated menus, no extra apps.  
Just forward → get perfect content → post to your channel. Fast & effortless! 🚀
