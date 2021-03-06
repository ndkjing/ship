import com_data
from utils import log
from utils import lng_lat_calculate
from utils import shirink
import config
import socket

import cv2
import numpy as np
from flask import Flask, request
from flask import render_template
from flask_cors import CORS
import os
import json
import time
import threading
import sys
import random
import logging
import copy
import sys
import serial
print('path: ', os.path.dirname(os.path.abspath(__file__)))


# 获取资源路径
def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


# CORS(app,supports_credentials=False)

log1 = logging.getLogger('xxl')
log1.disabled = True
app = Flask(__name__, template_folder=resource_path('templates'), static_folder=resource_path('statics'))
app.logger.disabled = True

CORS(app, resources=r'/*')
# 测试使用
b_test = config.test


@app.route('/')
def index():
    return render_template('map319.html')


logger = log.LogHandler('main')


# 湖轮廓像素位置
@app.route('/pool_cnts', methods=['GET', 'POST'])
def pool_cnts():
    # 失败返回提示信息
    print(request)
    print('pool_cnts',ship_obj.pix_cnts)
    if not ship_obj.pix_cnts:
        return '初始经纬度像素点未生成'
    # {'data':'391, 599 745, 539 872, 379 896, 254 745, 150 999, 63 499, 0 217, 51  66, 181 0, 470'}
    else:
        str_pix_points = ''
        for index, value in enumerate(ship_obj.pix_cnts):
            if index == len(ship_obj.pix_cnts) - 1:
                str_pix_points += str(value[0]) + ',' + str(value[1])
            else:
                str_pix_points += str(value[0]) + ',' + str(value[1]) + ' '
        return_json = json.dumps({'data': str_pix_points})
        print('return_json pool_cnts', return_json)
        return return_json


# 获取在线船列表
@app.route('/online_ship', methods=['GET', 'POST'])
def online_ship():
    # print('request.data', request.data)
    if b_test:
        random_data = random.randint(1, 50)
        points_status = {}
        for i in ship_obj.config_ship_lng_lats_dict.keys():
            point_status = [0] * len(ship_obj.config_ship_lng_lats_dict.get(i))
            if random_data > 25:
                point_status[0] = 1
            points_status.update({i: point_status})
        return_data = {
            # 船号
            "ids": [1, 2, 8, 10, 18],
            # 船像素信息数组
            "pix_postion": [[383 + random_data, 499 - random_data], [132 + random_data, 606 - random_data],
                            [52 - random_data, 206 + random_data], [0 + random_data, 569 + random_data]],
            # 船是否配置行驶点 1为已经配置  0位还未配置
            "config_path": [1 if i in ship_obj.config_ship_pix_points_dict else 0 for i in [1, 2, 8, 10, 18]],
            # 船剩余电量0-100整数
            "dump_energy": [90, 37, 80, 60],
            # 船速度 单位：m/s  浮点数
            "speed": [3.5 + random_data / 5.0, 2.0, 1.0, 5.0],
            "direction": [30 + random_data, 60 + random_data, 100 + random_data, 180 + random_data],
            "points_status": points_status
        }
        return json.dumps(return_data)
    else:
        return_data = {
            # 船号
            "ids": ship_obj.online_ship_list,
            # 船像素信息数组
            "pix_postion": [ship_obj.ship_pix_position_dict.get(i) for i in ship_obj.online_ship_list],
            # 船是否配置行驶点 1为已经配置  0位还未配置
            "config_path": [1 if i in ship_obj.config_ship_lng_lats_dict else 0 for i in ship_obj.online_ship_list],
            # 船剩余电量0-100整数
            "dump_energy": [ship_obj.ship_dump_energy_dict.get(i) for i in ship_obj.online_ship_list],
            # 船速度 单位：m/s  浮点数
            "speed": [ship_obj.ship_speed_dict.get(i) for i in ship_obj.online_ship_list],
            "direction": [ship_obj.ship_direction_dict.get(i) for i in ship_obj.online_ship_list],
            "points_status": ship_obj.config_ship_points_status
        }
        # print('online_ship data',return_data)
        return json.dumps(return_data)


# 获取所有配置路径
@app.route('/get_all_config', methods=['GET', 'POST'])
def get_all_config():
    print('get_all_config', request)
    ids = []
    pix_postion = []
    for i in ship_obj.config_ship_pix_points_dict.keys():
        ids.append(i)
        pix_postion.append(ship_obj.config_ship_pix_points_dict.get(i))
    # 船像素信息数组
    return_data = {
        # 船号
        "ids": ids,
        "pix_postion": pix_postion,
    }
    # try:
    #     logger.info({'get_all_config': return_data})
    # except Exception as e:
    #     return
    return json.dumps(return_data)


# 发送一条船配置路径
@app.route('/ship_path', methods=['GET', 'POST'])
def ship_path():
    data = json.loads(request.data)
    print('ship_path', data)
    if not ship_obj.pix_cnts :
        return '还没有湖，别点'
    if not data.get('id'):
        return 'no ship points data'
    ids_list = []
    for i in data['id'].split(' '):
        try:
            id = int(i)
            ship_obj.ship_control_dict.update({int(id): 1})
            ids_list.append(id)
        except Exception as e:
            logger.error({'error: ': e})
    # 没有合法id
    if len(ids_list) == 0:
        return
    for id in ids_list:
        # 发送第一个点
        if ship_obj.config_ship_lng_lats_dict.get(id):
            ship_obj.b_send_first_point = True
        if not data.get('data') or len(data.get('data')) < 1:
            return 'error'
        if data['data'][0][0].endswith('px'):
            click_pix_points = [[int(i[0][:-2]), int(i[1][:-2])] for i in data['data']]
        else:
            click_pix_points = [[int(i[0]), int(i[1])] for i in data['data']]
        click_lng_lats = []
        click_inpool_pix_point = []
        for point in click_pix_points:
            in_cnt = cv2.pointPolygonTest(np.array(ship_obj.pix_cnts), (point[0], point[1]), False)
            if in_cnt >= 0:
                click_inpool_pix_point.append(point)
                click_lng_lat = ship_obj.pix_to_lng_lat(point)
                click_lng_lats.append(click_lng_lat)
        # 第一次有点也发送
        ship_obj.b_send_first_point = True
        ship_obj.config_ship_pix_points_dict.update({id: click_inpool_pix_point})
        ship_obj.config_ship_lng_lats_dict.update({id: click_lng_lats})
        ship_obj.config_ship_points_status.update({id: [0]*len(click_lng_lats)})
    # logger.debug({'config_ship_lng_lats_dict':ship_obj.config_ship_lng_lats_dict})
    return 'ship_path'


# 全部启动
@app.route('/send_path', methods=['GET', 'POST'])
def send_path():
    print(request)
    ship_obj.b_send_path = True
    for i in ship_obj.online_ship_list:
        ship_obj.ship_control_dict.update({int(i): 1})
    return 'send_path'


# 控制船启动
@app.route('/ship_start', methods=['GET', 'POST'])
def ship_start():
    print(request)
    ship_obj.b_send_control = True
    data = json.loads(request.data)
    for i in data['id']:
        ship_obj.ship_control_dict.update({int(i): 1})
    return 'ship_start'


# 控制船停止
@app.route('/ship_stop', methods=['GET', 'POST'])
def ship_stop():
    print(request)
    ship_obj.b_send_control = True
    data = json.loads(request.data)
    for i in data['id']:
        ship_obj.ship_control_dict.update({int(i): 0})
    return 'ship_stop'


# 发送串口
@app.route('/get_coms', methods=['GET', 'POST'])
def get_coms():
    print(request)
    com_list = com_data.SerialData.print_used_com()
    print('com_list', com_list)
    return json.dumps(com_list)


# 接受串口打开
@app.route('/open_com', methods=['GET', 'POST'])
def open_com():
    data = json.loads(request.data)
    print(request, data)
    ship_obj.select_com = str(data)
    return 'open_com'


# 接受串口关闭
@app.route('/close_com', methods=['GET', 'POST'])
def close_com():
    print(request)
    ship_obj.select_com = ''
    return 'close_com'


class Ship:
    def __init__(self):
        self.logger = log.LogHandler('mian')
        self.com_logger = log.LogHandler('com_logger')

        # 湖泊像素轮廓点
        self.pix_cnts = []
        # 当前接收到的船号，
        self.online_ship_list = []
        # 手动控制状态 存储格式 船号：控制 （0 停止  1 启动）
        self.ship_control_dict = {}
        # 像素位置与经纬度
        self.ship_pix_position_dict = {}
        self.ship_lng_lat_position_dict = {}
        # 用户点击像素点
        # self.click_pix_points_dict = {}
        # 船配置航点
        self.config_ship_lng_lats_dict = {}
        # 船配置航点 像素坐标
        self.config_ship_pix_points_dict = {}
        # 船配置航点 到达状态 {1:[1,0,0]}
        self.config_ship_points_status = {}
        # 船剩余电量
        self.ship_dump_energy_dict = {}
        # 船速度
        self.ship_speed_dict = {}
        # 船朝向
        self.ship_direction_dict = {}
        # 是否发送所有路径到船
        self.b_send_path = False
        self.b_send_control = False
        # 采集点经纬度
        self.lng_lats_list = []
        # 记录当前存在的串口
        self.init_com_list = com_data.SerialData.print_used_com()
        # 串口对象
        self.serial_obj = None
        # 用户点击传过来的串口
        self.select_com = ''
        # 点击确定后发送第一个点
        self.b_send_first_point = False

    # 必须放在主线程中
    @staticmethod
    def run_flask(debug=True):
        # app.run(host='192.168.199.171', port=5500, debug=True)
        app.run(host='127.0.0.1', port=config.web_port, debug=True)
        # app.run(host='0.0.0.0', port=config.web_port, debug=debug)

    # 经纬度转像素
    def lng_lat_to_pix(self, lng_lat):
        """
        :param lng_lat: 经纬度
        :return:
        """
        int_lng_lat = [int(lng_lat[0] * 1000000), int(lng_lat[1] * 1000000)]
        int_lng_lats_offset = [int_lng_lat[0] - self.left_up_x, int_lng_lat[1] - self.left_up_y]
        # int_lng_lats_pix = [int(int_lng_lats_offset[0] / self.scale_w), int(int_lng_lats_offset[1] / self.scale_h)]
        int_lng_lats_pix = [int(int_lng_lats_offset[0] / self.scale_w), config.pix_h - int(int_lng_lats_offset[1] / self.scale_h)]
        # int_lng_lats_pix = [int(int_lng_lats_offset[0] / self.scale_w),
        #                     config.pix_h - int(int_lng_lats_offset[1] / self.scale_h)]
        return int_lng_lats_pix

    # 像素转经纬度
    def pix_to_lng_lat(self, pix):
        """
        :param pix:像素位置 先w 后h
        :return: 经纬度
        """
        lng = round((self.left_up_x + pix[0] * self.scale_w) / 1000000.0, 6)
        lat = round((self.left_up_y + pix[1] * self.scale_h) / 1000000.0, 6)
        return [lng, lat]

    def init_cnts_lng_lat_to_pix(self, b_show=False):
        lng_lats_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lng_lats.txt')
        while not os.path.exists(lng_lats_path):
            print('wait lng_lats.txt')
            time.sleep(1)
        try:
            with open(lng_lats_path, 'r') as f:
                temp_list = f.readlines()
                for i in temp_list:
                    i = i.strip()
                    self.lng_lats_list.append(
                        [round(float(i.split(',')[0]), 6), round(float(i.split(',')[1]), 6)])
        except Exception as e:
            self.logger.error({'lng_lats.txt 格式错误': e})
            return
        int_lng_lats_list = [[int(i[0] * 1000000), int(i[1] * 1000000)]
                             for i in self.lng_lats_list]
        (left_up_x, left_up_y, w, h) = cv2.boundingRect(np.array(int_lng_lats_list))
        self.left_up_x = left_up_x
        self.left_up_y = left_up_y
        self.logger.info({'(x, y, w, h) ': (left_up_x, left_up_y, w, h)})
        # 像素到单位缩放 等比拉伸
        if w >= h:
            self.scale_w = float(w) / config.pix_w
            self.scale_h = float(w) / config.pix_w
        else:
            self.scale_w = float(h) / config.pix_w
            self.scale_h = float(h) / config.pix_w
        if config.b_shirink:
            # 收缩
            pix_cnts = [self.lng_lat_to_pix(i) for i in self.lng_lats_list]
            poly = np.array(pix_cnts)
            shrink_poly = shirink.shrink_polygon(poly, 0.9)
            shrink_poly_list_temp = shrink_poly.tolist()
            self.pix_cnts = []
            for i in shrink_poly_list_temp:
                self.pix_cnts.append([int(i[0]),  config.pix_h-int(i[1])])
        else:
            # 经纬度转像素
            # self.pix_cnts = [self.lng_lat_to_pix(i) for i in self.lng_lats_list]
            for i in self.lng_lats_list:
                pix_x,pix_y = self.lng_lat_to_pix(i)
                self.pix_cnts.append([pix_x, config.pix_h-pix_y])
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

            # 鼠标回调函数
            # x, y 都是相对于窗口内的图像的位置
            def draw_circle(event, x, y, flags, param):
                # 判断事件是否为 Left Button Double Clicck
                if event == cv2.EVENT_LBUTTONDBLCLK or event == cv2.EVENT_LBUTTONDOWN:
                    in_cnt = cv2.pointPolygonTest(
                        np.array([self.pix_cnts]), (x, y), False)
                    # 大于0说明属于该轮廓
                    if in_cnt >= 0:
                        lng = round((left_up_x + x * self.scale_w) / 1000000.0, 6)
                        lat = round((left_up_y + y * self.scale_h) / 1000000.0, 6)
                        cv2.circle(img, (x, y), 5, (255, 0, 0), -1)
                if event == cv2.EVENT_RBUTTONDOWN:
                    in_cnt = cv2.pointPolygonTest(
                        np.array([self.pix_cnts]), (x, y), False)
                    # 大于0说明属于该轮廓
                    if in_cnt >= 0:
                        # print('像素', x, y)
                        lng = round((left_up_x + x * self.scale_w) / 1000000.0, 6)
                        lat = round((left_up_y + y * self.scale_h) / 1000000.0, 6)
                        # print('经纬度', lng, lat)
                        cv2.circle(img, (x, y), 5, (255, 0, 0), -1)

            cv2.namedWindow('img')
            # 设置鼠标事件回调
            cv2.setMouseCallback('img', draw_circle)
            while (True):
                cv2.imshow('img', img)
                if cv2.waitKey(1) == ord('q'):
                    break
            # cv2.waitKey(0)
            cv2.destroyAllWindows()

    # 发送串口数据
    def send_com_data(self):
        while True:
            if self.serial_obj is None:
                time.sleep(1)
                continue
            # 发送配置点
            if not ship_obj.b_send_path:
                time.sleep(config.com_send_sleep_time)
            else:
                # 转换为发送数据
                config_data_send = 'BB'
                self.logger.info({'ship_obj.config_ship_lng_lats_dict': ship_obj.config_ship_lng_lats_dict})
                for k, values in ship_obj.config_ship_lng_lats_dict.items():
                    config_data_send += '%03d' % k
                    for v in values[1:]:
                        config_data_send += ',' + str(v[0]) + ',' + str(v[1])
                    config_data_send += '#'
                # config_data_send += '$'
                print({'config_data_send': config_data_send})
                print({'config_ship_lng_lats_dict': ship_obj.config_ship_lng_lats_dict.get(1)})
                self.logger.info({'config_data_send': config_data_send})
                self.serial_obj.send_data(config_data_send)
                time.sleep(len(config_data_send) * 0.02)
                # 发送全部启动
                control_data_send = 'CC'
                self.logger.info({'ship_obj.config_ship_lng_lats_dict': ship_obj.ship_control_dict})
                for k, v in ship_obj.ship_control_dict.items():
                    control_data_send += '%03d,' % k + str(v) + '$'
                # control_data_send += '$'
                print({'control_data_send': control_data_send})
                self.logger.info({'control_data_send': control_data_send})
                self.serial_obj.send_data(control_data_send)
                self.b_send_path = False
            # 发送控制数据
            if not self.b_send_control:
                pass
            else:
                control_data_send = 'CC'
                self.logger.info({'ship_obj.config_ship_lng_lats_dict': ship_obj.ship_control_dict})
                for k, v in ship_obj.ship_control_dict.items():
                    control_data_send += '%03d,' % k + str(v) + '$'
                # control_data_send += '$'
                self.logger.info({'control_data_send': control_data_send})
                print({'control_data_send': control_data_send})
                self.serial_obj.send_data(control_data_send)
                self.b_send_control = False
            # 点击确定配置后发送第一个点坐标
            if self.b_send_first_point:
                # 转换为发送数据
                config_data_send = 'BB'
                self.logger.info({'ship_obj.config_ship_lng_lats_dict': ship_obj.config_ship_lng_lats_dict})
                for k, values in ship_obj.config_ship_lng_lats_dict.items():
                    config_data_send += '%03d' % k
                    config_data_send += ',' + str(values[0][0]) + ',' + str(values[0][1])
                    config_data_send += '#'
                # config_data_send += '$'
                print({'config_data_send': config_data_send})
                print({'config_ship_lng_lats_dict': ship_obj.config_ship_lng_lats_dict.get(1)})
                self.logger.info({'config_data_send': config_data_send})
                self.serial_obj.send_data(config_data_send)
                time.sleep(len(config_data_send) * 0.02)
                # 发送全部启动
                control_data_send = 'CC'
                self.logger.info({'ship_obj.config_ship_lng_lats_dict': ship_obj.ship_control_dict})
                for k, v in ship_obj.ship_control_dict.items():
                    control_data_send += '%03d,' % k + str(v) + '$'
                # control_data_send += '$'
                print({'control_data_send': control_data_send})
                self.logger.info({'control_data_send': control_data_send})
                self.serial_obj.send_data(control_data_send)
                self.b_send_first_point = False
            time.sleep(config.com_send_sleep_time)

    def get_com_data(self):
        # 读取函数会阻塞 必须使用线程
        # 记录上一次读取数据与读取时间
        last_lng_lat = None
        last_read_time = None
        while True:
            if not self.serial_obj:
                b_auto_detect = False
                if b_auto_detect:
                    # 检测串口模式
                    com_list = com_data.SerialData.print_used_com()
                    for port in com_list:
                        if port not in self.init_com_list:
                            self.serial_obj = com_data.SerialData(
                                port,
                                config.baud,
                                timeout=config.com_timeout,
                                logger=self.com_logger)
                            if not self.serial_obj.uart.isOpen():
                                self.serial_obj.uart.open()
                else:
                    if ship_obj.select_com:
                        self.serial_obj = com_data.SerialData(
                            ship_obj.select_com,
                            config.baud,
                            timeout=config.com_timeout,
                            logger=self.com_logger)
                        if not self.serial_obj.uart.isOpen():
                            self.serial_obj.uart.open()
                if config.port is not None:
                    port = config.port
                    self.serial_obj = com_data.SerialData(
                        port,
                        config.baud,
                        timeout=config.com_timeout,
                        logger=self.com_logger)
                    if not self.serial_obj.uart.isOpen():
                        self.serial_obj.uart.open()
            if not self.serial_obj:
                time.sleep(3)
                continue
            # 关闭串口
            if self.serial_obj and not ship_obj.select_com:
                self.serial_obj.close_Engine()
                self.serial_obj = None
                time.sleep(3)
                continue
            # 读取数据异常
            try:
                com_data_read = self.serial_obj.readline()
            except serial.SerialException:
                self.serial_obj.close_Engine()
                self.serial_obj = None
                ship_obj.select_com = ''
                time.sleep(3)
                self.logger.error('serial exception')
                continue
            # 解析串口发送过来的数据
            if com_data_read is None:
                continue
            print({'com_data_read': com_data_read})
            # 解析串口发送过来的数据
            try:
                if not com_data_read.startswith('AA'):
                    pass
                else:
                    self.logger.info({'get com data': com_data_read})
                    get_com_data_list = com_data_read.split(',')
                    ship_id = int(get_com_data_list[0][2:])
                    if ship_id not in self.online_ship_list:
                        self.online_ship_list.append(ship_id)
                    # 更新电量
                    self.ship_dump_energy_dict.update({ship_id: float(get_com_data_list[4])})
                    # 更新速度改为定位偏差 如果定位偏差小于5米开始计算
                    if float(get_com_data_list[3]) < 5.0:
                        if float(get_com_data_list[1]) < 1 or float(get_com_data_list[2]) < 1:
                            pass
                        else:
                            com_lng_lat = [float(get_com_data_list[1]), float(get_com_data_list[2])]
                            # 更新经纬度
                            self.ship_lng_lat_position_dict.update({ship_id: com_lng_lat})
                            # 经纬度转像素
                            com_pix = self.lng_lat_to_pix(com_lng_lat)
                            # 更新像素
                            self.ship_pix_position_dict.update({ship_id: com_pix})
                            if float(get_com_data_list[3]) < 5:
                                if last_lng_lat is None:
                                    last_lng_lat = copy.deepcopy(com_lng_lat)
                                    last_read_time = time.time()
                                else:
                                    # 计算当前行驶里程
                                    speed_distance = lng_lat_calculate.distanceFromCoordinate(com_lng_lat[0],
                                                                                              com_lng_lat[1],
                                                                                              last_lng_lat[0],
                                                                                              last_lng_lat[1])
                                    # 计算速度
                                    speed = round(speed_distance / (time.time() - last_read_time), 1)
                                    last_lng_lat = copy.deepcopy(com_lng_lat)
                                    last_read_time = time.time()
                                    self.ship_speed_dict.update({ship_id: speed})
                                    self.logger.info({'speed': speed * config.speed_scale})
                    # 更新朝向角度
                    self.ship_direction_dict.update({ship_id: float(get_com_data_list[5])})
                    # 更新到达点状态
                    current_mode = int(get_com_data_list[6])
                    current_target_index = int(get_com_data_list[7])
                    all_index = int(get_com_data_list[8])
                    all_len = len(ship_obj.config_ship_lng_lats_dict.get(ship_id))
                    if current_mode == 0:
                        point_status = self.config_ship_points_status.get(id)
                        if point_status:
                            if all_len == 0:
                                pass
                            else:
                                if current_target_index != 0:
                                    for i in range(current_target_index + 1):
                                        point_status[i] = 1
                            self.config_ship_points_status.update({ship_id: point_status})
                    # elif current_mode == 5:
                    #     if current_target_index == 1 and all_index == 0:
                    #         point_status[0] = 1
                    #     else:
                    #         for i in range(all_len):
                    #             point_status[i] = 1
            except Exception as e:
                self.logger.error({'com_data_read error': e})


class TcpClient:
    def __init__(self):
        self.target_host = config.tcp_server_ip  # 服务器端地址
        self.target_port = config.tcp_server_port  # 必须与服务器的端口号一致
        # self.connect_server()

    def connect_server(self):
        while True:
            try:
                self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.client.connect((self.target_host, self.target_port))
                break
            except Exception as e:
                time.sleep(2)
                print('connect_server error', e)
                continue

    def send(self, data):
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client.connect((self.target_host, self.target_port))
        if not data:
            return
        self.client.send(data.encode())
        response = self.client.recv(1024)
        print(response)
        self.client.close()

    def get(self):
        while True:
            try:
                print('self.client', self.client)
                response = self.client.recv(1024)
            except OSError:
                self.connect_server()
                response = self.client.recv(1024)
            # 如果没有client错误
            except AttributeError:
                time.sleep(1)
                continue
            str_response = str(response)[2:-1]
            if len(str_response) > 0:
                logger.info({'response': str_response})
            # 发送了开始
            print('str_response', str_response)
            if str_response == 'as':
                self.send('asc')
                ship_obj.b_send_path = True
                for i in ship_obj.online_ship_list:
                    ship_obj.ship_control_dict.update({int(i): 1})
                print('send asc')
            # 发送了结束
            elif str_response == 'cs':
                self.send('csc')
                print('send csc')
                ship_obj.b_send_control = True
                for i in ship_obj.online_ship_list:
                    ship_obj.ship_control_dict.update({int(i): 0})
            else:
                self.send('error')


if __name__ == '__main__':
    ship_obj = Ship()
    tcp_obj = TcpClient()
    # connect_server_thread = threading.Thread(target=tcp_obj.connect_server)
    init_cnts_lng_lat_to_pix = threading.Thread(target=ship_obj.init_cnts_lng_lat_to_pix, args=(False,))
    get_com_thread = threading.Thread(target=ship_obj.get_com_data)
    send_com_thread = threading.Thread(target=ship_obj.send_com_data)
    tcp_get_thread = threading.Thread(target=tcp_obj.get)

    # init_cnts_lng_lat_to_pix.setDaemon(True)
    # get_com_thread.setDaemon(True)
    # send_com_thread.setDaemon(True)
    # connect_server_thread.start()
    init_cnts_lng_lat_to_pix.start()
    get_com_thread.start()
    send_com_thread.start()
    # tcp_get_thread.start()

    # init_cnts_lng_lat_to_pix.join()
    # get_com_thread.join()
    # send_com_thread.join()
    # run_flask()
    ship_obj.run_flask(debug=False)
