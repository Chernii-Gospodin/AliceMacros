import boto3
import yandexcloud
from yandex.cloud.lockbox.v1.payload_service_pb2 import GetPayloadRequest
from yandex.cloud.lockbox.v1.payload_service_pb2_grpc import PayloadServiceStub

boto_session = None


def get_boto_session():
    global boto_session
    if boto_session != None:
        return boto_session

    # initialize lockbox and read secret value
    yc_sdk = yandexcloud.SDK()
    channel = yc_sdk._channels.channel("lockbox-payload")
    lockbox = PayloadServiceStub(channel)
    response = lockbox.Get(GetPayloadRequest(secret_id='e6qt9hvkm1omp7v9i9pv'))

    # extract values from secret
    access_key = None
    secret_key = None
    for entry in response.entries:
        if entry.key == 'ACCESS_KEY_ID':
            access_key = entry.text_value
        elif entry.key == 'SECRET_ACCESS_KEY':
            secret_key = entry.text_value
    if access_key is None or secret_key is None:
        raise Exception("secrets required")

    # initialize boto session
    boto_session = boto3.session.Session(
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key
    )
    return boto_session


session = get_boto_session()
s3 = session.client(
    service_name='s3',
    endpoint_url='https://storage.yandexcloud.net'
)
BUCKET_NAME = 'opengeimer-cloud'
BUTTONS_ENABLED = {True: [
    {
        "title": "Создать макрос",
        "payload": {
            "original_utterance": "Создать макрос",
        },
        "hide": 'true'
    },
    {
        "title": "Использовать макрос",
        "payload": {
            "original_utterance": "Использовать макрос",
        },
        "hide": 'true'
    },
    {
        "title": "Изменить макрос",
        "payload": {
            "original_utterance": "Изменить макрос",
        },
        "hide": 'true'
    },
    {
        "title": "Удалить макрос",
        "payload": {
            "original_utterance": "Удалить макрос",
        },
        "hide": 'true'
    },
    {
        "title": "Просмотреть макросы",
        "payload": {
            "original_utterance": "Просмотреть макросы",
        },
        "hide": 'true'
    },
],
    False: []}
BUTTONS_NAMES = ["создать макрос", "использовать макрос", "изменить макрос", "удалить макрос", "просмотреть макросы"]


def check_user_message(func):
    global BUCKET_NAME, s3

    def wrapper(original_utterance, USER_ID, session_state):
        macros_name = original_utterance.lower()
        macros = s3.list_objects(Bucket=BUCKET_NAME, Prefix=USER_ID + '/' + macros_name + '.txt')
        if 'Contents' in macros:
            text, session_state['user_action'], session_state['user_links'], buttons_status = func(macros_name, USER_ID,
                                                                                                   session_state)
        else:
            text = 'Такого макроса не существует'
            session_state['user_action'] = ''
            session_state['user_links'] = 'false'
            buttons_status = True
        return text, session_state['user_action'], session_state['user_links'], buttons_status

    return wrapper


def create_macros(original_utterance, USER_ID, session_state, user_links):
    global BUCKET_NAME, s3
    if user_links == 'false':
        text = 'Введите все ссылки, абсолютные пути нужных вам файлов или команды к операционной системе в формате, например:\nСсылка\n"Путь"\nСсылка\nСсылка\nКоманда'
        macros_name = original_utterance.lower()
        s3.put_object(Bucket=BUCKET_NAME,
                      Key=f"{USER_ID}/{macros_name}.txt",
                      Body='',
                      StorageClass='STANDARD',
                      ContentEncoding='UTF-8')
        session_state['user_action'] = 'Create'
        session_state['user_links'] = 'true'
        buttons_status = False
    elif user_links == 'true':
        user_macroses = s3.list_objects(Bucket=BUCKET_NAME, Prefix=USER_ID)
        for macros in user_macroses['Contents']:
            if macros['Size'] == 0:
                macros_path = macros['Key']
        s3.put_object(Bucket=BUCKET_NAME,
                      Key=macros_path,
                      Body=original_utterance,
                      StorageClass='STANDARD',
                      ContentEncoding='UTF-8')
        text = "Что дальше? Если забыли свой USER_ID, введите любое сообщение"
        session_state['user_action'] = ''
        session_state['user_links'] = 'false'
        buttons_status = True
    return text, session_state['user_action'], session_state['user_links'], buttons_status


@check_user_message
def change_macros_links_false(macros_name, USER_ID, session_state):
    global BUCKET_NAME, s3
    macros = s3.get_object(Bucket=BUCKET_NAME, Key=USER_ID + '/' + macros_name + '.txt')
    macros_content = macros['Body'].read().decode('utf-8')
    s3.put_object(Bucket=BUCKET_NAME, Key=USER_ID + '/' + macros_name + '.txt', Body='')
    text = 'Введите все ссылки, абсолютные пути нужных вам файлов или команды к операционной системе в формате, например:\nСсылка\n"Путь"\nСсылка\nСсылка\nКоманда\n\nВот как этот макрос выглядит сейчас:\n' + macros_content
    session_state['user_action'] = 'Change'
    session_state['user_links'] = 'true'
    buttons_status = False
    return text, session_state['user_action'], session_state['user_links'], buttons_status


def change_macros_links_true(original_utterance, USER_ID):
    global BUCKET_NAME, s3
    user_macroses = s3.list_objects(Bucket=BUCKET_NAME, Prefix=USER_ID)
    for macros in user_macroses['Contents']:
        if macros['Size'] == 0:
            macros_path = macros['Key']
    s3.put_object(Bucket=BUCKET_NAME,
                  Key=macros_path,
                  Body=original_utterance,
                  StorageClass='STANDARD',
                  ContentEncoding='UTF-8')
    text = "Макрос изменён\nЧто дальше? Если забыли свой USER_ID, введите любое сообщение"
    return text


@check_user_message
def use_macros(macros_name, USER_ID, session_state):
    global BUCKET_NAME, s3
    macros = s3.get_object(Bucket=BUCKET_NAME, Key=USER_ID + '/' + macros_name + '.txt')
    macros_content = str(macros['Body'].read().decode('utf-8'))
    s3.put_object(Bucket=BUCKET_NAME,
                  Key=USER_ID + '/' + macros_name + '.txt',
                  Body=macros_content + '\nFLAG',
                  StorageClass='STANDARD',
                  ContentEncoding='UTF-8')
    text = "Что дальше? Если забыли свой USER_ID, введите любое сообщение"
    session_state['user_action'] = ''
    session_state['user_links'] = 'false'
    buttons_status = True
    return text, session_state['user_action'], session_state['user_links'], buttons_status


@check_user_message
def delete_macros(macros_name, USER_ID, session_state):
    global BUCKET_NAME, s3
    deleted_object = [{'Key': USER_ID + '/' + macros_name + '.txt'}]
    s3.delete_objects(Bucket=BUCKET_NAME, Delete={'Objects': deleted_object})
    text = "Макрос успешно удалён\nЧто дальше? Если забыли свой USER_ID, введите любое сообщение"
    session_state['user_action'] = ''
    session_state['user_links'] = 'false'
    buttons_status = True
    return text, session_state['user_action'], session_state['user_links'], buttons_status


@check_user_message
def view_macros(macros_name, USER_ID, session_state):
    global BUCKET_NAME, s3
    macros = s3.get_object(Bucket=BUCKET_NAME, Key=USER_ID + '/' + macros_name + '.txt')
    macros_content = macros['Body'].read().decode('utf-8')
    text = 'Вот как этот макрос выглядит сейчас:\n' + macros_content
    session_state['user_action'] = ''
    session_state['user_links'] = 'false'
    buttons_status = True
    return text, session_state['user_action'], session_state['user_links'], buttons_status


def pressed_button(original_utterance, user_folder):
    utterances_and_contents = {'создать макрос': [
        'Create',
        'Придумайте название для макроса\nВАЖНО! Если хотите вызывать в будущем макрос голосом, дайте ему название на русском'
    ],
        'использовать макрос': [
            'Use',
            'Запустите программу перед использованием макроса, после можете ввести нужное название'
        ],
        'изменить макрос': [
            'Change',
            'Введите название макроса, который хотите изменить:'
        ],
        'удалить макрос': [
            'Delete',
            'Введите название макроса, который хотите удалить:'
        ],
        'просмотреть макросы': [
            'View',
            'Введите название макроса, который хотите посмотреть'
        ]
    }
    text = ''
    user_action = ''
    buttons_status = True
    if 'Contents' in user_folder:
        user_folder_content = user_folder['Contents']
        for key in range(len(user_folder_content)):
            text += str(str(key + 1) + '. ' + user_folder_content[key]['Key'].split('/')[-1][:-4]) + '\n'
    elif original_utterance == 'Создать макрос' or original_utterance == 'создать макрос':
        text = text
    else:
        text = 'У вас нет макросов'
        return text, user_action, buttons_status
    for key in utterances_and_contents.keys():
        if original_utterance.lower() == key:
            user_action = utterances_and_contents[key][0]
            text += utterances_and_contents[key][1]
            buttons_status = False
    return text, user_action, buttons_status


async def handler(event, context):
    global BUCKET_NAME, BUTTONS_ENABLED, BUTTONS_NAMES, s3
    # Entry-point for Serverless Function.
    # :param event: request payload.
    # :param context: information about current execution context.
    # :return: response to be serialized as JSON.
    USER_ID = event["session"]["user"]["user_id"]
    text = "Привет, пользователь.\n\nЧтобы данный навык работал исправно, скачай отсюда приложение: https://clck.ru/378m8o или https://github.com/Chernii-Gospodin/AliceMacros.\
\n\nВот твой USER_ID, необходимый для приложения: " + USER_ID + "\nПодготовте нужные ссылки и пути заранее, так как Алиса сбрасывается, если нажать в браузере на что-то кроме неё"
    session_state = {'user_action': '', 'user_links': 'false'}
    macros_name = ''
    buttons_status = True

    if event['request']['type'] == 'ButtonPressed':
        user_folder = s3.list_objects(Bucket=BUCKET_NAME, Prefix=USER_ID)
        text, session_state["user_action"], buttons_status = pressed_button(
            event['request']['payload']['original_utterance'], user_folder)
    elif event['request']['original_utterance'].lower() in BUTTONS_NAMES:
        user_folder = s3.list_objects(Bucket=BUCKET_NAME, Prefix=USER_ID)
        text, session_state["user_action"], buttons_status = pressed_button(event['request']['original_utterance'],
                                                                            user_folder)

    if 'user_action' in event['state']['session']:

        if event['state']['session']['user_action'] == 'Create':
            text, session_state['user_action'], session_state['user_links'], buttons_status = create_macros(
                event['request']['original_utterance'], USER_ID, session_state, event['state']['session']['user_links'])

        if event['state']['session']['user_action'] == 'Use':
            text, session_state['user_action'], session_state['user_links'], buttons_status = use_macros(
                event['request']['original_utterance'], USER_ID, session_state)

        if event['state']['session']['user_action'] == 'Change':
            if event['state']['session']['user_links'] == 'false':
                text, session_state['user_action'], session_state[
                    'user_links'], buttons_status = change_macros_links_false(event['request']['original_utterance'],
                                                                              USER_ID, session_state)
            elif event['state']['session']['user_links'] == 'true':
                text = change_macros_links_true(event['request']['original_utterance'], USER_ID)

        if event['state']['session']['user_action'] == 'Delete':
            text, session_state['user_action'], session_state['user_links'], buttons_status = delete_macros(
                event['request']['original_utterance'], USER_ID, session_state)

        if event['state']['session']['user_action'] == 'View':
            text, session_state['user_action'], session_state['user_links'], buttons_status = view_macros(
                event['request']['original_utterance'], USER_ID, session_state)

    buttons = BUTTONS_ENABLED[buttons_status]

    return {
        'version': event['version'],
        'session': event['session'],
        'response': {
            # Respond with the original request or welcome the user if this is the beginning of the dialog and the request has not yet been made.
            'text': text,
            # Don't finish the session after this response.
            'end_session': 'false',
            'buttons': buttons,
        },
        'session_state': session_state,
    }