"""
经纬度计算
"""
import math
import requests


# 测试通过
def DDD2DMS(number):
    D = number // 1
    temp = number % 1
    M = (temp * 60) // 1
    temp = (temp * 60) % 1
    S = (temp * 60)
    return D + (M / 100) + (S / 10000)


def angleFromCoordinate(long1, lat1, long2, lat2):
    """
    求两点的经纬度偏差角度 返回0-360,第一点为原点，第二点为目标点 以北为0度 逆时针为正方向
    :param long1: 第一点经度
    :param lat1: 第一点纬度
    :param long2: 第二点经度
    :param lat2: 第二点纬度
    :return: 角度 浮点数
    """
    lat1 = math.radians(DDD2DMS(lat1))
    lat2 = math.radians(DDD2DMS(lat2))
    long1 = math.radians(DDD2DMS(long1))
    long2 = math.radians(DDD2DMS(long2))
    y = math.sin(long2 - long1) * math.cos(lat2)
    x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * \
        math.cos(lat2) * math.cos(long2 - long1)
    deltaLon = long2 - long1
    theta = math.atan2(y, x)
    theta = math.degrees(theta)
    # print('row_theta',theta,'y, x',y, x)
    if theta > 0:
        theta = 360 - theta
    else:
        theta = abs(theta)
    return theta


def distanceFromCoordinate(lon1, lat1, lon2, lat2):
    """
    # 两点经纬度求两点的距离单位，返回单位米
    on the earth (specified in decimal degrees)
    :param long1: 第一点经度
    :param lat1: 第一点纬度
    :param long2: 第二点经度
    :param lat2: 第二点纬度
    :return: 距离 单位米
    """
    # 将十进制度数转化为弧度
    lon1, lat1, lon2, lat2 = map(math.radians, [lon1, lat1, lon2, lat2])
    # haversine公式
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * \
        math.cos(lat2) * math.sin(dlon / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))
    r = 6371  # 地球平均半径，单位为公里
    return c * r * 1000


def one_point_diatance_to_end(lng, lat, brng, d):
    """
    已知一点的经纬度和移动方向与距离，求终点的经纬度
    :param lng:经度
    :param lat:纬度
    :param brng: 右手坐标系角度 北为0度 逆时针为正
    :param d:距离单位米
    :return:求得的目标点经纬度 [经度, 纬度]
    """
    R = 6378.1  # Radius of the Earth
    brng = 360 - brng
    brng = math.radians(brng)  # Bearing is 90 degrees converted to radians.
    d = d / 1000  # Distance in km

    # lat2  52.20444 - the lat result I'm hoping for
    # lon2  0.36056 - the long result I'm hoping for.

    lat1 = math.radians(lat)  # Current lat point converted to radians
    lon1 = math.radians(lng)  # Current long point converted to radians

    lat2 = math.asin(math.sin(lat1) * math.cos(d / R) +
                     math.cos(lat1) * math.sin(d / R) * math.cos(brng))

    lon2 = lon1 + math.atan2(math.sin(brng) * math.sin(d / R) * math.cos(lat1),
                             math.cos(d / R) - math.sin(lat1) * math.sin(lat2))

    lat2 = math.degrees(lat2)
    lon2 = math.degrees(lon2)
    return [round(lon2, 6), round(lat2, 6)]


def gps_gaode_to_gps(gps, gps_gaode, gaode):
    """
        一个GPS和一个高德经纬度，计算高德经纬度的实际经纬度
        :param gps:传入GPS
        :param gps_gaode:传入GPS对应的高德经纬度
        :param gaode: 目标点高德经纬度
        :return: 目标点真实经纬度
        """
    distance = distanceFromCoordinate(gps_gaode[0],
                                      gps_gaode[1],
                                      gaode[0],
                                      gaode[1])
    theta = angleFromCoordinate(gps_gaode[0],
                                gps_gaode[1],
                                gaode[0],
                                gaode[1])
    return one_point_diatance_to_end(gps[0],
                                     gps[1],
                                     theta,
                                     distance)


def get_x_y_distance(lon_lat0, lon_lat1):
    """
    计算两点之间的x和y轴距离
    :return:
    """
    distance = distanceFromCoordinate(lon_lat0[0], lon_lat0[0], lon_lat1[1], lon_lat1[1])
    theta = angleFromCoordinate(lon_lat0[0], lon_lat0[0], lon_lat1[1], lon_lat1[1])
    # NED 坐标系下距离
    theta = ((360 - theta) % 360 + 90) % 360
    x = distance * math.sin(theta)
    y = distance * math.cos(theta)
    return x, y


def download_image(lng_lat, zoom=16, height=600, width=600, scale=1, gaode_key='8177df6428097c5e23d3280ffdc5a13a',
                   save_img_path='./statics/1.png'):
    png_url = 'https://restapi.amap.com/v3/staticmap?location={position}&zoom={zoom}&size={h}*{w}&scale={scale}&key={key}'.format(
        position='%f,%f' %
                 (lng_lat[0], lng_lat[1]), zoom=(
            zoom), h=height, w=width, scale=scale, key=gaode_key)
    response = requests.get(png_url)
    # 获取的文本实际上是图片的二进制文本
    img = response.content
    # 将他拷贝到本地文件 w 写  b 二进制  wb代表写入二进制文本
    with open(save_img_path, 'wb') as f:
        f.write(img)
    print('保存图片', save_img_path)


if __name__ == '__main__':
    import config
    lng_lat_gps = gps_gaode_to_gps(config.src_gps, config.src_gaode, config.lng_lat)
    print(lng_lat_gps)
    theta = angleFromCoordinate(config.src_gaode[0], config.src_gaode[1], config.lng_lat[0], config.lng_lat[1])
    print('##########theta1 0', theta)
    distance = distanceFromCoordinate(config.src_gaode[0], config.src_gaode[1], config.lng_lat[0], config.lng_lat[1])
    print('#############distance', distance)
    theta = angleFromCoordinate(config.src_gps[0], config.src_gps[1], lng_lat_gps[0], lng_lat_gps[1])
    print('##########theta1 0', theta)
    distance = distanceFromCoordinate(config.src_gps[0], config.src_gps[1], lng_lat_gps[0], lng_lat_gps[1])
    print('#############distance', distance)
    distance = distanceFromCoordinate(lng_lat_gps[0], lng_lat_gps[1], 114.520994, 30.508157)
    print(distanceFromCoordinate(lng_lat_gps[0], lng_lat_gps[1], 114.520212, 30.50848))
    print(angleFromCoordinate(lng_lat_gps[0], lng_lat_gps[1], 114.520212, 30.50848))
    print('##distance', distance)
    theta = angleFromCoordinate(114.348469, 30.464598, 114.520994, 30.508157)
    print('theta0 1', theta)
    theta = angleFromCoordinate(114.348469, 30.464598, 114.348369, 30.464698)
    print('theta-1 1', theta)
    theta = angleFromCoordinate(114.348469, 30.464598, 114.348369, 30.464598)
    print('theta-1 0', theta)
    theta = angleFromCoordinate(114.348469, 30.464598, 114.348369, 30.464498)
    print('theta-1 -1', theta)
    theta = angleFromCoordinate(114.348469, 30.464598, 114.348469, 30.4644988)
    print('theta0 -1', theta)
    theta = angleFromCoordinate(114.348469, 30.464598, 114.348569, 30.464498)
    print('theta1 -1', theta)
    # 30.505588, 114.524145
    # 30.505588,114.528145

    temp = one_point_diatance_to_end(114.316966, 30.576768, 90, 1)
    print(temp)
    # current 114.432112, 30.522414 target 114.432112, 30.522414