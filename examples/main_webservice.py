import json

# Make sure this file will be located at
# `./apis/{api_name}/` from the execution directory.

# Directory in which this file is located
import os
this_directory = os.path.dirname(os.path.abspath(__file__))


class APIResource:
    def on_get(self, req, resp):
        # params = req.params  # GET parameters
        resp.content_type = 'text/html'
        resp.body = '''
            <html>
                <body>
                    <form action="" method="POST" enctype="multipart/form-data">
                        <input type="text" id="textbox1" name="textbox1" width=30>
                        <input type="submit" value="Post!" />
                    </form>
                </body>
            </html>'''
        # Note that the URI "" is regarded as here.

    def on_post(self, req, resp):  # when multipart/form-data is POSTed
        try:
            textbox1 = req.get_param('textbox1')
        except:
            textbox1 = '(error occured)'
        obj = {
            'code': 0,
            'message': 'This is POST test.',
            'result': textbox1
        }
        resp.content_type = 'application/json'
        resp.body = json.dumps(obj, ensure_ascii=False)
