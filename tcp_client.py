import config
import socket
import logging

logger = logging


class TcpClient:
    def __init__(self):
        self.target_host = config.tcp_server_ip  # 服务器端地址
        self.target_port = config.tcp_server_port  # 必须与服务器的端口号一致
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        while True:
            try:
                self.client.connect((self.target_host, self.target_port))
                break
            except Exception as e:
                print('error',e)
                continue

    def send(self, data):
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client.connect((self.target_host, self.target_port))
        if not data:
            return
        self.client.send(data.encode())
        # response = self.client.recv(1024)
        # print(response)
        # self.client.close()

    def get(self):
        while True:
            response = self.client.recv(1024)
            print(response)
            str_response = str(response)[2:-1]
            if len(str_response) > 0:
                logger.info({'response': str_response})
            # 发送了开始
            print('str_response',str_response)
            if str_response == 'as':
                self.send('asc')
                print('send asc')
            # 发送了结束
            elif str_response == 'cs':
                self.send('csc')
                print('send csc')
            else:
                self.send('error')

if __name__ == '__main__':
    tcp_client_obj = TcpClient()
    tcp_client_obj.get()
