import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton

import wikipediaapi
import wikipedia  # For images

from dotenv import dotenv_values, set_key, get_key
from attr import attrs, attrib

config = dotenv_values('.env')  # Get envs from .env file

wiki = wikipediaapi.Wikipedia('ru')  # Sets language to api

API_TOKEN = config.get('TOKEN')

knownUsers = eval(get_key('.env', 'knownUsers'))
userStep = eval(get_key('.env', 'userStep'))  # so they won't reset every time the bot restarts

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
        print('New user detected, who hasn\'t used "/start" yet')
        return 0


# only used for console output now
def listener(messages):
    """
    When new messages arrive TeleBot will call this function.
    """
    for m in messages:
        if m.content_type == 'text':
            # print the sent message to the console
            print(f'{str(m.chat.first_name)} [{str(m.chat.id)}]: {m.text}')


bot = telebot.TeleBot(API_TOKEN)
bot.set_update_listener(listener)  # register listener


def set_my_commands():
    bot.delete_my_commands(scope=None, language_code=None)
    commands_list = list()
    for key in commands:
        commands_list.append(telebot.types.BotCommand(key, commands[key]))
    bot.set_my_commands(commands_list)


def create_keyboard(buttons: list, row_width: int = 2):
    markup = ReplyKeyboardMarkup(row_width=row_width)
    button_list = list()
    for button in buttons:
        button_list.append(KeyboardButton(button))
    markup.add(*button_list)
    return markup


# Button's text (bot wide)
class ButtText:
    keyboard_search = '🔍 Поиск'
    keyboard_random = '🎲 Рандом'
    keyboard_help = '🛟 Помощь'
    keyboard_main = '✅ На главную'
    keyboard_pics = '🌄 Картинки'
    keyboard_links = '🔗 Ссылки'
    keyboard_back = '↪  ️Назад'
    keyboard_random_wiki = '🎲 Рандомная статья'
    next_page_button = '👉🏻 След. страница'
    back_page_button = '👈🏻 Пред. страница'


def keyboard(key_type: str = 'default'):
    if key_type == 'default':
        return create_keyboard([ButtText.keyboard_search, ButtText.keyboard_random, ButtText.keyboard_help])
    if key_type == 'back':
        return create_keyboard([ButtText.keyboard_main])
    if key_type == 'search':
        return create_keyboard(
            [ButtText.keyboard_pics, ButtText.keyboard_links, ButtText.keyboard_back, ButtText.keyboard_main])
    if key_type == 'search_links':
        return create_keyboard([ButtText.keyboard_pics, ButtText.keyboard_back, ButtText.keyboard_main])
    if key_type == "random":
        return create_keyboard([ButtText.keyboard_random_wiki, ButtText.keyboard_main])


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
            'Привет, я бот для поиска в Википедии',
            reply_markup=keyboard()
        )
        set_key('.env', 'knownUsers', str(knownUsers))
    else:
        bot.send_message(
            cid,
            'Не нужно заново писать /start 🐸'
        )


# handle the "/stop" command
@bot.message_handler(commands=['stop'])
def command_stop(m):
    cid = m.chat.id
    if cid in knownUsers:
        knownUsers.remove(cid)
        set_key('.env', 'knownUsers', str(knownUsers))


@bot.message_handler(commands=['help'])
def command_help(m):
    cid = m.chat.id
    help_text = 'Доступные команды: \n'
    for key in commands:
        help_text += f'/{key}: '
        help_text += f'{commands[key]}\n'
    bot.send_message(
        cid,
        help_text
    )


@attrs
class WikiSearch:
    wiki_results_title = attrib(default=None)
    wiki_results_summary = attrib(default=None)
    wiki_results_links = attrib(default=None)

    def wiki_search(self, query):
        self.wiki_results_title = wiki.page(query).title
        self.wiki_results_summary = wiki.page(query).summary
        self.wiki_results_links = wiki.page(query).links


WikiSearchInstance = WikiSearch()
WikiSearchInstance2 = WikiSearch()


@bot.message_handler(commands=['search'])
def search(m):
    cid = m.chat.id
    bot.send_message(
        cid,
        'Отправь в ответ свой запрос, чтобы я нашел статью',
        reply_markup=keyboard('back')
    )
    userStep[cid] = 'search_screen'
    set_key('.env', 'userStep', str(userStep))


@bot.message_handler(func=lambda message: get_user_step(message.chat.id) == 'search_screen')
def search_screen(m):
    cid = m.chat.id
    text = m.text

    bot.send_chat_action(cid, 'typing')

    if text == ButtText.keyboard_main:
        bot.send_message(
            cid,
            'Используй клавиатуру для выбора действий!',
            reply_markup=keyboard(),
        )
        userStep[cid] = 0
        set_key('.env', 'userStep', str(userStep))
    else:
        WikiSearchInstance.wiki_search(text)
        bot.send_message(
            cid,
            WikiSearchInstance.wiki_results_summary,
            reply_markup=keyboard('search'),
        )
        userStep[cid] = 'search_screen_results'
        set_key('.env', 'userStep', str(userStep))


@attrs(auto_attribs=True)
class Pagination:
    pagination_limit = 7
    pagination_start = 1
    start = 1

    def pagination_keyboard(self, found_links: dict, start: int = 1):
        self.start = start
        results = [link for link in found_links]
        found_links_titles = [ButtText.keyboard_search]
        #  Add next button if not on last page
        if start * self.pagination_limit <= results.__len__():
            found_links_titles.append(ButtText.next_page_button)
        #  Add back button if not on first page
        if start != self.pagination_start:
            found_links_titles.append(ButtText.back_page_button)
        pagination = results[(start - self.pagination_start) * self.pagination_limit:start * self.pagination_limit]
        found_links_titles.extend(pagination)
        return create_keyboard(found_links_titles, 3)


PaginationInstance = Pagination()


@bot.message_handler(func=lambda message: get_user_step(message.chat.id) == 'search_screen_results')
def search_screen_results(m):
    cid = m.chat.id
    text = m.text

    bot.send_chat_action(cid, 'typing')

    # If bot restarted opens search page
    def bot_restarted():
        if not WikiSearchInstance.wiki_results_title:
            bot.send_message(
                cid,
                'Отправь в ответ свой запрос, чтобы я нашел статью',
                reply_markup=keyboard('back')
            )
            userStep[cid] = 'search_screen'
            set_key('.env', 'userStep', str(userStep))
            return
    match text:
        case ButtText.keyboard_back:
            bot.send_message(
                cid,
                'Отправь в ответ свой запрос, чтобы я нашел статью',
                reply_markup=keyboard('back')
            )
            userStep[cid] = 'search_screen'
            set_key('.env', 'userStep', str(userStep))
        case ButtText.keyboard_main:
            bot.send_message(
                cid,
                'Используй клавиатуру для выбора действий!',
                reply_markup=keyboard(),
            )
            userStep[cid] = 0
            set_key('.env', 'userStep', str(userStep))
        case ButtText.keyboard_pics:
            bot_restarted()
            try:
                found_images = wikipedia.page(WikiSearchInstance.wiki_results_title).images
            except Exception:
                found_images = None
            if found_images:
                bot.send_message(
                    cid,
                    'Вот картинки, которые я смог найти:',
                )
                bot.send_message(
                    cid,
                    found_images,
                )
            else:
                bot.send_message(
                    cid,
                    'Я не смог найти картинки 💩',
                )
            userStep[cid] = 'search_screen_results'
            set_key('.env', 'userStep', str(userStep))
        case ButtText.keyboard_links:
            bot_restarted()
            try:
                found_links = WikiSearchInstance.wiki_results_links
            except Exception:
                found_links = None
            if found_links:
                bot.send_message(
                    cid,
                    'Вот ссылки, которые я смог найти:',
                    reply_markup=PaginationInstance.pagination_keyboard(found_links)
                )
                userStep[cid] = 'links_screen'
                set_key('.env', 'userStep', str(userStep))
            else:
                bot.send_message(
                    cid,
                    'Я не смог найти ссылки 💩',
                )
        case _:
            search_screen(m)


@bot.message_handler(func=lambda message: get_user_step(message.chat.id) == 'links_screen')
def links_screen(m):
    cid = m.chat.id
    text = m.text

    bot.send_chat_action(cid, 'typing')

    found_links = WikiSearchInstance.wiki_results_links

    try:
        if text in [link for link in found_links]:
            WikiSearchInstance2.wiki_search(text)
            bot.send_message(
                cid,
                WikiSearchInstance2.wiki_results_summary,
                reply_markup=keyboard('search_links'),
            )
            userStep[cid] = 'link_search_screen_results'
            set_key('.env', 'userStep', str(userStep))
            return
    except TypeError:
        bot.send_message(
            cid,
            'Отправь в ответ свой запрос, чтобы я нашел статью',
            reply_markup=keyboard('back')
        )
        userStep[cid] = 'search_screen'
        set_key('.env', 'userStep', str(userStep))
        return
    if text in [ButtText.keyboard_search, ButtText.back_page_button, ButtText.next_page_button]:
        match text:
            case ButtText.keyboard_search:
                bot.send_message(
                    cid,
                    'Используй клавиатуру для выбора действий!',
                    reply_markup=keyboard('search'),
                )
                userStep[cid] = 'search_screen_results'
                set_key('.env', 'userStep', str(userStep))
            case ButtText.next_page_button:
                page_number = PaginationInstance.start + 1
                bot.send_message(
                    cid,
                    f'Страница {page_number}',
                    reply_markup=PaginationInstance.pagination_keyboard(found_links, page_number)
                )
            case ButtText.back_page_button:
                page_number = PaginationInstance.start - 1
                bot.send_message(
                    cid,
                    f'Страница {page_number}',
                    reply_markup=PaginationInstance.pagination_keyboard(found_links, page_number)
                )
    else:
        bot.send_message(
            cid,
            'Используй клавиатуру для выбора действий!',
        )


@bot.message_handler(func=lambda message: get_user_step(message.chat.id) == 'link_search_screen_results')
def link_search_screen_results(m):
    cid = m.chat.id
    text = m.text

    bot.send_chat_action(cid, 'typing')

    match text:
        case ButtText.keyboard_back:
            bot.send_message(
                cid,
                f'Страница {PaginationInstance.start}',
                reply_markup=PaginationInstance.pagination_keyboard(WikiSearchInstance.wiki_results_links,
                                                                    PaginationInstance.start)
            )
            userStep[cid] = 'links_screen'
            set_key('.env', 'userStep', str(userStep))
        case ButtText.keyboard_main:
            bot.send_message(
                cid,
                'Используй клавиатуру для выбора действий!',
                reply_markup=keyboard(),
            )
            userStep[cid] = 0
            set_key('.env', 'userStep', str(userStep))
        case ButtText.keyboard_pics:
            if not WikiSearchInstance.wiki_results_title:
                bot.send_message(
                    cid,
                    'Отправь в ответ свой запрос, чтобы я нашел статью',
                    reply_markup=keyboard('back')
                )
                userStep[cid] = 'search_screen'
                set_key('.env', 'userStep', str(userStep))
                return
            try:
                found_images = wikipedia.page(WikiSearchInstance2.wiki_results_title).images
            except Exception:
                found_images = None
            if found_images:
                bot.send_message(
                    cid,
                    'Вот картинки, которые я смог найти:',
                )
                bot.send_message(
                    cid,
                    found_images,
                )
            else:
                bot.send_message(
                    cid,
                    'Я не смог найти картинки 💩',
                )
        case _:
            search_screen(m)


@bot.message_handler(commands=['random'])
def random(m):
    cid = m.chat.id
    bot.send_message(
        cid,
        'Используй клавиатуру для выбора действий!',
        reply_markup=keyboard('random'),
    )
    userStep[cid] = 'random_screen'
    set_key('.env', 'userStep', str(userStep))


@bot.message_handler(func=lambda message: get_user_step(message.chat.id) == 'random_screen')
def random_screen(m):
    cid = m.chat.id
    text = m.text

    bot.send_chat_action(cid, 'typing')

    match text:
        case ButtText.keyboard_random_wiki:
            wikipedia.set_lang('ru')
            random_wiki_title = wikipedia.random()
            WikiSearchInstance.wiki_search(random_wiki_title)
            bot.send_message(
                cid,
                f'{random_wiki_title}\n\n{WikiSearchInstance.wiki_results_summary}',
            )
        case ButtText.keyboard_main:
            bot.send_message(
                cid,
                'Используй клавиатуру для выбора действий!',
                reply_markup=keyboard(),
            )
            userStep[cid] = 0
            set_key('.env', 'userStep', str(userStep))
        case _:
            bot.send_message(
                cid,
                'Используй клавиатуру для выбора действий!',
            )


@bot.message_handler(func=lambda message: True, content_types=['text'])
def command_default(m):
    cid = m.chat.id
    text = m.text
    match text:
        case ButtText.keyboard_search:
            search(m)
        case ButtText.keyboard_random:
            random(m)
        case ButtText.keyboard_help:
            command_help(m)
        case _:
            if get_user_step(cid):
                bot.send_message(
                    cid,
                    'Используй клавиатуру для выбора действий!',
                    reply_markup=keyboard()
                )
            else:
                bot.send_message(
                    cid,
                    f'Не понимаю команду "{text}"\nСписок команд в /help',
                )


if __name__ == '__main__':
    bot.infinity_polling()
