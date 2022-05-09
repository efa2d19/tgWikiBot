import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton

import wikipediaapi
import wikipedia

from dotenv import dotenv_values
from attr import attrs, attrib

config = dotenv_values('.env')

wiki = wikipediaapi.Wikipedia('ru')

API_TOKEN = config.get('TOKEN')

knownUsers = []  # todo: save these in a file,
userStep = {}  # so they won't reset every time the bot restarts

commands = {  # command description used in the "help" command
    'start': 'Начало общения с ботом',
    'help': 'Выдает список доступных команд',
    'search': 'Поиск в Википедии',
    'random': 'Рандомная статья из википедии'
}


# error handling if user isn't known yet
# (obsolete once known users are saved to file, because all users
#   had to use the /start command and are therefore known to the bot)
def get_user_step(uid):
    if uid in userStep:
        return userStep[uid]
    else:
        knownUsers.append(uid)
        userStep[uid] = 0
        print("New user detected, who hasn't used \"/start\" yet")
        return 0


# only used for console output now
def listener(messages):
    """
    When new messages arrive TeleBot will call this function.
    """
    for m in messages:
        if m.content_type == 'text':
            # print the sent message to the console
            print(str(m.chat.first_name) + " [" + str(m.chat.id) + "]: " + m.text)


bot = telebot.TeleBot(API_TOKEN)
bot.set_update_listener(listener)  # register listener


def set_my_commands():
    bot.delete_my_commands(scope=None, language_code=None)
    commands_list = list()
    for key in commands:
        commands_list.append(telebot.types.BotCommand(key, commands[key]))
    bot.set_my_commands(commands_list)


def keyboard(key_type: str = 'default'):
    markup = ReplyKeyboardMarkup(row_width=3)
    if key_type == 'default':
        markup.add(
            KeyboardButton('🔍Поиск'),
            KeyboardButton('🎲Рандом'),
            KeyboardButton('🛟Помощь'),
        )
    if key_type == 'back':
        markup.add(
            KeyboardButton('✅На главную'),
        )
    if key_type == 'search':
        markup.add(
            KeyboardButton('Картинки'),
            KeyboardButton('Ссылки'),
            KeyboardButton('🔙Назад'),
            KeyboardButton('✅На главную'),
        )
    # if key_type == "random":
    #     markup.add(
    #         KeyboardButton("Рандом"),
    #         KeyboardButton("🔙Назад"),
    #     )
    return markup


# handle the "/start" command
@bot.message_handler(commands=['start'])
def command_start(m):
    cid = m.chat.id
    set_my_commands()
    if cid not in knownUsers:
        knownUsers.append(cid)
        userStep[cid] = 0
        bot.send_message(
            cid,
            "Привет, я бот для поиска в Википедии",
            reply_markup=keyboard()
        )
    else:
        bot.send_message(
            cid,
            "Не нужно заново писать /start 🐸"
        )


@bot.message_handler(commands=['help'])
def command_help(m):
    cid = m.chat.id
    help_text = "Доступные команды: \n"
    for key in commands:
        help_text += "/" + key + ": "
        help_text += commands[key] + "\n"
    bot.send_message(
        cid,
        help_text
    )


@attrs
class WikiSearch:
    wiki_results_title = attrib(default=None)
    wiki_results_summary = attrib(default=None)

    def wiki_search(self, query):
        self.wiki_results_title = wiki.page(query).title
        self.wiki_results_summary = wiki.page(query).summary


WikiSearchInstance = WikiSearch()


@bot.message_handler(commands=['search'])
def search(m):
    cid = m.chat.id
    bot.send_message(
        cid,
        "Отправь в ответ свой запрос, чтобы я нашел статью",
        reply_markup=keyboard('back')
    )
    userStep[cid] = 'search_screen'


@bot.message_handler(func=lambda message: get_user_step(message.chat.id) == 'search_screen')
def search_screen(m):
    cid = m.chat.id
    text = m.text

    bot.send_chat_action(cid, 'typing')

    if text == '✅На главную':
        bot.send_message(
            cid,
            "Используй клавиатуру для выбора действий!",
            reply_markup=keyboard(),
        )
        userStep[cid] = 0
    else:
        WikiSearchInstance.wiki_search(text)
        bot.send_message(
            cid,
            WikiSearchInstance.wiki_results_summary,
            reply_markup=keyboard('search'),
        )
        userStep[cid] = 'search_screen_results'


@bot.message_handler(func=lambda message: get_user_step(message.chat.id) == 'search_screen_results')
def search_screen_results(m):
    cid = m.chat.id
    text = m.text

    bot.send_chat_action(cid, 'typing')

    match text:
        case '🔙Назад':
            bot.send_message(
                cid,
                "Отправь в ответ свой запрос, чтобы я нашел статью",
                reply_markup=keyboard('back')
            )
            userStep[cid] = 'search_screen'
        case '✅На главную':
            bot.send_message(
                cid,
                "Используй клавиатуру для выбора действий!",
                reply_markup=keyboard(),
            )
            userStep[cid] = 0
        case 'Картинки':
            try:
                found_images = wikipedia.page(WikiSearchInstance.wiki_results_title).images
            except Exception:
                found_images = None
            if found_images:
                bot.send_message(
                    cid,
                    "Вот картинки, которые я смог найти:",
                )
                bot.send_message(
                    cid,
                    found_images,
                )
            else:
                bot.send_message(
                    cid,
                    "Я не смог найти картинки 💩",
                )
            userStep[cid] = 'search_screen_results'
        case 'Ссылки':
            try:
                found_links = wikipedia.page(WikiSearchInstance.wiki_results_title).links
            except Exception:
                found_links = None
            if found_links:
                bot.send_message(
                    cid,
                    "Вот ссылки, которые я смог найти:",
                )
                bot.send_message(
                    cid,
                    found_links,
                )
            else:
                bot.send_message(
                    cid,
                    "Я не смог найти ссылки 💩",
                )
            userStep[cid] = 'search_screen_results'
        case _:
            bot.send_message(
                cid,
                "Используй клавиатуру для выбора действий!"
            )


# @bot.message_handler(commands=['random'])
# def random(m):
#     cid = m.chat.id
#     bot.send_message(
#         cid,
#         "Please choose your image now",
#         reply_markup=keyboard('random')
#     )
#     userStep[cid] = 'random'

# @bot.message_handler(func=lambda message: get_user_step(message.chat.id) == 'random')
# def random_screen(m):
#     cid = m.chat.id
#     text = m.text
#
#     bot.send_chat_action(cid, 'typing')
#
#     if text == '🔙Назад':
#         userStep[cid] = 0
#     else:
#         bot.send_message(cid, "Используй клавиатуру для выбора действий!")


@bot.message_handler(func=lambda message: True, content_types=['text'])
def command_default(m):
    cid = m.chat.id
    text = m.text
    match text:
        case '🔍Поиск':
            search(m)
        # case '🎲Рандом':
        #     random(m)
        case '🛟Помощь':
            command_help(m)
        case _:
            bot.send_message(
                cid,
                f'Не понимаю команду "{text}"\nСписок команд в /help'
            )


if __name__ == '__main__':
    bot.infinity_polling()
