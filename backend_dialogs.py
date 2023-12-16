import boto3
import requests
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


def pressed_button(BUCKET_NAME, USER_ID, original_utterance, folder):
    utterances_and_contents = {'Создать макрос': [
        'Create',
        'Придумайте название для макроса\nВАЖНО! Если хотите вызывать в будущем макрос голосом, дайте ему название на русском'
    ],
        'Использовать макрос': [
            'Use',
            'Запустите программу перед использованием макроса, после можете ввести нужное название'
        ],
        'Изменить макрос': [
            'Change',
            'Введите название макроса, который хотите изменить:'
        ],
        'Удалить макрос': [
            'Delete',
            'Введите название макроса, который хотите удалить:'
        ],
        'Просмотреть макросы': [
            'View',
            'Введите название макроса, который хотите посмотреть'
        ]
    }
    text = ''
    user_action = ''
    buttons_enabled = True
    if 'Contents' in folder:
        folder_content = folder['Contents']
        for key in range(len(folder_content)):
            text += str(str(key + 1) + '. ' + folder_content[key]['Key'].split('/')[-1][:-4]) + '\n'
    elif original_utterance == 'Создать макрос':
        text = text
    else:
        text = 'У вас нет макросов'
        return text, user_action, buttons_enabled
    for key in utterances_and_contents.keys():
        if original_utterance == key:
            user_action = utterances_and_contents[key][0]
            text += utterances_and_contents[key][1]
            buttons_enabled = False
    return text, user_action, buttons_enabled


async def handler(event, context):
    # Entry-point for Serverless Function.
    # :param event: request payload.
    # :param context: information about current execution context.
    # :return: response to be serialized as JSON.
    session = get_boto_session()
    BUCKET_NAME = 'opengeimer-cloud'
    USER_ID = event["session"]["user"]["user_id"]
    s3 = session.client(
        service_name='s3',
        endpoint_url='https://storage.yandexcloud.net'
    )
    text = "Привет, пользователь.\n\nЧтобы данный навык работал исправно, скачай отсюда приложение: https://clck.ru/378m8o или https://github.com/Chernii-Gospodin/AliceMacros.\
\n\nВот твой USER_ID, необходимый для приложения: " + USER_ID
    session_state = {'user_action': '', 'user_links': 'false'}
    macros_name = ''
    buttons_status = True
    buttons_enabled = {True: [
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

    if event['request']['type'] == 'ButtonPressed':
        folder = s3.list_objects(Bucket=BUCKET_NAME, Prefix=USER_ID)
        text, session_state["user_action"], buttons_status = pressed_button(BUCKET_NAME, USER_ID,
                                                                            event['request']['payload'][
                                                                                'original_utterance'], folder)

    if 'user_action' in event['state']['session']:

        if event['state']['session']['user_action'] == 'Create':
            if event['state']['session']['user_links'] == 'false':
                text = 'Введите все ссылки, абсолютные пути нужных вам файлов или команды к операционной системе в формате, например:\nСсылка\n"Путь"\nСсылка\nСсылка\nКоманда'
                macros_name = event['request']['original_utterance'].lower()
                s3.put_object(Bucket=BUCKET_NAME,
                              Key=f"{event['session']['user']['user_id']}/{macros_name}.txt",
                              Body='',
                              StorageClass='STANDARD',
                              ContentEncoding='UTF-8')
                session_state['user_action'] = 'Create'
                session_state['user_links'] = 'true'
                buttons_status = False
            elif event['state']['session']['user_links'] == 'true':
                user_macroses = s3.list_objects(Bucket=BUCKET_NAME, Prefix=USER_ID)
                for macros in user_macroses['Contents']:
                    if macros['Size'] == 0:
                        macros_name = macros['Key']
                s3.put_object(Bucket=BUCKET_NAME,
                              Key=macros_name,
                              Body=event['request']['original_utterance'],
                              StorageClass='STANDARD',
                              ContentEncoding='UTF-8')
                text = "Что дальше? Если забыли свой USER_ID, введите любое сообщение"

        if event['state']['session']['user_action'] == 'Use':
            macros_name = event['request']['original_utterance'].lower()
            macros = s3.list_objects(Bucket=BUCKET_NAME, Prefix=USER_ID + '/' + macros_name + '.txt')
            if 'Contents' in macros:
                macros = s3.get_object(Bucket=BUCKET_NAME, Key=USER_ID + '/' + macros_name + '.txt')
                macros_content = str(macros['Body'].read().decode('utf-8'))
                s3.put_object(Bucket=BUCKET_NAME,
                              Key=USER_ID + '/' + macros_name + '.txt',
                              Body=macros_content + '\nFLAG',
                              StorageClass='STANDARD',
                              ContentEncoding='UTF-8')
                text = "Что дальше? Если забыли свой USER_ID, введите любое сообщение"
            else:
                text = 'Такого макроса не существует'

        if event['state']['session']['user_action'] == 'Change':
            if event['state']['session']['user_links'] == 'false':
                macros_name = event['request']['original_utterance'].lower()
                macros = s3.list_objects(Bucket=BUCKET_NAME, Prefix=USER_ID + '/' + macros_name + '.txt')
                if 'Contents' in macros:
                    macros = s3.get_object(Bucket=BUCKET_NAME, Key=USER_ID + '/' + macros_name + '.txt')
                    macros_content = macros['Body'].read().decode('utf-8')
                    s3.put_object(Bucket=BUCKET_NAME, Key=USER_ID + '/' + macros_name + '.txt', Body='')
                    text = 'Введите все ссылки, абсолютные пути нужных вам файлов или команды к операционной системе в формате, например:\nСсылка\n"Путь"\nСсылка\nСсылка\nКоманда\n\nВот как этот макрос выглядит сейчас:\n' + macros_content
                    session_state['user_action'] = 'Change'
                    session_state['user_links'] = 'true'
                    buttons_status = False
                else:
                    text = 'Такого макроса не существует'
            elif event['state']['session']['user_links'] == 'true':
                user_macroses = s3.list_objects(Bucket=BUCKET_NAME, Prefix=USER_ID)
                for macros in user_macroses['Contents']:
                    if macros['Size'] == 0:
                        macros_name = macros['Key']
                s3.put_object(Bucket=BUCKET_NAME,
                              Key=macros_name,
                              Body=event['request']['original_utterance'],
                              StorageClass='STANDARD',
                              ContentEncoding='UTF-8')
                text = "Что дальше? Если забыли свой USER_ID, введите любое сообщение"

        if event['state']['session']['user_action'] == 'Delete':
            macros_name = event['request']['original_utterance'].lower()
            deleted_object = [{'Key': USER_ID + '/' + macros_name + '.txt'}]
            s3.delete_objects(Bucket=BUCKET_NAME, Delete={'Objects': deleted_object})
            text = "Что дальше? Если забыли свой USER_ID, введите любое сообщение"

        if event['state']['session']['user_action'] == 'View':
            macros_name = event['request']['original_utterance'].lower()
            macros = s3.get_object(Bucket=BUCKET_NAME, Key=USER_ID + '/' + macros_name + '.txt')
            macros_content = macros['Body'].read().decode('utf-8')
            text = 'Вот как этот макрос выглядит сейчас:\n' + macros_content

    buttons = buttons_enabled[buttons_status]

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