import os
from utils import lng_lat_calculate
CURRENT_PATH = os.path.dirname(os.path.abspath(__file__))
ROOT_PATH = os.path.dirname(CURRENT_PATH)

log_path = os.path.join(CURRENT_PATH, 'log')
save_img_path = os.path.join(CURRENT_PATH, 'statics', '2.png')
gps_gaode_path = os.path.join(CURRENT_PATH, 'gps_gaode.json')
# src_gps = [116.481499,39.990475]
# src_gaode = [116.487585177952,39.991754014757]
src_gps = [114.520212, 30.50848]
src_gaode = [114.525421278212, 30.505929633247]
zoom = 16
width = 600
height = 600
lng_lat = (114.525685,30.505769)
lng_lat_gps = lng_lat_calculate.gps_gaode_to_gps(src_gps, src_gaode, lng_lat)
print(lng_lat,lng_lat_gps)
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
pix_h, pix_w = 600, 600

# 串口端口号
# port = 'com4'
# 串口波特率
baud = 9600
# 串口超时
com_timeout = 0.5

# 串口发送间隔
com_send_sleep_time = 0.4
# 本地服务端口
web_port = 8899

tcp_server_ip = '0.0.0.0'
# tcp_server_ip = '192.168.8.19'
# tcp_server_ip = '*'
# tcp_server_ip = '127.0.0.1'
tcp_server_port = 9090

speed_scale = 1.2
b_shirink = False
test = False
