import os

CURRENT_PATH = os.path.dirname(os.path.abspath(__file__))
ROOT_PATH = os.path.dirname(CURRENT_PATH)

log_path = os.path.join(ROOT_PATH, 'log')
# 采集经纬度
lng_lats = [[114.431193, 30.525967],
            [114.432802, 30.525247],
            [114.433382, 30.523344],
            [114.433489, 30.521866],
            [114.432802, 30.520629],
            [114.433961, 30.519594],
            [114.431686, 30.518837],
            [114.430399, 30.519446],
            [114.429712, 30.520998],
            [114.429411, 30.524434]]

# [391, 599 745, 539 872, 379 896, 254 745, 150 999, 63 499, 0 217, 51  66, 181 0, 470]
# 设置图像高宽
pix_h, pix_w = 2000, 2000

# 串口端口号
# port = 'com4'
port = None
# 串口波特率
baud = 9600
# 串口超时
com_timeout = 0.5

# 串口发送间隔
com_send_sleep_time = 0.5
# 本地服务端口
web_port = 8899

tcp_server_ip = '127.0.0.1'
tcp_server_port = 9090

speed_scale = 1.5
b_shirink = False
test = False