import com_data
from utils import log as log1
import config
import socket
from utils import lng_lat_calculate
import cv2
import numpy as np
from flask import Flask, request
from flask import render_template
from flask_cors import CORS
import os
import json
import time
import threading
import random
import logging
import copy
import sys
import serial
import math

print('path: ', os.path.dirname(os.path.abspath(__file__)))
lng_lats_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lng_lats.txt')
lng_lats_path_json = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lng_lats.json')
ship_paths_dir = os.path.dirname(os.path.abspath(__file__))


# 获取资源路径
def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


app = Flask(__name__, template_folder=resource_path('templates'), static_folder=resource_path('statics'))
log = logging.getLogger('werkzeug')
log.disabled = True
# CORS(app, supports_credentials=True)
CORS(app, resources=r'/*')


@app.route('/')
def index():
    return render_template('map319.html')


logger = log1.LogHandler('main')


# 湖轮廓像素位置
@app.route('/pool_cnts', methods=['GET', 'POST'])
def pool_cnts():
    # 失败返回提示信息
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
        return return_json


# 获取在线船列表
@app.route('/online_ship', methods=['GET', 'POST'])
def online_ship():
    if config.test:
        random_data = random.randint(1, 50)
        points_status = {}
        for i in ship_obj.config_ship_lng_lats_dict.keys():
            point_status = [0] * len(ship_obj.config_ship_lng_lats_dict.get(i))
            if random_data > 25:
                point_status[0] = 1
            points_status.update({i: point_status})
        ship_obj.online_ship_list = [1, 2, 8, 10]
        lng_lats = [[114.520994, 30.508157],
                    [114.520147, 30.508237],
                    [114.521206, 30.508574],
                    [114.521107, 30.508261], ]
        pixs = []
        for i in lng_lats:
            pixs.append(ship_obj.lng_lat_to_pix(i))
        return_data = {
            # 船号
            "ids": ship_obj.online_ship_list,
            # 船像素信息数组
            # "pix_postion": [[383 + random_data, 199 - random_data], [132 + random_data, 406 - random_data],
            #                 [52 - random_data, 206 + random_data], [0 + random_data, 169 + random_data]],
            "pix_postion": pixs,
            # 船是否配置行驶点 1为已经配置  0位还未配置
            "config_path": [1 if i in ship_obj.config_ship_pix_points_dict else 0 for i in [1, 2, 8, 10]],
            # 船剩余电量0-100整数
            "dump_energy": [90, 37, 80, 60],
            # 船速度 单位：m/s  浮点数
            "speed": [3.5 + random_data / 5.0, 2.0, 1.0, 5.0],
            "direction": [30 + random_data, 60 + random_data, 100 + random_data, 180 + random_data],
            "points_status": points_status,
            "home_pix_lng_lat": ship_obj.home_pix_lng_lat,
            "distance": [100, 10, 20, 35],
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
            "points_status": ship_obj.config_ship_points_status,
            "home_pix_lng_lat": ship_obj.home_pix_lng_lat,
            "distance": [ship_obj.ship_home_distance_dict.get(i) for i in ship_obj.online_ship_list],
        }
        if len(return_data["pix_postion"]) > 0 and return_data["pix_postion"][0] is None:
            return_data["pix_postion"] = [[0, 0]]
        if len(return_data["speed"]) > 0 and return_data["speed"][0] is None:
            return_data["speed"] = [0]
        return json.dumps(return_data)


# 确定按钮  发送一条船配置路径
@app.route('/ship_path', methods=['GET', 'POST'])
def ship_path():
    data = json.loads(request.data)
    ship_obj.start_search = 0
    ship_obj.logger.info({'ship_path': data})
    if not ship_obj.pix_cnts:
        return '还没有湖，别点'
    if not data.get('id'):
        ship_obj.logger.error({"配置轨迹没有船号:": data})
        return "配置轨迹没有船号"
    ship_id = int(data.get('id'))

    if not data.get('data') or len(data.get('data')) < 1:
        return 'error'
    if data['data'][0][0].endswith('px'):
        click_pix_points = [[int(i[0][:-2]), int(i[1][:-2])] for i in data['data']]
    else:
        click_pix_points = [[int(i[0]), int(i[1])] for i in data['data']]
    click_lng_lats = []
    click_inpool_pix_point = []
    # 最多存储10个点
    if len(click_pix_points) > 10:
        click_pix_points = click_pix_points[:10]
    for point in click_pix_points:
        in_cnt = cv2.pointPolygonTest(np.array(ship_obj.pix_cnts), (point[0], point[1]), False)
        if in_cnt >= 0:
            click_inpool_pix_point.append(point)
            click_lng_lat = ship_obj.pix_to_lng_lat(point)
            ship_obj.logger.info({'click_lng_lat': click_lng_lat})
            click_lng_lats.append(click_lng_lat)
    if len(click_lng_lats) < 1:
        return "全部点在湖外面"
    else:
        ship_obj.b_send_first_point = True
        ship_obj.ship_control_dict.update({ship_id: 1})
        # 路径点像素位置
        ship_obj.config_ship_pix_points_dict.update({ship_id: click_inpool_pix_point})
        # 路径点经纬度位置
        ship_obj.config_ship_lng_lats_dict.update({ship_id: click_lng_lats})
        # 路径点到达状态
        ship_obj.config_ship_points_status.update({ship_id: [0] * len(click_lng_lats)})
        ship_obj.target_mode = 0
        return 'ok'


# 获取所有配置路径
@app.route('/get_all_config', methods=['GET', 'POST'])
def get_all_config():
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
    return json.dumps(return_data)


# 全部启动
@app.route('/send_path', methods=['GET', 'POST'])
def send_path():
    ship_obj.logger.info('全部启动')
    ship_obj.b_send_path = True
    # 设置所有在线船只为需要启动
    for i in ship_obj.online_ship_list:
        ship_obj.ship_control_dict.update({int(i): 1})
    return 'send_path'


# 控制船启动
@app.route('/ship_start', methods=['GET', 'POST'])
def ship_start():
    ship_obj.b_send_control = True
    data = json.loads(request.data)
    ship_obj.logger.info({'ship_start': data})
    if data.get('id'):
        ship_id = int(data.get('id'))
        # 设置指定船只为需要启动
        ship_obj.ship_control_dict.update({ship_id: 1})
        return '启动'
    else:
        return '没有id'


# 控制船停止
@app.route('/ship_stop', methods=['GET', 'POST'])
def ship_stop():
    ship_obj.start_search = 1
    ship_obj.b_send_control = True
    ship_obj.b_send_path = False  # 取消时取消发送数据
    ship_obj.b_send_first_point = False  # 取消时取消发送数据
    data = json.loads(request.data)
    ship_obj.logger.info({'ship_stop': data})
    if data.get('id'):
        ship_id = int(data.get('id'))
        # 设置指定船只为需要启动
        ship_obj.ship_control_dict.update({ship_id: 0})
        return '停止'
    else:
        return '没有id'


# 发送串口
@app.route('/get_coms', methods=['GET', 'POST'])
def get_coms():
    com_list = com_data.SerialData.print_used_com()
    return json.dumps(com_list)


# 接受串口打开
@app.route('/open_com', methods=['GET', 'POST'])
def open_com():
    data = str(json.loads(request.data))
    ship_obj.logger.info({"打开串口": data})
    if data.startswith('COM'):
        ship_obj.select_com = str(data)
    return 'open_com'


# 接受串口关闭
@app.route('/close_com', methods=['GET', 'POST'])
def close_com():
    ship_obj.logger.info("关闭串口")
    ship_obj.select_com = ''
    return 'close_com'


# 保存当前船只设置轨迹到文件夹中
@app.route('/save_ship_path', methods=['GET', 'POST'])
def save_ship_path():
    # 船号
    data = json.loads(request.data)
    ship_obj.logger.info({'保存路径': data})
    if data.get('id'):
        ship_id = int(data.get('id'))
        if ship_obj.config_ship_lng_lats_dict.get(ship_id):
            # 保存当前轨迹到文件中
            ship_paths_path = os.path.join(ship_paths_dir, '%d_paths.json' % ship_id)
            if os.path.exists(ship_paths_path):
                os.remove(ship_paths_path)
            with open(ship_paths_path, 'w') as f:
                json.dump(ship_obj.config_ship_lng_lats_dict.get(ship_id), f)
            return 'save_ship_path'
        else:
            return "ok"
    else:
        return 'error'


# 加载对应船只保存轨迹
@app.route('/load_ship_path', methods=['GET', 'POST'])
def load_ship_path():
    # 船号
    data = json.loads(request.data)
    ship_obj.logger.info({'加载路径': data})
    if data.get('id'):
        ship_id = int(data.get('id'))
        # 加载轨迹到文件中
        ship_paths_path = os.path.join(ship_paths_dir, '%d_paths.json' % ship_id)
        if os.path.exists(ship_paths_path):
            with open(ship_paths_path, 'r') as f:
                ship_lng_lats = json.load(f)
                click_inpool_pix_point = []
                for point in ship_lng_lats:
                    click_pix = ship_obj.lng_lat_to_pix(point, b_gps=True)
                    click_inpool_pix_point.append(click_pix)
                ship_obj.b_send_first_point = True
                # 路径点像素位置
                ship_obj.config_ship_pix_points_dict.update({ship_id: click_inpool_pix_point})
                # 路径点经纬度位置
                ship_obj.config_ship_lng_lats_dict.update({ship_id: ship_lng_lats})
                # 路径点到达状态
                ship_obj.config_ship_points_status.update({ship_id: [0] * len(click_inpool_pix_point)})
                ship_obj.target_mode = 0
                return 'ok'
        else:
            return 'error'
    else:
        return 'error'


# 设置当前点位为边界轮廓点
@app.route('/set_boundary', methods=['GET', 'POST'])
def set_boundary():
    # 船号
    data = json.loads(request.data)
    if data.get('id'):
        ship_id = int(data.get('id'))
        if ship_obj.ship_info_dict.get(ship_id) and ship_obj.ship_info_dict.get(ship_id).get('lng_lat'):
            ship_obj.logger.info({'当前经纬度添加到txt文件中': ship_obj.ship_info_dict.get(ship_id).get('lng_lat')})
            if os.path.exists(lng_lats_path_json):
                try:
                    with open(lng_lats_path_json, 'r') as f:
                        lng_lats_path_data = json.load(f)
                    # 读取配置
                    if lng_lats_path_data.get('lng_lats') is not None:
                        lng_lats_path_data.get('lng_lats').append(ship_obj.ship_info_dict.get(ship_id).get('lng_lat'))
                    return '设置成功'
                except Exception as e:
                    ship_obj.logger.error({'经纬度添加到txt文件中error': e})
                    os.remove(lng_lats_path_json)
                    return '本地出错'
            else:
                return 'set_boundary'
        else:
            return '没有船经纬度'
    else:
        return '没有id'


# 设置返航点
@app.route('/set_home_point', methods=['GET', 'POST'])
def set_home_point():
    # 船号
    data = json.loads(request.data)
    ship_obj.logger.info({'设置返航点': data})
    if data.get('lng_lat'):
        # 经纬度转像素
        pix_click = [int(data.get('lng_lat')[0][0].split('px')[0]), int(data.get('lng_lat')[0][1].split('px')[0])]
        click_lng_lat = ship_obj.pix_to_lng_lat(pix_click)
        ship_obj.home_lng_lat = click_lng_lat
        ship_obj.home_pix_lng_lat = pix_click
        return "设置返航点"
    else:
        return '没有点数据'


# 返航
@app.route('/back_home_point', methods=['GET', 'POST'])
def back_home_point():
    # 将返航点发给单片机
    data = json.loads(request.data)
    ship_obj.logger.info({'返航：': data})
    if data.get('id'):
        ship_id = int(data.get('id'))
        if ship_obj.home_lng_lat:
            home_lng_lat = ship_obj.home_lng_lat
            ship_obj.b_send_first_point = True
            # 路径点像素位置
            home_lng_lat_pix = ship_obj.lng_lat_to_pix(home_lng_lat)
            ship_obj.config_ship_pix_points_dict.update({ship_id: [home_lng_lat_pix]})
            # 路径点经纬度位置
            ship_obj.config_ship_lng_lats_dict.update({ship_id: [home_lng_lat]})
            # 路径点到达状态
            ship_obj.config_ship_points_status.update({ship_id: [0] * 1})
            ship_obj.target_mode = 0
            return '返航'
        else:
            return '没有船经纬度'
    else:
        return '没有id'


# 获取船只列表
@app.route('/get_ship_list', methods=['GET', 'POST'])
def get_ship_list():
    return_data = {"ids": ship_obj.online_ship_list}
    return json.dumps(return_data)


class Ship:
    def __init__(self, logger=None):
        if logger:
            self.logger = logger
        else:
            self.logger = log1.LogHandler('ship',level=20)
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
        # 船距离起始点距离
        self.ship_home_distance_dict = {}
        # 船剩余电量
        self.ship_dump_energy_dict = {}
        # 船速度
        self.ship_speed_dict = {}
        # 船朝向
        self.ship_direction_dict = {}
        self.b_send_path = False  # 发送所有路径到船 并启动
        self.b_send_control = False
        # 采集轮廓点经纬度
        self.lng_lats_list = []
        # 记录当前存在的串口
        self.init_com_list = com_data.SerialData.print_used_com()
        # 串口对象
        self.serial_obj = None
        # 用户点击传过来的串口
        self.select_com = ''
        # 点击确定后发送第一个点
        self.b_send_first_point = False
        self.receive_info = []  # 存储接收到下位机的确认数据
        self.is_auto = [0] * 21  # 存储所有船当前是否在自动行驶 0:不在自动中 1:在自动中
        self.target_mode = 0  # 1:第一个点     2:后续多个点   0 都不是
        self.init_lng_lat = None  # 记录初始经纬度用于计算距离
        self.left_up_x = 0
        self.left_up_y = 0
        self.scale_w = 1
        self.scale_h = 1
        self.ship_info_dict = {}
        self.home_lng_lat = []
        self.home_pix_lng_lat = []
        self.start_search = 1  # 开始轮训查找船
        self.pix_2_meter = 0.12859689044 * math.pow(2, 19 - config.zoom)
        """
        {1:{'ship_control_dict':[]}
        }
        """

    # 必须放在主线程中
    @staticmethod
    def run_flask(debug=True):
        app.run(host=config.tcp_server_ip, port=config.web_port, debug=debug)

    # 经纬度转像素
    # def lng_lat_to_pix(self, lng_lat, b_gps=False):
    #     """
    #     :param lng_lat: 经纬度
    #     :return:
    #     """
    #     int_lng_lat = [int(lng_lat[0] * 1000000), int(lng_lat[1] * 1000000)]
    #     int_lng_lats_offset = [int_lng_lat[0] - self.left_up_x, int_lng_lat[1] - self.left_up_y]
    #     # int_lng_lats_pix = [int(int_lng_lats_offset[0] / self.scale_w), int(int_lng_lats_offset[1] / self.scale_h)]
    #     if not b_gps:
    #         int_lng_lats_pix = [int(int_lng_lats_offset[0] / self.scale_w),
    #                             int(int_lng_lats_offset[1] / self.scale_h)]
    #     else:
    #         int_lng_lats_pix = [int(int_lng_lats_offset[0] / self.scale_w),
    #                             config.pix_h - int(int_lng_lats_offset[1] / self.scale_h)]
    #     # int_lng_lats_pix = [int(int_lng_lats_offset[0] / self.scale_w),
    #     #                     int(int_lng_lats_offset[1] / self.scale_h)]
    #     return int_lng_lats_pix

    # 像素转经纬度
    # def pix_to_lng_lat(self, pix):
    #     """
    #     :param pix:像素位置 先w 后h
    #     :return: 经纬度
    #     """
    #     lng = round((self.left_up_x + pix[0] * self.scale_w) / 1000000.0, 6)
    #     lat = round((self.left_up_y + (config.pix_h - pix[1]) * self.scale_h) / 1000000.0, 6)
    #     return [lng, lat]

    def lng_lat_to_pix(self, lng_lat, b_gps=False):
        """
        :param lng_lat: 经纬度
        :return:
        """
        # lng_lat_gps = lng_lat_calculate.gps_gaode_to_gps(config.src_gps, config.src_gaode, config.lng_lat)
        distance = lng_lat_calculate.distanceFromCoordinate(config.lng_lat_gps[0], config.lng_lat_gps[1], lng_lat[0],
                                                            lng_lat[1])
        angle = lng_lat_calculate.angleFromCoordinate(config.lng_lat_gps[0], config.lng_lat_gps[1], lng_lat[0],
                                                      lng_lat[1])
        if angle < 90:
            x_distance = -1 * distance * math.sin(math.radians(angle))
            y_distance = -1 * distance * math.cos(math.radians(angle))
        elif angle < 180:
            x_distance = -1 * distance * math.cos(math.radians(angle - 90))
            y_distance = 1 * distance * math.sin(math.radians(angle - 90))
        elif angle < 270:
            x_distance = 1 * distance * math.sin(math.radians(angle - 180))
            y_distance = 1 * distance * math.cos(math.radians(angle - 180))
        else:
            x_distance = 1 * distance * math.cos(math.radians(angle - 270))
            y_distance = -1 * distance * math.sin(math.radians(angle - 270))
        # print('################', lng_lat, config.lng_lat_gps, x_distance, y_distance, self.pix_2_meter)
        int_lng_lats_pix = [int(x_distance / self.pix_2_meter + config.width / 2),
                            int(y_distance / self.pix_2_meter + config.height / 2)]
        return int_lng_lats_pix

    def pix_to_lng_lat(self, pix):
        x_distance = (pix[0] - config.width / 2) * self.pix_2_meter
        y_distance = (pix[1] - config.height / 2) * self.pix_2_meter
        if x_distance >= 0 and y_distance >= 0:
            theta = 180 + math.degrees(math.fabs(math.atan2(x_distance, y_distance)))
        elif x_distance >= 0 and y_distance < 0:
            theta = 270 + math.degrees(math.fabs(math.atan2(y_distance, x_distance)))
        elif x_distance < 0 and y_distance >= 0:
            theta = 90 + math.degrees(math.fabs(math.atan2(y_distance, x_distance)))
        else:
            theta = math.degrees(math.fabs(math.atan2(x_distance, y_distance)))
        # print('x_distance,y_distance,theta', x_distance, y_distance, theta, (x_distance ** 2 + y_distance ** 2) ** 0.5)
        target_gps = lng_lat_calculate.one_point_diatance_to_end(config.lng_lat_gps[0], config.lng_lat_gps[1], theta,
                                                                 (x_distance ** 2 + y_distance ** 2) ** 0.5)
        target_gaode = lng_lat_calculate.one_point_diatance_to_end(config.lng_lat[0], config.lng_lat[1], theta,
                                                                   (x_distance ** 2 + y_distance ** 2) ** 0.5)
        # target_gps = lng_lat_calculate.gps_gaode_to_gps(config.src_gps, config.src_gaode, target_gaode)
        # print('target_gps target_gaode', target_gps, target_gaode)
        return target_gps

    def init_cnts_lng_lat_to_pix(self, b_show=False):
        """
        1 是否有图片
        2 是否有经纬度对应高德经纬度
        :param b_show:
        :return:
        """
        while not os.path.exists(config.save_img_path):
            lng_lat_calculate.download_image(lng_lat=config.lng_lat, zoom=config.zoom,
                                             save_img_path=config.save_img_path)
        baund_width = 3
        self.pix_cnts = [[baund_width, baund_width],
                         [config.width - baund_width, baund_width],
                         [config.width - baund_width, config.height - baund_width],
                         [baund_width, config.height - baund_width]]
        # if not os.path.exists(config.gps_gaode_path):
        #     with open(config.gps_gaode_path,'w') as f:
        #         json.du

    # def init_cnts_lng_lat_to_pix(self, b_show=False):
    #     b_txt = False  # 使用txt边界地址json
    #     b_json = False  # 使用json边界地址
    #     while True:
    #         if os.path.exists(lng_lats_path):
    #             b_txt = True
    #             break
    #         elif os.path.exists(lng_lats_path_json):
    #             b_json = True
    #             break
    #         else:
    #             time.sleep(1)
    #     if b_txt:
    #         try:
    #             with open(lng_lats_path, 'r') as f:
    #                 temp_list = f.readlines()
    #                 for i in temp_list:
    #                     i = i.strip()
    #                     self.lng_lats_list.append(
    #                         [round(float(i.split(',')[0]), 6), round(float(i.split(',')[1]), 6)])
    #         except Exception as e:
    #             self.logger.error({'lng_lats.txt 格式错误': e})
    #             return
    #     if b_json:
    #         try:
    #             with open(lng_lats_path_json, 'r') as f:
    #                 json_data = json.load(f)
    #                 self.lng_lats_list = json_data.get('lng_lats')
    #         except Exception as e:
    #             self.logger.error({'lng_lats.txt 格式错误': e})
    #             return
    #     int_lng_lats_list = [[int(i[0] * 1000000), int(i[1] * 1000000)]
    #                          for i in self.lng_lats_list]
    #     (left_up_x, left_up_y, w, h) = cv2.boundingRect(np.array(int_lng_lats_list))
    #     self.left_up_x = left_up_x
    #     self.left_up_y = left_up_y
    #     self.logger.info({'(x, y, w, h) ': (left_up_x, left_up_y, w, h)})
    #     # 像素到单位缩放 等比拉伸
    #     if w >= h:
    #         self.scale_w = float(w) / config.pix_w
    #         self.scale_h = float(w) / config.pix_w
    #     else:
    #         self.scale_w = float(h) / config.pix_w
    #         self.scale_h = float(h) / config.pix_w
    #     # 经纬度转像素
    #     # self.pix_cnts = [self.lng_lat_to_pix(i) for i in self.lng_lats_list]
    #     for i in self.lng_lats_list:
    #         pix_x, pix_y = self.lng_lat_to_pix(i)
    #         self.pix_cnts.append([pix_x, config.pix_h - pix_y])
    #     self.logger.info({'self.pix_cnts': self.pix_cnts})
    #     if b_show:
    #         img = np.zeros((config.pix_h, config.pix_w, 3), dtype=np.uint8)
    #         cv2.circle(img, (int(config.pix_w / 2),
    #                          int(config.pix_h / 2)), 5, (255, 0, 255), -1)
    #         cv2.drawContours(
    #             img,
    #             np.array(
    #                 [self.pix_cnts]),
    #             contourIdx=-1,
    #             color=(255, 0, 0))
    #
    #         # 鼠标回调函数
    #         # x, y 都是相对于窗口内的图像的位置
    #         def draw_circle(event, x, y, flags, param):
    #             # 判断事件是否为 Left Button Double Clicck
    #             if event == cv2.EVENT_LBUTTONDBLCLK or event == cv2.EVENT_LBUTTONDOWN:
    #                 in_cnt = cv2.pointPolygonTest(
    #                     np.array([self.pix_cnts]), (x, y), False)
    #                 # 大于0说明属于该轮廓
    #                 if in_cnt >= 0:
    #                     lng = round((left_up_x + x * self.scale_w) / 1000000.0, 6)
    #                     lat = round((left_up_y + y * self.scale_h) / 1000000.0, 6)
    #                     cv2.circle(img, (x, y), 5, (255, 0, 0), -1)
    #             if event == cv2.EVENT_RBUTTONDOWN:
    #                 in_cnt = cv2.pointPolygonTest(
    #                     np.array([self.pix_cnts]), (x, y), False)
    #                 # 大于0说明属于该轮廓
    #                 if in_cnt >= 0:
    #                     # print('像素', x, y)
    #                     lng = round((left_up_x + x * self.scale_w) / 1000000.0, 6)
    #                     lat = round((left_up_y + y * self.scale_h) / 1000000.0, 6)
    #                     # print('经纬度', lng, lat)
    #                     cv2.circle(img, (x, y), 5, (255, 0, 0), -1)
    #
    #         cv2.namedWindow('img')
    #         # 设置鼠标事件回调
    #         cv2.setMouseCallback('img', draw_circle)
    #         while (True):
    #             cv2.imshow('img', img)
    #             if cv2.waitKey(1) == ord('q'):
    #                 break
    #         # cv2.waitKey(0)
    #         cv2.destroyAllWindows()

    # 发送串口数据
    def send_com_data(self):
        ship_status = [0] * 20
        index_send = 0  # 当前发送数据索引
        sum_send = 0  # 总点数
        choose_ship_time = time.time()
        while True:
            if self.serial_obj is None:
                time.sleep(1)
                continue
            if self.start_search:
                loop_list = [i for i in range(1, 21)]
            else:
                loop_list = self.online_ship_list
            for ship_id in loop_list:
                if self.b_send_path or self.b_send_control or self.b_send_first_point:
                    # 发送全部配置点 并启动
                    if self.b_send_path:
                        # for k, values in ship_obj.config_ship_lng_lats_dict.items():
                        #     sum_send = len(values) - 1
                        if ship_obj.config_ship_lng_lats_dict.get(ship_id) is None:
                            continue
                        sum_send = len(ship_obj.config_ship_lng_lats_dict.get(ship_id)) - 1
                        if sum_send <= 0:
                            self.b_send_path = False
                        # 检查32是否收到点消息
                        if len(self.receive_info) != 3 or self.receive_info[
                            0] != index_send or index_send < sum_send - 1:  # 判断是否所有点均已发完
                            # 转换为发送数据
                            config_data_send = 'BB'
                            self.logger.info({'ship_obj.config_ship_lng_lats_dict': ship_obj.config_ship_lng_lats_dict})
                            self.logger.debug({'self.receive_info': self.receive_info})
                            for k, values in ship_obj.config_ship_lng_lats_dict.items():
                                config_data_send += '%03d' % k
                                config_data_send += ',' + str(index_send) + ',' + str(sum_send) + ',' + str(
                                    values[index_send + 1][0]) + ',' + str(values[index_send + 1][1])
                                config_data_send += '#'
                                break
                            self.logger.debug({'多点发送数据:': config_data_send})
                            self.send_lora_data(config_data_send)
                            time.sleep(len(config_data_send) * 0.02)
                            # if len(self.receive_info) == 3 and self.receive_info[0] == index_send and self.receive_info[0] < sum_send-1:
                            #     index_send += 1  # 确认一点收到后发送下一点
                        if len(self.receive_info) == 3 and self.receive_info[
                            0] == index_send and index_send < sum_send - 1:
                            index_send += 1  # 确认一点收到后发送下一点
                        if len(self.receive_info) == 3 and self.receive_info[
                            0] == index_send and index_send == sum_send - 1:
                            # 检查32是否收到启动消息
                            if self.is_auto[ship_id] != 1:
                                # if len(self.receive_info) != 3 and self.receive_info[2] != 1:
                                # 发送全部启动
                                control_data_send = 'CC'
                                self.logger.info({'ship_obj.config_ship_lng_lats_dict': ship_obj.ship_control_dict})
                                for k, v in ship_obj.ship_control_dict.items():
                                    control_data_send += '%03d,' % k + str(v) + '$'
                                # control_data_send += '$'
                                self.logger.info({'启动停止数据:': control_data_send})
                                self.send_lora_data(control_data_send)
                            else:
                                self.target_mode = 2
                                self.receive_info = []
                                self.b_send_path = False
                                index_send = 0
                    # 发送控制数据
                    if self.b_send_control:
                        # 判断是否真的启动和停止
                        control_data_send = 'CC'
                        self.logger.info({'ship_obj.config_ship_lng_lats_dict': ship_obj.ship_control_dict})
                        for k, v in ship_obj.ship_control_dict.items():
                            control_data_send += '%03d,' % k + str(v) + '$'
                            ship_status[k] = v
                            # control_data_send += '$'
                            self.logger.info({'启停命令:': control_data_send})
                            self.send_lora_data(control_data_send)
                        if self.is_auto[ship_id] == ship_status[ship_id]:
                            self.b_send_control = False
                            self.target_mode = 0
                    # 点击确定配置后发送第一个点坐标
                    if self.b_send_first_point:
                        # 检查32是否收到点消息
                        # if len(self.receive_info)==0:
                        self.logger.info({'32反馈确认数据:': self.receive_info})
                        if len(self.receive_info) != 3 or self.receive_info[0] != 0 or self.receive_info[1] != 1:
                            # 转换为发送数据
                            config_data_send = 'BB'
                            self.logger.info({'ship_obj.config_ship_lng_lats_dict': ship_obj.config_ship_lng_lats_dict})
                            for k, values in ship_obj.config_ship_lng_lats_dict.items():
                                config_data_send += '%03d' % k
                                config_data_send += ',0,1'
                                config_data_send += ',' + str(values[0][0]) + ',' + str(values[0][1])
                                config_data_send += '#'
                            # config_data_send += '$'
                            self.logger.info({'单点': config_data_send})
                            self.send_lora_data(config_data_send)
                            time.sleep(len(config_data_send) * 0.02)
                        # 检查32是否收到启动消息
                        else:
                            if self.is_auto[ship_id] != 1:
                                # 发送启动
                                control_data_send = 'CC'
                                # self.logger.info({'ship_obj.config_ship_lng_lats_dict': ship_obj.ship_control_dict})
                                for k, v in ship_obj.ship_control_dict.items():
                                    control_data_send += '%03d,' % k + str(v) + '$'
                                self.logger.info({'单点启动': control_data_send})
                                self.send_lora_data(control_data_send)
                            else:
                                self.target_mode = 1
                                self.b_send_first_point = False
                                self.receive_info = []
                # 间隔轮训所有船只信息
                choose_ship_data = "H%dZ" % (ship_id)
                self.logger.info({'发送数据': choose_ship_data})
                self.send_lora_data(choose_ship_data)
                time.sleep(config.com_send_sleep_time)

    def send_lora_data(self, data):
        if self.serial_obj is None:
            return
        try:
            self.serial_obj.send_data(data)
        except Exception as e:
            ship_obj.logger.error({"串口发送数据报错": e})
            self.serial_obj.close_Engine()
            self.serial_obj = None

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
                                logger=self.logger)
                            ship_obj.logger.info('com open', self.serial_obj.uart.is_open)
                else:
                    if ship_obj.select_com:
                        self.serial_obj = com_data.SerialData(
                            ship_obj.select_com,
                            config.baud,
                            timeout=config.com_timeout,
                            logger=self.logger)
                        ship_obj.logger.info('com open', self.serial_obj.uart.is_open)
            if not self.serial_obj:
                time.sleep(0.1)
                continue
            # 关闭串口
            if self.serial_obj and not ship_obj.select_com:
                self.serial_obj.close_Engine()
                self.serial_obj = None
                time.sleep(0.1)
                continue
            # 读取数据异常 关闭串口后重连
            try:
                com_data_read = self.serial_obj.readline()
            except serial.SerialException:
                self.serial_obj.close_Engine()
                self.serial_obj = None
                time.sleep(1)
                self.logger.error('serial exception')
                continue
            # 解析串口发送过来的数据
            if com_data_read is None:
                continue
            self.logger.info({'com_data_read': com_data_read})
            # 解析串口发送过来的数据
            try:
                if com_data_read.startswith('EE'):
                    get_com_data_list = com_data_read.split(',')
                    ship_id = int(get_com_data_list[0][2:])
                    if ship_id not in self.online_ship_list:
                        self.online_ship_list.append(ship_id)
                    # 接收到索引信息
                    if len(get_com_data_list) == 4:
                        self.receive_info = [int(get_com_data_list[1]), int(get_com_data_list[2]),
                                             int(get_com_data_list[3][0])]
                elif com_data_read.startswith('AA'):
                    # self.logger.info({'get com data': com_data_read})
                    get_com_data_list = com_data_read.split(',')
                    if len(get_com_data_list) < 7:
                        continue
                    ship_id = int(get_com_data_list[0][2:])
                    if ship_id not in self.online_ship_list:
                        self.online_ship_list.append(ship_id)
                    # 更新电量
                    self.ship_dump_energy_dict.update({ship_id: float(get_com_data_list[3])})
                    if float(get_com_data_list[1]) < 1 or float(get_com_data_list[2]) < 1:
                        pass
                    else:
                        # 单片机发送过来经纬度为114132312的整数样式将其转为度格式
                        com_lng_lat = [float(get_com_data_list[1]) / 1000000.0,
                                       float(get_com_data_list[2]) / 1000000.0]
                        # 更新经纬度
                        self.ship_lng_lat_position_dict.update({ship_id: com_lng_lat})
                        # 经纬度转像素
                        com_pix = self.lng_lat_to_pix(com_lng_lat, b_gps=True)
                        # 更新像素
                        self.ship_pix_position_dict.update({ship_id: com_pix})
                        self.ship_info_dict.update({ship_id: {"lng_lat": com_lng_lat, "pix_lng_lat": com_pix}})
                        if self.init_lng_lat is None:
                            self.init_lng_lat = com_lng_lat
                        if self.home_lng_lat is None:
                            self.home_lng_lat = com_lng_lat
                            self.home_pix_lng_lat = com_pix
                        if last_lng_lat is None:
                            last_lng_lat = copy.deepcopy(com_lng_lat)
                            last_read_time = time.time()
                        else:
                            # 计算当前行驶里程
                            speed_distance = lng_lat_calculate.distanceFromCoordinate(com_lng_lat[0],
                                                                                      com_lng_lat[1],
                                                                                      last_lng_lat[0],
                                                                                      last_lng_lat[1])
                            home_distance = 0
                            if self.init_lng_lat is not None:
                                home_distance = lng_lat_calculate.distanceFromCoordinate(com_lng_lat[0],
                                                                                         com_lng_lat[1],
                                                                                         self.init_lng_lat[0],
                                                                                         self.init_lng_lat[1])
                                home_distance *= 1.2
                                home_distance = round(home_distance, 1)

                            # 计算速度
                            speed = round(config.speed_scale * speed_distance / (time.time() - last_read_time), 1)
                            last_lng_lat = copy.deepcopy(com_lng_lat)
                            last_read_time = time.time()
                            self.ship_speed_dict.update({ship_id: speed})
                            self.logger.info({'speed': speed})
                            self.ship_home_distance_dict.update({ship_id: home_distance})  # 离出发距离暂时占用电量位置
                    # 更新朝向角度
                    self.ship_direction_dict.update({ship_id: float(get_com_data_list[4])})
                    # 当前已经到达点数量0都没到  1到了一个 2到了两个
                    current_target_index = int(get_com_data_list[5])
                    # 是否是自动状态
                    self.is_auto[ship_id] = int(get_com_data_list[6][0])
                    # 更新到达点状态
                    if ship_obj.config_ship_lng_lats_dict.get(ship_id):
                        # 获取全部点
                        all_len = len(ship_obj.config_ship_lng_lats_dict.get(ship_id))
                        if self.target_mode == 1:
                            point_status = self.config_ship_points_status.get(ship_id)
                            if point_status:
                                if all_len == 0:
                                    pass
                                else:
                                    if current_target_index != 0:
                                        point_status[0] = 1
                                self.config_ship_points_status.update({ship_id: point_status})
                        elif self.target_mode == 2:
                            # 获取全部点
                            if ship_obj.config_ship_lng_lats_dict.get(ship_id):
                                all_len = len(ship_obj.config_ship_lng_lats_dict.get(ship_id))
                            else:
                                all_len = 0
                            if self.target_mode == 2:
                                point_status = self.config_ship_points_status.get(ship_id)
                                if point_status:
                                    if all_len == 0:
                                        pass
                                    else:
                                        point_status = [0] * all_len
                                        # if current_target_index != 0:
                                        for i in range(current_target_index + 1):
                                            point_status[i] = 1
                                    self.config_ship_points_status.update({ship_id: point_status})
                                    self.logger.debug({'################点状态': self.config_ship_points_status})
            except Exception as e:
                self.logger.error({'com_data_read error': e})


class TcpClient:
    def __init__(self):
        self.target_host = '127.0.0.1'  # 服务器端地址
        self.target_port = config.tcp_server_port  # 必须与服务器的端口号一致

    def connect_server(self):
        while True:
            try:
                self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.client.connect((self.target_host, self.target_port))
                break
            except Exception as e:
                time.sleep(2)
                # print(time.time(), 'connect_server error', e)
                continue

    def get(self):
        while True:
            try:
                response = self.client.recv(1024)
            except OSError:
                self.connect_server()
                response = self.client.recv(1024)
            # 如果没有client错误
            except AttributeError:
                time.sleep(1)
                continue
            # str_response = str(response)[2:-1]
            str_response = str(response)
            ship_obj.logger.info({'tcp rec': str_response})
            # 发送了开始
            ship_obj.logger.info({'str_response': str_response})
            if 'as' in str_response:
                send_data = 'asc'
                self.client.send(send_data.encode())
                ship_obj.b_send_path = True
                for i in ship_obj.online_ship_list:
                    ship_obj.ship_control_dict.update({int(i): 1})
                ship_obj.logger.info({'tcp send': send_data})
            # 发送了结束
            elif 'cs' in str_response:
                send_data = 'csc'
                self.client.send(send_data.encode())
                ship_obj.b_send_control = True
                for i in ship_obj.online_ship_list:
                    ship_obj.ship_control_dict.update({int(i): 0})
                ship_obj.logger.info({'tcp send': send_data})
            # 接受到其他发送error
            else:
                send_data = 'error'
                self.client.send(send_data.encode())


if __name__ == '__main__':
    ship_obj = Ship()
    tcp_obj = TcpClient()
    connect_server_thread = threading.Thread(target=tcp_obj.connect_server)
    init_cnts_lng_lat_to_pix = threading.Thread(target=ship_obj.init_cnts_lng_lat_to_pix, args=(False,))
    get_com_thread = threading.Thread(target=ship_obj.get_com_data)
    send_com_thread = threading.Thread(target=ship_obj.send_com_data)
    tcp_get_thread = threading.Thread(target=tcp_obj.get)

    # init_cnts_lng_lat_to_pix.setDaemon(True)
    # get_com_thread.setDaemon(True)
    # send_com_thread.setDaemon(True)
    connect_server_thread.start()
    init_cnts_lng_lat_to_pix.start()
    get_com_thread.start()
    send_com_thread.start()
    tcp_get_thread.start()

    # init_cnts_lng_lat_to_pix.join()
    # get_com_thread.join()
    # send_com_thread.join()
    # run_flask()
    ship_obj.run_flask(debug=False)
