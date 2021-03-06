import falcon
from falcon_multipart.middleware import MultipartMiddleware
import json
import os
import shutil
import subprocess
import time
import importlib
import zipfile
import glob
import sys
import argparse
import cgi
import traceback
import datetime


def get_error_message(sys_exc_info=None):
    ex, ms, tb = sys.exc_info() if sys_exc_info is None else sys_exc_info
    # return '[Error]\n' + str(ex) + '\n' + str(ms)
    return ''.join(traceback.format_exception(ex, ms, tb))

class CORSMiddleware:
    def process_request(self, req, resp):
        resp.set_header('Access-Control-Allow-Origin', '*')
        resp.set_header('Access-Control-Allow-Methods', '*')
        resp.set_header('Access-Control-Allow-Headers', '*')
        # resp.set_header('Access-Control-Max-Age', 1728000)  # 20 days
        if req.method == 'OPTIONS':
            raise falcon.http_status.HTTPStatus(falcon.HTTP_200, body='\n')




app = falcon.API(middleware=[CORSMiddleware(), MultipartMiddleware()])


def is_healthy_api_name(s):
    """
    api_name に使用可能な文字列かを判定する．
    --------
    Args: s (str)
    Returns: (bool)
    """
    if s == '': return False
    if s[0] == '_': return False
    for c in s:
        if (c < 'a' or 'z' < c) and (c < '0' or '9' < c) and c not in '-_': return False
    return True


def is_healthy_package_name(s):
    """
    package_name に使用可能な文字列かを判定する．
    --------
    Args: s (str)
    Returns: (bool)
    """
    if s == '': return False
    for c in s:
        if (c < 'a' or 'z' < c) and (c < 'A' or 'Z' < c) and (c < '0' or '9' < c) and c not in '-_.': return False
    return True

'''
def execute_shell_command(com):
    """
    Args:
        com (list of str): コマンド．例： ["pip", "install", "-U", "tqdm"]

    ※ com の内容の安全性や危険性について，この関数内では一切評価しないので注意．
    """
    proc = subprocess.run(com, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
    return 
'''

class RootResource:
    """
    API の管理ができる index ページを表示する．
    URL: /
    """
    def __init__(self, started_at):
        self.started_at = started_at

    def on_get(self, req, resp):
        resp.content_type = falcon.MEDIA_HTML
        with open('./index.html', 'r') as f:
            resp.body = f.read()
        # TODO: 最低限のセキュリティ（外部者に API 削除される・・・）

        api_name_list = apis_resource.get_api_name_list()
        api_list = ['./apis/{}'.format(name) for name in api_name_list]
        api_list = ['<a href="{}">{}</a>'.format(a, a) for a in api_list]
        if len(api_list) > 0:
            resp.body = resp.body.replace('{api_list}', ', '.join(api_list))
        else:
            resp.body = resp.body.replace('{api_list}', '(None)')

        resp.body = resp.body.replace('{started_at}', self.started_at.strftime('%Y/%m/%d %H:%M:%S'))


class APIsResource:
    """
    API の呼び出しを行う．（ルーティング）
    URL: /apis/{api_name}
    """ 
    def __init__(self):
        self.api_dict = dict()
        # 最初からディレクトリにある apis を自身に登録する．ただし unhealthy な名前のディレクトリは対象にしない．
        for d in glob.glob('./apis/*/'):
            api_name = d[7:-1]
            if is_healthy_api_name(api_name):
                self.add_api(api_name)

    def get_api_name_list(self):
        return list(self.api_dict.keys())

    def add_api(self, api_name):
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
            importlib.reload(NewModule) # reload の場合はこれが必要．（reload でない場合もこれを実行して良い．）
            api_resource = NewModule.APIResource()
            if api_name in self.api_dict:
                old_resource = self.api_dict.pop(api_name)
                del old_resource
            self.api_dict[api_name] = api_resource
            return True, ''
        except Exception as e:
            print('Registration failed: /apis/{}'.format(api_name))
            msg = get_error_message()
            print(msg)
            return False, msg

    def del_api(self, api_name):
        """
        ./apis/{api_name} の API を削除する．
        --------
        Args:
            api_name (str): APIの名称．名称の適切性（例えばスラッシュやドットが含まれていない等）は判定されません．

        Returns:
            ((bool), (str)): 削除に正常に成功したか否か，及びエラーメッセージ
        """
        try:
            if api_name in self.api_dict:
                resource = self.api_dict.pop(api_name)
                del resource
                api_path = './apis/{}'.format(api_name)
                if os.path.exists(api_path):
                    shutil.rmtree(api_path)
                return True, ''
            else:
                return False, 'not such api registered: {}'.format(api_name)
        except:
            msg = get_error_message()
            print(msg)
            return False, msg

    def on_get(self, req, resp, api_name):
        """
        ルーティング (GET)
        """
        if api_name in self.api_dict:
            try:
                self.api_dict[api_name].on_get(req, resp)
            except:
                err = get_error_message()
                resp.status = falcon.HTTP_500
                resp.body = json.dumps({
                    'code': -100,
                    'message': 'Error occured during processing /apis/{}: {}'.format(api_name, err),
                    'result': None
                })
        else:
            resp.status = falcon.HTTP_404

    def on_post(self, req, resp, api_name):
        """
        ルーティング (POST)
        """
        if api_name in self.api_dict:
            try:
                self.api_dict[api_name].on_post(req, resp)
            except:
                err = get_error_message()
                resp.status = falcon.HTTP_500
                resp.body = json.dumps({
                    'code': -100,
                    'message': 'Error occured during processing /apis/{}: {}'.format(api_name, err),
                    'result': None
                })
        else:
            resp.status = falcon.HTTP_404
apis_resource = APIsResource()



class RegisterResource:
    """
    API の登録を行う．
    URL: /query/register
    """
    def on_post(self, req, resp):
        code, message, result = 0, '', None
        file = req.get_param('file')
        if isinstance(file, cgi.FieldStorage):
            api_name = req.get_param('api_name')
            if isinstance(api_name, str) and len(api_name) > 0:
                if is_healthy_api_name(api_name):
                    raw = file.file.read()
                    with open('./apis/_', 'wb') as f:
                        f.write(raw)

                    # zip ファイルを展開し，所定のディレクトリに保存する．
                    try:
                        with zipfile.ZipFile('./apis/_') as f:
                            f.extractall('./apis/__')
                    except zipfile.BadZipFile:
                        shutil.rmtree('./apis/__/')
                        code = 10
                        message = 'File is not a zip file.'
                    except:
                        shutil.rmtree('./apis/__/')
                        err = get_error_message()
                        code = 11
                        message = 'error while extracting zip file : {}'.format(err)
                    else:
                        api_path = './apis/{}/'.format(api_name)
                        flg_reload = False
                        if os.path.exists(api_path):
                            shutil.rmtree(api_path)
                            flg_reload = True
                        os.rename('./apis/__', api_path)
                        os.remove('./apis/_')

                        # ディレクトリに保存された内容を元に，新しい API を登録する．
                        flg, err = apis_resource.add_api(api_name)

                        if flg:
                            print('Successfully added new route /apis/{}'.format(api_name))
                            message = 'Successfully added new route /apis/{}'.format(api_name)
                            if flg_reload:
                                message += ' (reloaded)'
                        else:
                            shutil.rmtree(api_path) # 正常に API を登録できなかった場合は，フォルダ削除する．
                            code = 1
                            message = 'Error while adding new route /apis/{} : {}'.format(api_name, err)
                else:
                    code = 2
                    message = 'Use only a-z, 0-9, -, and _ in `api_name`. Also, first letter must not be _ (actual: {})'.format(api_name)
            else:
                code = 3
                message = 'Specify parameter `api_name`'
        else:
            code = 4
            message = 'Specify `file`'

        resp.body = json.dumps({
            'code': code,
            'message': message,
            'result': result
        }, ensure_ascii=False)


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
        code, message, result = 0, '', None
        api_name = req.get_param('api_name')
        if isinstance(api_name, str) and len(api_name) > 0:
            if is_healthy_api_name(api_name):

                flg, err = apis_resource.del_api(api_name)

                if flg:
                    print('Successfully deleted route: /apis/{}'.format(api_name))
                    message = 'Successfully deleted route: /apis/{}'.format(api_name)
                else:
                    code = 1
                    message = 'Error while deleting route: /apis/{}  \n{}'.format(api_name, err)
            else:
                code = 2
                message = 'Use only a-z, 0-9, -, and _ in `api_name`. Also, first letter must not be _ (actual: {})'.format(api_name)
        else:
            code = 3
            message = 'Specify parameter `api_name`'

        resp.body = json.dumps({
            'code': code,
            'message': message,
            'result': result
        }, ensure_ascii=False)


class PipInstallResource:
    """
    pip install する．
    URL: /query/pip_install
    """
    def on_post(self, req, resp):
        code, message, result = 0, '', None
        package_name = req.get_param('package_name')
        if isinstance(package_name, str) and len(package_name) > 0:
            if is_healthy_package_name(package_name):

                command_str = 'pip install -U {}'.format(package_name)

                proc = subprocess.Popen(
                    command_str.strip().split(' '),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                try:
                    out, err = proc.communicate(timeout=50)
                except subprocess.TimeoutExpired:
                    # proc.kill()
                    out, err = '', ''
                    flg = False
                else:
                    flg = True

                out = out.decode('utf-8') if isinstance(out, bytes) else out
                err = err.decode('utf-8') if isinstance(err, bytes) else err

                if flg:
                    print('Finished `{}`: \n{}\n{}'.format(command_str, out, err))
                    message = 'Finished `{}`: \n{}\n{}'.format(command_str, out, err)
                else:
                    code = 1
                    message = 'Timeout (may be still running): `pip install -U {}`'.format(package_name)
            else:
                code = 2
                message = 'There are some invalid characters in the package_name ({})'.format(package_name)
        else:
            code = 3
            message = 'Specify parameter `package_name`'

        resp.body = json.dumps({
            'code': code,
            'message': message,
            'result': result
        }, ensure_ascii=False)

class RestartResource:
    """
    サーバーを再起動する．
    URL: /query/restart
    """
    def __init__(self, port):
        self.port = port

    def on_post(self, req, resp):
        code, message, result = 0, 'This server will restart in a few seconds.', None
        resp.body = json.dumps({
            'code': code,
            'message': message,
            'result': result
        }, ensure_ascii=False)
        # with open('_restart.sh', 'w') as f:
        #     f.write('sleep 5; python self_contained_server.py -p {}\n'.format(self.port))
        python = sys.executable
        os.execl(python, python, *sys.argv)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='SELF-CONTAINED SERVER')
    # parser.add_argument('FILENAME', help='input filename')
    parser.add_argument('--port', '-p', type=int, default=8000,
                        help='port number')
    args = parser.parse_args()

    started_at = datetime.datetime.now()

    # api registration
    app.add_route('/', RootResource(started_at=started_at))
    app.add_route('/query/register', RegisterResource())
    app.add_route('/query/delete', DeleteResource())
    app.add_route('/query/pip_install', PipInstallResource())
    app.add_route('/query/restart', RestartResource(port=args.port))
    app.add_route('/examples/{filename}', ExamplesResource())
    app.add_route('/apis/{api_name}', apis_resource)


    from wsgiref import simple_server
    httpd = simple_server.make_server("127.0.0.1", args.port, app)
    print("Server started at port {}!".format(args.port))
    httpd.serve_forever()
