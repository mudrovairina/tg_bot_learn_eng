import random

import sqlalchemy
from sqlalchemy.orm import sessionmaker
from telebot import types, TeleBot, custom_filters
from telebot.handler_backends import State, StatesGroup
from telebot.storage import StateMemoryStorage

from models import create_tables, User, Vocabulary, PersonalDictionary

print('Start telegram bot...')

LOGIN = 'postgres'
PASSWORD = 'admin'
NAME_SERVER = 'localhost'
PORT_SERVER = 5432
NAME_DB = 'tg_bot'
DSN = f'postgresql://{LOGIN}:{PASSWORD}@{NAME_SERVER}:{PORT_SERVER}/{NAME_DB}'
engine = sqlalchemy.create_engine(DSN)

state_storage = StateMemoryStorage()
TOKEN_BOT = ''
bot = TeleBot(TOKEN_BOT, state_storage=state_storage)

userStep = {}
buttons = []


def initial_data(session):
    love = Vocabulary(ru_word='Любовь', eng_word='Love')
    peace = Vocabulary(ru_word='Мир', eng_word='Peace')
    cat = Vocabulary(ru_word='Кошка', eng_word='Cat')
    spring = Vocabulary(ru_word='Весна', eng_word='Spring')
    development = Vocabulary(ru_word='Развитие', eng_word='Development')
    experience = Vocabulary(ru_word='Опыт', eng_word='Experience')
    family = Vocabulary(ru_word='Семья', eng_word='Family')
    life = Vocabulary(ru_word='Жизнь', eng_word='Life')
    hope = Vocabulary(ru_word='Надежда', eng_word='Hope')
    support = Vocabulary(ru_word='Поддержка', eng_word='Support')
    session.add_all(
        [love, peace, cat, spring, development,
         experience, family, life, hope, support]
    )
    session.commit()


def show_hint(*lines):
    return '\n'.join(lines)


def show_target(data):
    return f"{data['target_word']} -> {data['translate_word']}"


class Command:
    ADD_WORD = 'Добавить слово ➕'
    DELETE_WORD = 'Удалить слово🔙'
    NEXT = 'Дальше ⏭'


class MyStates(StatesGroup):
    translating_word = State()
    adding_word = State()
    deleting_word = State()


# показывает наличие нового пользователя
def get_user_step(cid):
    if cid in userStep:
        return True
    else:
        userStep[cid] = 0
        print("New user detected, who hasn't used \"/start\" yet")
        return False


def get_or_create_user(user_id_from_tg):
    db_user_id = None
    for user in session.query(User).\
            filter(User.id_user_tg == user_id_from_tg).all():
        db_user_id = user.id
    # создание пол-ля в БД
    if not db_user_id:
        user = User(id_user_tg=user_id_from_tg)
        session.add(user)
        session.commit()
        db_user_id = user.id
    return db_user_id


# обработчик команд, создание и отправка сообщений с шаблоном (клавиатурой)
# создание карточек
@bot.message_handler(commands=['cards', 'start'])
def create_cards(message):
    hello = 'Привет 👋 Давай попрактикуемся в английском языке.' \
            'Тренировки можешь проходить в удобном для себя темпе.\n\n' \
            'У тебя есть возможность использовать тренажёр, ' \
            'как конструктор, и собирать свою собственную базу для обучения. ' \
            'Для этого воспользуйся инструментами:\n\n' \
            'добавить слово ➕,\n' \
            'удалить слово 🔙.\n' \
            'Ну что, начнём ⬇\n️'
    cid = message.chat.id
    is_exist = get_user_step(cid)
    if not is_exist:
        bot.send_message(cid, hello)

    db_user_id = get_or_create_user(message.from_user.id)

    # создание шаблона(клавиатуры) для кнопок
    markup = types.ReplyKeyboardMarkup(row_width=2)

    global buttons
    buttons = []
    dict_ru_eng = {}
    for word in session.query(Vocabulary).all():
        dict_ru_eng[word.eng_word] = word.ru_word
    target_word = random.choice(list(dict_ru_eng.keys()))
    translate = dict_ru_eng[target_word]
    # добавляем кнопку target_word
    target_word_btn = types.KeyboardButton(target_word)
    buttons.append(target_word_btn)
    # добавляем рандомные кнопки с другими словами
    del dict_ru_eng[target_word]
    others = random.sample(list(dict_ru_eng.keys()), 4)
    other_words_btns = [types.KeyboardButton(word) for word in others]
    buttons.extend(other_words_btns)
    # рандомное распределение кнопок
    random.shuffle(buttons)
    # добавляем кнопки NEXT, ADD, DELETE
    next_btn = types.KeyboardButton(Command.NEXT)
    add_word_btn = types.KeyboardButton(Command.ADD_WORD)
    delete_word_btn = types.KeyboardButton(Command.DELETE_WORD)
    buttons.extend([next_btn, add_word_btn, delete_word_btn])
    # добавляем в шаблон (клавиатуру) все кнопки
    markup.add(*buttons)

    greeting = f"Выбери перевод слова:\n🇷🇺 {translate}"
    # отправка сообщения определенному пол-лю с клавиатурой
    bot.send_message(message.chat.id, greeting, reply_markup=markup)
    # установка состояния пол-ля в чате
    bot.set_state(
        message.from_user.id,
        MyStates.translating_word,
        message.chat.id
    )
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['target_word'] = target_word
        data['translate_word'] = translate
        data['other_words'] = others
        data['db_user_id'] = db_user_id


# обработчик нажатия на кнопку "дальше"
@bot.message_handler(func=lambda message: message.text == Command.NEXT)
def next_cards(message):
    create_cards(message)


# обработчик нажатия на кнопку "удалить"
@bot.message_handler(func=lambda message: message.text == Command.DELETE_WORD)
def delete_word(message):
    text = "Введите слово на русском языке, " \
           "которое Вы хотели бы удалить из своего словаря: "
    # отправка сообщения определенному пол-лю БЕЗ клавиатуры
    bot.send_message(
        message.chat.id,
        text,
        reply_markup=types.ReplyKeyboardRemove()
    )
    bot.set_state(
        message.from_user.id,
        MyStates.deleting_word,
        message.chat.id
    )


# процесс удаления слова из личного словаря определенного пользователя
@bot.message_handler(state=MyStates.deleting_word)
def process_deleting_word(message):
    word_to_delete = message.text
    id_personal_dictionary = None
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        db_user_id = data['db_user_id']
    for word in session.query(PersonalDictionary).\
            filter(PersonalDictionary.id_vocabulary == Vocabulary.id). \
            filter(PersonalDictionary.id_user == db_user_id). \
            filter(Vocabulary.ru_word == word_to_delete).all():
        id_personal_dictionary = word.id
    if id_personal_dictionary:
        session.query(PersonalDictionary).\
            filter(PersonalDictionary.id == id_personal_dictionary).delete()
        session.commit()
        text = f"Слово '{word_to_delete}' удалено из Вашего персонального словаря👍"
        bot.send_message(
            message.chat.id,
            text,
            reply_markup=types.ReplyKeyboardRemove()
        )
        create_cards(message)
    else:
        text = "Слово не найдено в вашем словаре🙃 " \
               "Введите слово на русском языке, " \
               "которое Вы хотели бы удалить из своего словаря: "
        bot.send_message(
            message.chat.id,
            text,
            reply_markup=types.ReplyKeyboardRemove()
        )


# обработчик нажатия на кнопку "добавить"
@bot.message_handler(func=lambda message: message.text == Command.ADD_WORD)
def add_word(message):
    text = "Введите слово на русском языке, которое Вы хотели бы добавить в свой словарь: "
    # отправка сообщения определенному пол-лю БЕЗ клавиатурой
    bot.send_message(
        message.chat.id,
        text,
        reply_markup=types.ReplyKeyboardRemove()
    )
    bot.set_state(
        message.from_user.id,
        MyStates.adding_word,
        message.chat.id
    )


# процесс добавления слова из общего словаря в личный словарь
# определенного пользователя
@bot.message_handler(state=MyStates.adding_word)
def process_adding_word(message):
    new_word = message.text
    id_vocabulary = None
    for word in session.query(Vocabulary).\
            filter(Vocabulary.ru_word == new_word).all():
        id_vocabulary = word.id
    if id_vocabulary:
        with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
            db_user_id = data['db_user_id']
        add_new_word = PersonalDictionary(
            id_user=db_user_id,
            id_vocabulary=id_vocabulary
        )
        session.add(add_new_word)
        session.commit()
        text = f"Слово '{new_word}' добавлено в Ваш персональный словарь👍"
        bot.send_message(
            message.chat.id,
            text,
            reply_markup=types.ReplyKeyboardRemove()
        )
        create_cards(message)
    else:
        text = "Слово не найдено в нашем словаре🙃 " \
               "Введите слово на русском языке," \
               " которое Вы хотели бы добавить в свой словарь: "
        bot.send_message(
            message.chat.id,
            text,
            reply_markup=types.ReplyKeyboardRemove()
        )


# обработчик, если пол-ль ввел любое слово
@bot.message_handler(func=lambda message: True, content_types=['text'])
def message_reply(message):
    cid = message.chat.id
    is_exist = get_user_step(cid)
    # если пол-ль не ввел "/start", то перенаправляем его в начало
    if not is_exist:
        create_cards(message)
        return

    input_word = message.text
    markup = types.ReplyKeyboardMarkup(row_width=2)  # пустая клавиатура
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        target_word = data['target_word']
        if input_word == target_word:
            hint_text = ["Отлично!❤", show_target(data)]
            hint = show_hint(*hint_text)
        else:
            for btn in buttons:
                if btn.text == input_word:
                    btn.text = input_word + '❌'
                    break
            hint = show_hint(
                f"Допущена ошибка! "
                f"Попробуй ещё раз вспомнить слово 🇷🇺{data['translate_word']}"
            )
    markup.add(*buttons)
    bot.send_message(message.chat.id, hint, reply_markup=markup)


if __name__ == "__main__":
    create_tables(engine)

    Session = sessionmaker(bind=engine)
    session = Session()

    initial_data(session)

    bot.add_custom_filter(custom_filters.StateFilter(bot))

    bot.infinity_polling(skip_pending=True)

    session.close()
