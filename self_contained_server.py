import falcon
from falcon_multipart.middleware import MultipartMiddleware
import json
import numpy as np
import os, shutil
import importlib
import zipfile
import glob
import sys
import argparse
import cgi


def get_error_message(sys_exc_info=None):
    ex, ms, tb = sys.exc_info() if sys_exc_info is None else sys_exc_info
    return '[Error]\n' + str(ex) + '\n' + str(ms)

class CORSMiddleware:
    def process_request(self, req, resp):
        resp.set_header('Access-Control-Allow-Origin', '*')

app = falcon.API(middleware=[CORSMiddleware(), MultipartMiddleware()])



def is_healthy_api_name(s):
    """
    api_name に使用可能な文字列かを判定する．
    --------
    Args: s (str)
    Returns: (bool)
    """
    for c in s:
        if (c < 'a' or 'z' < c) and (c < '0' or '9' < c) and c not in '-_': return False
    return True


class APIManager:
    """
    /apis/ 配下の API (URL と Resourse) の一覧を管理するクラス．
    API を登録したり削除したりできる．
    """
    def __init__(self):
        # API の一覧．[(api_name(str), api_resource(Resource class instance)), ... ]
        self.api_list = [] # PUBLIC

    def get_api_name_list(self):
        return [a[0] for a in self.api_list]

    def delete_api(self, api_name):
        """
        ./apis/{api_name} の API を削除する．
        --------
        Args:
            api_name (str): APIの名称．名称の適切性（例えばスラッシュやドットが含まれていない等）は判定されません．

        Returns:
            ((bool), (str)): 削除に正常に成功したか否か，及びエラーメッセージ
        """
        try:
            for i,a in enumerate(self.api_list):
                if a[0] == api_name:
                    name, resource = self.api_list.pop(i)
                    del resource # Resource class の破棄．
                    api_path = './apis/{}'.format(name)
                    if os.path.exists(api_path):
                        shutil.rmtree(api_path)
                    return True, ''
        except:
            msg = get_error_message()
            print(msg)
            return False, msg
        return False, 'not such api registered: {}'.format(api_name)

    def register_api_from_directory(self, api_name):
        """
        ./apis/{api_name}/ ディレクトリに格納されている内容を元に，route の登録を試みる．
        --------
        Args:
            api_name (str): APIの名称．名称の適切性（例えばスラッシュやドットが含まれていない等）は判定されません．

        Returns:
            ((bool), (str)): route の登録に正常に成功したか否か，及びエラーメッセージ
        """
        try:
            NewModule = importlib.import_module('apis.{}.main'.format(api_name))
            # reload の場合はこれが必要．
            importlib.reload(NewModule)
            api_resource = NewModule.APIResource()
            app.add_route('/apis/{}'.format(api_name), api_resource)
            self.api_list.append((api_name, api_resource))
            return True, ''
        except Exception as e:
            print('Registration failed: /apis/{}'.format(api_name))
            msg = get_error_message()
            print(msg)
            return False, msg

api_manager = APIManager()


class RootResource:
    """
    API の管理ができる index ページを表示する．
    URL: /
    """
    def on_get(self, req, resp):
        resp.content_type = falcon.MEDIA_HTML
        with open('./index.html', 'r') as f:
            resp.body = f.read()

        api_list = [i[1:] for i in glob.glob('./apis/*')]
        # TODO: 実際に app に登録されているもののみを表示すべき

        # TODO: 最低限のセキュリティ（外部者に API 削除される・・・）
        resp.body = resp.body.replace('{api_list}', ', '.join(api_list))

        
class RegisterResource:
    """
    API の登録を行う．
    URL: /query/register
    """
    def on_post(self, req, resp):
        file = req.get_param('file')
        print('file:', file)
        if isinstance(file, cgi.FieldStorage):
            api_name = req.get_param('api_name')
            if isinstance(api_name, str) and len(api_name) > 0:
                if is_healthy_api_name(api_name):
                    raw = file.file.read()
                    with open('./apis/_', 'wb') as f:
                        f.write(raw)

                    # zip ファイルを展開し，所定のディレクトリに保存する．
                    with zipfile.ZipFile('./apis/_') as f:
                        f.extractall('./apis/__')
                    api_path = './apis/{}/'.format(api_name)
                    flg_reload = False
                    if os.path.exists(api_path):
                        shutil.rmtree(api_path)
                        flg_reload = True
                    os.rename('./apis/__', api_path)
                    os.remove('./apis/_')

                    # ディレクトリに保存された内容を元に，新しい API を登録する．
                    flg, msg = api_manager.register_api_from_directory(api_name)

                    if flg:
                        print('successfully added new route: /apis/{}'.format(api_name))
                        obj = 'successfully added new route: /apis/{}'.format(api_name)
                        if flg_reload:
                            obj += ' (reloaded)'
                    else:
                        obj = 'error while adding new route: /apis/{} \n {}'.format(api_name, msg)
                else:
                    obj = 'use a-z, 0-9, -, and _ only in `api_name` (actual: {})'.format(api_name)
            else:
                obj = 'specify parameter `api_name`'
        else:
            obj = 'specify file.'

        resp.body = json.dumps(obj, ensure_ascii=False)
        # TODO もっと machine-friendly なフォーマットで結果を返却する


class ExamplesResource:
    """
    examples ディレクトリ内の任意のファイルを，テキスト形式としてそのまま表示する．
    URL: /examples/{filename}
    """
    def on_get(self, req, resp, filename):
        resp.content_type = falcon.MEDIA_TEXT
        with open('./examples/{}'.format(filename), 'r') as f:
            resp.body = f.read()

class DeleteResource:
    """
    API を削除する．
    URL: /query/delete
    """
    def on_post(self, req, resp):
        api_name = req.get_param('api_name')
        if isinstance(api_name, str) and len(api_name) > 0:
            if is_healthy_api_name(api_name):

                flg, msg = api_manager.delete_api(api_name)

                if flg:
                    print('successfully deleted route: /apis/{}'.format(api_name))
                    obj = 'successfully deleted route: /apis/{}'.format(api_name)
                else:
                    obj = 'error while deleting route; /apis/{} \n {}'.format(api_name, msg)
            else:
                obj = 'use a-z, 0-9, -, and _ only in `api_name` (actual: {})'.format(api_name)
        else:
            obj = 'specify parameter `api_name`'

        resp.body = json.dumps(obj, ensure_ascii=False)
        # TODO もっと machine-friendly なフォーマットで結果を返却する

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='SELF-CONTAINED SERVER')
    # parser.add_argument('FILENAME', help='input filename')
    parser.add_argument('--port', '-p', type=int, default=8000,
                        help='port number')
    args = parser.parse_args()

    # api registration
    app.add_route('/', RootResource())
    app.add_route('/query/register', RegisterResource())
    app.add_route('/query/delete', DeleteResource())
    app.add_route('/examples/{filename}', ExamplesResource())
    for d in glob.glob('./apis/*/'):
        api_name = d[7:-1]
        api_manager.register_api_from_directory(api_name)


    from wsgiref import simple_server
    httpd = simple_server.make_server("127.0.0.1", args.port, app)
    print("Server started!")
    httpd.serve_forever()