import boto3

ACCESS_KEY = 'YCAJE9DYWEosmFd9bSDJQXsc_'
SECRET_ACCESS_KEY = 'YCOKpks4vvloTovPA0pTw99T7JZAw2yOwzO0AvCG'
BUCKET_NAME = 'opengeimer-cloud'

session = boto3.session.Session(aws_access_key_id=ACCESS_KEY,
                                aws_secret_access_key=SECRET_ACCESS_KEY)
s3 = session.client(service_name='s3', endpoint_url='https://storage.yandexcloud.net')


def handler(event, context):
    USER_ID = event['body']
    object2return = 'None'

    for name in s3.list_objects(Bucket=BUCKET_NAME)['Contents']:
        File = name['Key']
        if USER_ID in File:
            raw_data = s3.get_object(Bucket=BUCKET_NAME, Key=File)
            raw_data = raw_data['Body'].read().decode('utf-8').split('\n')

            if raw_data[-1] == 'FLAG':
                object2return = raw_data[:-1]
                body2return = '\n'.join(object2return)

                s3.put_object(Bucket=BUCKET_NAME, Key=File, Body=body2return, StorageClass='STANDARD')
                break

    return {
        'body': object2return
    }
