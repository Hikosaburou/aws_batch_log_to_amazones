# batch_logs_to_amazones

CW Logsに連携されたAWS BatchのログをAmazon ESに連携するLambda Function.

## ざっくり前提条件と仕様

### 前提

- Amazon ES はパブリックアクセスで配置されている
    - VPC接続する場合は Lambda Function のIAMロールに別途 AWSLambdaVPCAccessExecutionRole ポリシーを付与する必要がある
- Amazon ES バージョン 2.3 での動作を確認済み
    - type 指定があるので、最新版では動作しない可能性あり
- CW Logs ロググループは `/aws/batch/job` 
- AWS Batch のジョブ定義は `{{ 環境 }}-{{ バッチ種別 }}-job-definition` の形式　
    - CW Logs ログストリームは `{{ 環境 }}-{{ バッチ種別 }}-job-definition/default/{{ Job ID }}` の形式になる。

### 仕様

- CW Logs ログストリームで ES に連携するかどうかを判定する
    - 環境によってESのエンドポイントを変える
        - config.yml の `ES_ENDPOINT` リストにKV形式で記載する。
        - ex: `"prd": "search-endpoint-xxxxxxxxxxxxxxxxxx.ap-northeast-1.es.amazonaws.com"`
    - バッチ種別によってインデックス名を変える
        - `dev-foober-job-definition` というジョブ定義を作成した場合、 `dev-applilog-foober` というインデックス名となる
    - config.ymlの `ALLOED_PATTERN` で対象のバッチ種別を指定する
        - `foober` バッチを連携したい場合は `foober` を追加する

## Lambda Function について

- [Serverless Framework](https://serverless.com/) でデプロイする
- 以下のServerless Frameworkプラグインを利用する

|プラグイン名|用途|
|:---|:---|
|[serverless-python-requirements](https://github.com/UnitedIncome/serverless-python-requirements)|PythonモジュールをLambdaにデプロイするため|
|[serverless-prune-prugin](https://www.npmjs.com/package/serverless-prune-plugin)|古いバージョンのLambda Functionを削除するため|

## Requirements

- Node.js, npm
- Serverless Framework
- Docker
    - serverless-python-requirementsでモジュールをインストールするために使用する

以下の環境で動作確認済

```
$ npm --version
6.9.0

$ serverless version
1.45.1

$ docker --version
Docker version 18.09.2, build 6247962
```

## Prepare

### Serverless Framework の設定

Serverless Framework をインストールする ( [ドキュメント](https://serverless.com/framework/docs/providers/aws/guide/installation/) )

以下コマンドを実行し、各種プラグインをインストールする

```
sls plugin install -n serverless-python-requirements
sls plugin install -n serverless-prune-plugin
```

## Deploy

`sls` コマンドでデプロイを行う。`--stage` オプションで `env-hoge.yml` の `hoge` を指定する。

```sh
# Lambda のデプロイ
$ sls deploy --aws-profile=oreno-profile --stage=dev
```

## Remove

Lambda Function 本体は `sls` コマンドで削除する
S3バケットに設定したEvents設定は手動で削除する