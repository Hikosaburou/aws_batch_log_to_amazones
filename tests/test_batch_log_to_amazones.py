#!/usr/bin/env python
# -*- coding:utf-8 -*-
import batch_log_to_amazones
import json
from datetime import datetime


def test_get_es_target_attributes():
    '''
    Description: get_es_target_attributes をテストする
    '''

    config = {
        'ES_ENDPOINT': {'debug': 'debug-endpoint'},
        'ALLOWED_PATTERN': ['test-pattern']
    }

    test_log_stream = 'debug-test-pattern-stream/default/xxxxx-id-xxxxx'

    endpoint, index_name = batch_log_to_amazones.get_es_target_attributes(
        config, test_log_stream)

    assert endpoint == 'debug-endpoint'
    assert index_name == 'debug-applilog-test-pattern'


def test_transform_ok():
    '''
    Description: transform ... ES送信情報を作る部分のテスト
    '''

    # 変換元データをjsonから読み込む
    with open('tests/data.json', 'r') as f:
        data = json.load(f)

    # ES投入データを得る
    actions = batch_log_to_amazones.transform(
        data, 'debug-applilog-test-log', 0)

    assert len(actions) == 3
    assert actions[0].get('_index') == 'debug-applilog-test-log'
    assert actions[0].get('_source') is not None
    assert actions[0]['_source'].get(
        '@timestamp') == datetime(2015, 5, 28, 15, 27, 35)


def test_transform_stop():
    '''
    Description: transform ... 要素数が0になるパターン (iter_i = 1000) を確認
    '''

    # 変換元データをjsonから読み込む
    with open('tests/data.json', 'r') as f:
        data = json.load(f)

    # ES投入データを得る
    actions = batch_log_to_amazones.transform(
        data, 'debug-applilog-test-log', 1000)

    assert actions == []
