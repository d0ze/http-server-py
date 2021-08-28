import socket
import json
import argparse

class SocketServer:
    def __init__(self, host='127.0.0.1', port=65432):
        self.host, self.port = host, port
        self.socket = None
        self.connection = None
        self.controller = Controller()

    def accept_connections(self):
        self.socket.listen(0)
        return self.socket.accept()

    def create_socket(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def build_response(self, json_data, content_type, status_code):
        code_to_text = {200: 'Ok ',
                        201: 'Created ',
                        204: 'No-Content ',
                        500: 'Ko ',
                        }
        response_body = json_data

        response_body_raw = json.dumps(response_body)

        # Clearly state that connection will be closed after this response,
        # and specify length of response body
        response_headers = {
            'Content-Type': f'{content_type}',
            'Content-Length': len(response_body_raw),
            'Connection': 'close',
        }

        response_headers_raw = ''.join(f'{k}: {v}\n' for k, v in response_headers.items())

        # Reply as HTTP/1.1 server, saying "HTTP OK" (code 200).
        response_proto = b'HTTP/1.1'
        response_status = status_code.encode()
        response_status_text = code_to_text[int(status_code)].encode()
        return response_headers_raw, response_proto, response_status, response_status_text, response_body_raw

    def send_response(self, response):
        resp_data = response['data']
        headers, proto, status, text, body = self.build_response(json_data=resp_data,
                                                                 content_type=self.get_response_content_type(resp_data),
                                                                 status_code=str(response['status_code']))
        print(f"==== Response \n{response}")
        self.connection.send(b'%s %s %s\r\n' % (proto, status, text))
        self.connection.send(headers.encode())
        self.connection.send(b'\n')
        self.connection.send(body.encode())

    def get_response_content_type(self, response_data):
        if isinstance(response_data, dict):
            return 'application/json; charset=utf8'
        elif isinstance(response_data, str):
            return 'application/x-www-form-urlencoded; charset=utf8'
        else:
            return 'text/plain'

    def parse_request(self, data):
        data = data.decode()
        print(f"==== Request \n{data}")
        meta, body = data.split('\r\n\r\n')
        meta_chunks = meta.split('\r\n')
        start_line = meta_chunks[0]
        headers = meta_chunks[1:]
        formatted_headers = {h.split(':')[0]: h.split(':')[1] for h in headers}
        http_method, protocol_version = start_line.split(' / ')
        return http_method, body, formatted_headers

    def start(self):
        print(f"===== Starting socket server...")
        if not self.socket:
            self.create_socket()
        with self.socket as s:
            print(f"===== Binding on  {self.host}:{self.port}\n")
            s.bind((self.host, self.port))
            while not self.connection:
                self.connection, address = self.accept_connections()
                try:
                    method, body, headers = self.parse_request(self.connection.recv(1024))
                    response_data = self._dispatch_request(method, body, headers)
                    self.send_response(response_data)
                except Exception as e:
                    response_data = {'status_code': 500, 'data': {'Error': {e}}}
                    self.send_response(response_data)
                self.connection, address = None, None

    def _dispatch_request(self, method, body, headers):
        return getattr(self.controller, method.lower())(body, headers)


class Controller(object):
    def get(self, request_data, headers):
        return {'status_code': 200, 'data': {'lorem': 'ipsum'}}

    def post(self, request_data, headers):
        return {'status_code': 201, 'data': {'dolor': 'sic'}}

    def put(self, request_data, headers):
        return {'status_code': 200, 'data': {'put': request_data}}

    def patch(self, request_data, headers):
        return {'status_code': 200, 'data': {'patch': request_data}}

    def delete(self, request_data, headers):
        return {'status_code': 204, 'data': {}}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-host')
    parser.add_argument('-port', type=int)
    args = parser.parse_args()
    server = SocketServer(host=args.host, port=args.port)
    server.start()
