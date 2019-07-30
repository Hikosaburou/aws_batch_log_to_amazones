# -*- coding:utf-8 -*-
import os
import base64
import zlib
import logging
import ast
import yaml
from datetime import datetime

from elasticsearch import (
    helpers,
    Elasticsearch,
    RequestsHttpConnection
)
from requests_aws4auth import AWS4Auth
from typing import Tuple


# ログレベル設定
logger = logging.getLogger()
logLevelTable = {
    'DEBUG': logging.DEBUG,
    'INFO': logging.INFO,
    'WARNING': logging.WARNING,
    'ERROR': logging.ERROR,
    'CRITICAL': logging.CRITICAL
}

if 'LOG_LEVEL' in os.environ and os.environ['LOG_LEVEL'] in logLevelTable:
    logLevel = logLevelTable[os.environ['LOG_LEVEL']]
else:
    logLevel = logging.WARNING
logger.setLevel(logLevel)


def type_exchange(data):
    '''
    Description: valueを適当に型変換する
    '''
    if type(data) is not str:
        return data

    if data.isdecimal():
        return int(data)

    return data


def build_source(log_event: {}) -> {}:
    '''
    Description: Elasticsearch への送信用データセットを作る
   '''
    # ドキュメントのソース情報を埋め込む。適宜型を変換するために type_exchange を呼んでいる
    return {key: type_exchange(val)
            for (key, val) in log_event.get('extractedFields').items()}


def transform(data: {}, index_name: str, index: int) -> []:
    '''
    Description: Elasticsearch への送信用データセットを作る。
    '''

    actions = []

    # bulk API で送れるのは1000件がmaxなので、1000個ずつ返す
    for log_event in data['logEvents'][index:index+1000]:
        source = build_source(log_event)
        # メタデータの設定
        source['@id'] = log_event['id']
        source['@timestamp'] = datetime.utcfromtimestamp(
            int(log_event['timestamp']) / 1000)
        source['@message'] = log_event['message']
        source['@owner'] = data['owner']
        source['@log_group'] = data['logGroup']
        source['@log_stream'] = data['logStream']

        actions.append({
            '_index': index_name,
            '_type': data['logGroup'],
            '_id': log_event['id'],
            '_source': source
        })

    return actions


def get_es_target_attributes(config: {}, log_stream: str) -> Tuple[str, str]:
    '''
    Description: ESの投入先(エンドポイント、インデックス名)を返す
    '''

    # エンドポイントを得る
    envs = [
        env for env in config['ES_ENDPOINT'].keys()
        if log_stream.startswith(env)
    ]
    env = None if not envs else envs[0]

    # ログの種別を得る
    indices = [
        batch_type for batch_type in config['ALLOWED_PATTERN']
        if batch_type in log_stream
    ]
    index = None if not indices else indices[0]

    endpoint = config['ES_ENDPOINT'].get(env)
    index_name = '-'.join([env, 'applilog', index])

    return (endpoint, index_name)


def lambda_handler(event, context):
    '''
    description: lambdaハンドラ。eventからデータを取得して投げる
    '''

    # イベントデータを取得
    data = ast.literal_eval(zlib.decompress(base64.b64decode(
        event['awslogs']['data']), 16+zlib.MAX_WBITS).decode('utf-8'))

    # messageType が "DATA_MESSAGE" 以外の場合は終了
    logger.info('message type: {}'.format(data.get('messageType')))
    if data.get('messageType') != 'DATA_MESSAGE':
        return

    with open('config.yml', 'r') as f:
        config = yaml.safe_load(f)

    # ES連携設定
    endpoint, index = get_es_target_attributes(config, data.get('logStream'))
    awsauth = AWS4Auth(
        os.environ.get('AWS_ACCESS_KEY_ID'),
        os.environ.get('AWS_SECRET_ACCESS_KEY'),
        config.get('REGION'),
        'es',
        session_token=os.environ.get('AWS_SESSION_TOKEN')
    )
    es = Elasticsearch(
        host=endpoint,
        port=443,
        http_auth=awsauth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection
    )

    # 1000件単位でデータを送る
    iter_i = 0
    while True:
        actions = transform(data, index, iter_i)
        if not bool(actions):
            break
        helpers.bulk(es, actions)
        iter_i += 1000
