import com_data
import log
import config
import cv2
import numpy as np
from flask import Flask, request
from flask import render_template
from flask_cors import CORS
import os
import json
import time
import threading
app = Flask(__name__)

CORS(app)


app = Flask(__name__, template_folder='template')


@app.route('/')
def index():
    return render_template('vue-map.html')
    # return render_template('map-1.html')

# 湖轮廓像素位置
@app.route('/pool_cnts', methods=['GET', 'POST'])
def pool_cnts():
    print(request)
    print("request.url", request.url)
    print("request.args", request.args)
    # 失败返回提示信息
    if ship_obj.pix_cnts is None:
        return '初始经纬度像素点未生成'
    #{'data':'391, 599 745, 539 872, 379 896, 254 745, 150 999, 63 499, 0 217, 51  66, 181 0, 470'}
    else:
        str_pix_points = ''
        for index, value in enumerate(ship_obj.pix_cnts):
            if index == len(ship_obj.pix_cnts) - 1:
                str_pix_points += str(value[0]) + ',' + str(value[1])
            else:
                str_pix_points += str(value[0]) + ',' + str(value[1]) + ' '
        return_json = json.dumps({'data': str_pix_points})
        return return_json

# 获取在线船列表
@app.route('/online_ship', methods=['GET', 'POST'])
def online_ship():
    print(request)
    print('request.data', request.data)
    data = json.loads(request.data)
    ship_obj.click_pix_points = data['data']
    return 'confirm'

# 发送一条船配置路径
@app.route('/ship_path', methods=['GET', 'POST'])
def ship_path():
    print(request)
    print('request.data', request.data)
    data = json.loads(request.data)
    ship_obj.click_pix_points = data['data']
    return 'confirm'

# 发送所有配置路径到船
@app.route('/send_path', methods=['GET', 'POST'])
def send_path():
    print(request)
    ship_obj.b_send_path = True
    return 'send_path'

# 控制船运动
@app.route('/ship_control', methods=['GET', 'POST'])
def ship_control():
    print(request)
    print(request)
    print('request.data', request.data)
    data = json.loads(request.data)
    for i in enumerate(data['ids']):
        ship_obj.ship_control_list.update({data['ids'][i]:data['control_data'][i]})
    return 'ship_control'

class Ship:

    def __init__(self):
        self.logger = log.LogHandler('mian')
        self.com_logger = log.LogHandler('com_logger')

        # 湖泊像素轮廓点
        self.pix_cnts = None
        # 当前船号，船位置，船规划行驶点
        self.online_ship_list = []

        # 手动控制状态
        self.ship_control_list={}

        # 像素位置与经纬度
        self.ship_pix_position = {}
        self.ship_lng_lat_position = {}
        # 用户点击像素点
        self.click_pix_points = {}
        # 用户点击经纬度点
        self.click_lng_lats = {}
        # 是否发送所有路径到船
        self.b_send_path = False

    # 必须放在主线程中
    @staticmethod
    def run_flask():
        app.run(host='0.0.0.0', port=8899, debug=True)

    # 经纬度转像素
    def lng_lat_to_pix(self,lng_lat):
        """
        :param lng_lat: 经纬度
        :return:
        """
        int_lng_lat = [int(lng_lat[0] * 1000000), int(lng_lat[1] * 1000000)]
        int_lng_lats_offset = [int_lng_lat[0] - self.left_up_x, int_lng_lat[1] - self.left_up_y]
        int_lng_lats_pix = [int(int_lng_lats_offset[0] / self.scale_w), int(int_lng_lats_offset[1] / self.scale_h)]
        return int_lng_lats_pix

    # 像素转经纬度
    def pix_to_lng_lat(self, pix):
        """
        :param pix:像素位置 先w 后h
        :return: 经纬度
        """
        lng = round((self.left_up_x + pix[0] * self.scale_w) / 1000000.0, 6)
        lat = round((self.left_up_y + pix[1] * self.scale_h) / 1000000.0, 6)
        return [lng,lat]

    def init_cnts_lng_lat_to_pix(self, b_show=False):
        while not os.path.exists('lng_lats.txt'):
            time.sleep(1)
        lng_lats_list = []
        try:
            with open('lng_lats.txt', 'r') as f:
                temp_list = f.readlines()
                for i in temp_list:
                    i = i.strip()
                    lng_lats_list.append(
                        [float(i.split(',')[0]), float(i.split(',')[1])])
        except Exception as e:
            self.logger.error({'lng_lats.txt error':e})

        int_lng_lats = [[int(i[0] * 1000000), int(i[1] * 1000000)]
                        for i in lng_lats_list]
        (left_up_x, left_up_y, w, h) = cv2.boundingRect(np.array(int_lng_lats))
        self.left_up_x = left_up_x
        self.left_up_y = left_up_y
        self.logger.info({'(x, y, w, h) ': (left_up_x, left_up_y, w, h)})
        # 像素到单位缩放
        self.scale_w = float(w) / config.pix_w
        self.scale_h = float(h) / config.pix_h

        # 经纬度转像素
        self.pix_cnts = [self.lng_lat_to_pix(i) for i in lng_lats_list]
        self.logger.info({'self.pix_cnts': self.pix_cnts})

        if b_show:
            img = np.zeros((config.pix_h, config.pix_w, 3), dtype=np.uint8)
            cv2.circle(img, (int(config.pix_w / 2),
                             int(config.pix_h / 2)), 5, (255, 0, 255), -1)
            cv2.drawContours(
                img,
                np.array(
                    [self.pix_cnts]),
                contourIdx=-1,
                color=(255, 0, 0))

            print(img.shape)
            # 鼠标回调函数
            # x, y 都是相对于窗口内的图像的位置
            def draw_circle(event, x, y, flags, param):
                # 判断事件是否为 Left Button Double Clicck
                if event == cv2.EVENT_LBUTTONDBLCLK or event == cv2.EVENT_LBUTTONDOWN:
                    in_cnt = cv2.pointPolygonTest(
                        np.array([self.pix_cnts]), (x, y), False)
                    # 大于0说明属于该轮廓
                    if in_cnt >= 0:
                        print('像素', x, y)
                        lng = round((left_up_x + x * self.scale_w) / 1000000.0, 6)
                        lat = round((left_up_y + y * self.scale_h) / 1000000.0, 6)
                        print('经纬度', lng, lat)
                        cv2.circle(img, (x, y), 5, (255, 0, 0), -1)
                if event == cv2.EVENT_RBUTTONDOWN:
                    in_cnt = cv2.pointPolygonTest(
                        np.array([self.pix_cnts ]), (x, y), False)
                    # 大于0说明属于该轮廓
                    if in_cnt >= 0:
                        print('像素', x, y)
                        lng = round((left_up_x + x * self.scale_w) / 1000000.0, 6)
                        lat = round((left_up_y + y * self.scale_h) / 1000000.0, 6)
                        print('经纬度', lng, lat)
                        cv2.circle(img, (x, y), 5, (255, 0, 0), -1)

            cv2.namedWindow('img')
            # 设置鼠标事件回调
            cv2.setMouseCallback('img', draw_circle)
            print('22222222222222222222222222222')
            while (True):
                cv2.imshow('img', img)
                if cv2.waitKey(1) == ord('q'):
                    break
            # cv2.waitKey(0)
            cv2.destroyAllWindows()

    # 发送串口数据
    def send_com_data(self):
        self.serial_obj = com_data.SerialData(
            config.port,
            config.baud,
            timeout=config.com_timeout,
            logger=self.com_logger)
        while True:
            if len(ship_obj.click_pix_points) <= 0 or not ship_obj.b_send_path:
                time.sleep(1)
            else:
                # 像素转换为经纬度
                for k, v in ship_obj.click_pix_points.items():
                    lng = round(
                        (self.left_up_x + v[0] * self.scale_w) / 1000000.0, 6)
                    lat = round(
                        (self.left_up_y + v[1] * self.scale_h) / 1000000.0, 6)
                    ship_obj.click_lng_lats.update({k: [lng, lat]})
                # 转换为发送数据
                com_data_send = 'BB'
                for k, v in ship_obj.click_lng_lats.items():
                    com_data_send += com_data_send + '%03d,' % k + \
                        str(v[0]) + ',' + str(v[1]) + '#'
                com_data_send += com_data_send + '$'
                self.serial_obj.send_data(com_data_send)
            # TODO 等待与手动停止控制
            # time.sleep()

    def get_com_data(self):
        # 读取函数会阻塞 必须使用线程
        while True:
            com_data_read = self.serial_obj.readline()
            # 解析串口发送过来的数据
            if com_data_read is None:
                continue
            self.logger.debug({'com_data_read': com_data_read})
            # 解析串口发送过来的数据
            try:
                get_com_data_list = com_data_read.split(',')
                ship_id = int(get_com_data_list[0])
                self.online_ship_list.append(ship_id)
                com_lng_lat = [float(get_com_data_list[1]),float(get_com_data_list[2])]
                # 更新经纬度
                self.ship_lng_lat_position.update({ship_id:com_lng_lat})
                # 经纬度转像素
                com_pix = self.lng_lat_to_pix(com_lng_lat)
                # 更新像素
                self.ship_pix_position.update({ship_id:com_pix})
            except Exception as e:
                self.logger.error({'com_data_read error': e})


if __name__ == '__main__':
    ship_obj = Ship()
    init_cnts_lng_lat_to_pix = threading.Thread(target=ship_obj.init_cnts_lng_lat_to_pix)
    # get_com_thread = threading.Thread(target=ship_obj.get_com_data)
    # send_com_thread = threading.Thread(target=ship_obj.send_com_data)

    init_cnts_lng_lat_to_pix.setDaemon(True)
    # get_com_thread.setDaemon(True)
    # send_com_thread.setDaemon(True)

    init_cnts_lng_lat_to_pix.start()
    # get_com_thread.start()
    # send_com_thread.start()

    init_cnts_lng_lat_to_pix.join()
    # get_com_thread.join()
    # send_com_thread.join()

    ship_obj.run_flask()
