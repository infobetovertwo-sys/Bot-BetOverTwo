"""
Ponto de entrada do projeto — arranca o bot do Telegram.
Este é o ficheiro que o Railway vai executar continuamente.
"""

import asyncio
import db
import bot as bot_module


async def main():
    db.init_db()
    await bot_module.dp.start_polling(bot_module.bot)


if __name__ == "__main__":
    asyncio.run(main())
