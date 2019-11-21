import json


def topic_parser(prefix, message_topic):
    return message_topic.replace('{}/'.format(prefix), '').split('/')


def iot_thing_topic(thing):
    return "$aws/things/{}/shadow/update".format(thing)


def iot_payload(target, doc):
    return json.dumps({'state': {target: doc}})
