import json

# Make sure this file will be located at
# `./apis/{api_name}/` from the execution directory.

# Directory in which this file is located
# import os
# this_directory = os.path.dirname(os.path.abspath(__file__))

class APIResource:
    def on_get(self, req, resp):
        params = req.params # GET parameters
        obj = {
            'code': 0,
            'message': 'This is GET test.',
            'result': params
        }
        resp.content_type = 'application/json'
        resp.body = json.dumps(obj, ensure_ascii=False)

    def on_post(self, req, resp):
        buf = req.stream.read()
        try:
            params = json.loads(str(buf, encoding='utf-8'))
        except:
            params = '(not json)'
        obj = {
            'code': 0,
            'message': 'This is POST test.',
            'result': params
        }
        resp.content_type = 'application/json'
        resp.body = json.dumps(obj, ensure_ascii=False)
