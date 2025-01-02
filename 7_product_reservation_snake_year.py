"""
7、预约申购_蛇年茅台 - 2025年1月1日 - 1月5日 活动

9点到10点预约，18 点公布名单。
无需添加蛇茅的商品ID和店铺ID，会从接口自动获取。
如果查询到支持预约蛇茅的店铺数量大于1，会自动选择离你最近的店铺。不支持库存最多的模式。

通知：运行结果会调用青龙面板的通知渠道。

配置环境变量：KEN_IMAOTAI_ENV
-- 在旧版本青龙（例如 v2.13.8）中，使用 $ 作为分隔符时会出现解析环境变量失败，此时可以把 `$` 分隔符换为 `#` 作为分隔符。
-- 📣 怕出错？**建议直接使用 `#` 作为分隔符即可** (2024-10-15 更新支持)。
内容格式为：PHONE_NUMBER$USER_ID$DEVICE_ID$MT_VERSION$PRODUCT_ID_LIST$SHOP_ID^SHOP_MODE^PROVINCE^CITY$LAT$LNG$TOKEN$COOKIE
解释：手机号码$用户ID$设备ID$版本号$商品ID列表$店铺ID店铺缺货时自动采用的模式^省份^城市$纬度$经度$TOKEN$COOKIE
多个用户时使用 & 连接

说明：^SHOP_MODE^PROVINCE^CITY 为可选

常量。
- PHONE_NUMBER: 用户的手机号码。                    --- 自己手机号码
- CODE: 短信验证码。                                --- 运行 1_generate_code.py 获取
- DEVICE_ID: 设备的唯一标识符。                      --- 运行 1_generate_code.py 获取
- MT_VERSION: 应用程序的版本号。                     --- 运行 1_generate_code.py 获取
- USER_ID: 用户的唯一标识符。                        --- 运行 2_login.py 获取
- TOKEN: 用于身份验证的令牌。                        --- 运行 2_login.py 获取
- COOKIE: 用于会话管理的Cookie。                     --- 运行 2_login.py 获取
- PRODUCT_ID_LIST: 商品ID列表，表示用户想要预约的商品。--- 运行 3_retrieve_shop_and_product_info.py 获取
- SHOP_ID: 店铺的唯一标识符。                         --- 运行 3_retrieve_shop_and_product_info.py 获取
           可设置为 AUTO，则根据 SHOP_MODE 的值来选择店铺 ID。
- SHOP_MODE：店铺缺货模式，可选值为NEAREST（距离最近）或INVENTORY（库存最多）。设置该值时，需要同时设置 PROVINCE 和 CITY。
             非必填，但 SHOP_ID 设置 AUTO 时为必填，需要同时设置 SHOP_MODE、PROVINCE 和 CITY。
- PROVINCE: 用户所在的省份。                          --- 与 3_retrieve_shop_and_product_info.py 填写的省份一致
            非必填，但 SHOP_MODE 设置为 NEAREST 或 INVENTORY 时为必填。
- CITY: 用户所在的城市。                              --- 与 3_retrieve_shop_and_product_info.py 填写的城市一致
            非必填，但 SHOP_MODE 设置为 NEAREST 或 INVENTORY 时为必填。
- LAT: 用户所在位置的纬度。                           --- 运行 3_retrieve_shop_and_product_info.py 获取
- LNG: 用户所在位置的经度。                          --- 运行 3_retrieve_shop_and_product_info.py 获取

"""

import datetime
import time
import requests
import json
import logging
import base64
import os
import ast
import io
import math
import re

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from notify import send

# 1月1日-1月5日 9:12 开始预约
'''
cron: 12 9 1-5 1 *
new Env("7_预约申购_蛇年茅台-1月1日-1月5日")
'''

# 创建 StringIO 对象
log_stream = io.StringIO()

# 配置 logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# 创建控制台 Handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(
    logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

# 创建 StringIO Handler
stream_handler = logging.StreamHandler(log_stream)
# stream_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

# 将两个 Handler 添加到 logger
logger.addHandler(console_handler)
logger.addHandler(stream_handler)

# 当天零点的时间戳
timestamp_today = None

# 调试模式
DEBUG = True

# 读取 KEN_IMAOTAI_ENV 环境变量
KEN_IMAOTAI_ENV = os.getenv('KEN_IMAOTAI_ENV', '')

# 加密 KEY
ENCRYPT_KEY = "qbhajinldepmucsonaaaccgypwuvcjaa"
# 加密 IV
ENCRYPT_IV = "2018534749963515"

# 解析 KEN_IMAOTAI_ENV 环境变量并保存到 user 列表
users = []
if KEN_IMAOTAI_ENV:
    env_list = KEN_IMAOTAI_ENV.split('&')
    for env in env_list:
        try:
            # 使用 re.split() 分割字符串，支持 '#' 和 '$'
            split_values = re.split(r'[#$]', env)

            PHONE_NUMBER, USER_ID, DEVICE_ID, MT_VERSION, PRODUCT_ID_LIST, SHOP_INFO, LAT, LNG, TOKEN, COOKIE = split_values

            SHOP_MODE = ''
            PROVINCE = ''
            CITY = ''

            if '^' in SHOP_INFO:
                parts = SHOP_INFO.split('^')
                if len(parts) > 1:
                    # 检测 parts 长度是否为 4，否则抛出异常
                    if len(parts) != 4:
                        raise Exception(
                            "🚫 店铺缺货模式值错误，请检查是否为 SHOP_ID^SHOP_MODE^PROVINCE^CITY"
                        )
                    SHOP_ID, SHOP_MODE, PROVINCE, CITY = parts
                    # 检测 SHOP_MODE 是否为 NEAREST 或 INVENTORY
                    if SHOP_MODE not in ['NEAREST', 'INVENTORY']:
                        raise Exception(
                            "🚫 店铺缺货模式值错误，请检查 SHOP_MODE 值是否为 NEAREST（<默认> 距离最近） 或 INVENTORY（库存最多）"
                        )
                        # 如果 SHOP_MODE 值合法，则需要配合检测 PROVINCE 和 CITY 是否为空（接口需要用到这些值）
                    if not PROVINCE or not CITY:
                        raise Exception(
                            "🚫 店铺缺货模式值为 NEAREST 或 INVENTORY 时，需要同时设置 PROVINCE 和 CITY"
                        )
            else:
                logging.warning(
                    "🚨🚨 建议根据环境变量格式，设置 SHOP_ID^SHOP_MODE^PROVINCE^CITY 值，否则无法在指定店铺缺货时自动预约其他店铺！🚨🚨"
                )
                # 如果 SHOP_INFO 没有 ^ 符号，则 SHOP_ID 为 SHOP_INFO
                SHOP_ID = SHOP_INFO

            # 如果 SHOP_ID 为 AUTO，检查 SHOP_MODE 是否为空
            if SHOP_ID == 'AUTO' and not SHOP_MODE:
                raise Exception(
                    "🚫 店铺缺货模式值错误，SHOP_ID 值为 AUTO 时，需设置 SHOP_MODE、PROVINCE 和 CITY 值 "
                )

            user = {
                'PHONE_NUMBER': PHONE_NUMBER.strip(),
                'USER_ID': USER_ID.strip(),
                'DEVICE_ID': DEVICE_ID.strip(),
                'MT_VERSION': MT_VERSION.strip(),
                'PRODUCT_ID_LIST': ast.literal_eval(PRODUCT_ID_LIST.strip()),
                'SHOP_ID': SHOP_ID.strip(),
                'SHOP_MODE': SHOP_MODE.strip(),
                'PROVINCE': PROVINCE.strip(),
                'CITY': CITY.strip(),
                'LAT': LAT.strip(),
                'LNG': LNG.strip(),
                'TOKEN': TOKEN.strip(),
                'COOKIE': COOKIE.strip()
            }
            # 检查字段是否完整且有值，不检查 SHOP_MODE、PROVICE、CITY 字段（PROVICE 和 CITY 用于 SHOP_MODE 里，而 SHOP_MODE 可选）
            required_fields = [
                'PHONE_NUMBER', 'USER_ID', 'DEVICE_ID', 'MT_VERSION',
                'PRODUCT_ID_LIST', 'SHOP_ID', 'LAT', 'LNG', 'TOKEN', 'COOKIE'
            ]
            if all(user.get(field) for field in required_fields):
                # 判断 PRODUCT_ID_LIST 长度是否大于 0
                if len(user['PRODUCT_ID_LIST']) > 0:
                    users.append(user)
                else:
                    raise Exception("🚫 预约商品列表 - PRODUCT_ID_LIST 值为空，请添加后重试")
            else:
                logging.info(f"🚫 用户信息不完整: {user}")
        except Exception as e:
            errText = f"🚫 KEN_IMAOTAI_ENV 环境变量格式错误: {e}"
            send("i茅台预约日志：", errText)
            raise Exception(errText)

    logging.info("找到以下用户配置：")
    # 输出用户信息
    for index, user in enumerate(users):
        if DEBUG:
            logging.info(f"用户 {index + 1}: {user}")
            continue
        logging.info(f"用户 {index + 1}: 📞 {user['PHONE_NUMBER']}")

else:
    errText = "🚫 KEN_IMAOTAI_ENV 环境变量未定义"
    send("i茅台预约日志：", errText)
    raise Exception(errText)


# DEBUG 控制日志输出
def debug_log(message):
    if DEBUG:
        logging.info(message)


# 生成请求头
def generate_headers(device_id, mt_version, cookie, lat=None, lng=None):
    headers = {
        "MT-Device-ID": device_id,
        "MT-APP-Version": mt_version,
        "User-Agent": "iOS;16.3;Apple;?unrecognized?",
        "Cookie": f"MT-Token-Wap={cookie};MT-Device-ID-Wap={device_id};"
    }
    if lat and lng:
        headers["MT-Lat"] = lat
        headers["MT-Lng"] = lng
    return headers


# 加密
def aes_cbc_encrypt(data, key, iv):
    cipher = AES.new(key.encode('utf-8'), AES.MODE_CBC, iv.encode('utf-8'))
    padded_data = pad(data.encode('utf-8'), AES.block_size)
    encrypted_data = cipher.encrypt(padded_data)
    return base64.b64encode(encrypted_data).decode('utf-8')


# 预约商品
def reserve_product(itemId, shopId, sessionId, userId, token, deviceId,
                    mtVersion, lat, lng):

    mt_k = f'{int(time.time() * 1000)}'
    headers = {
        'User-Agent': 'iOS;16.3;Apple;?unrecognized?',
        'MT-Token': token,
        'MT-Network-Type': 'WIFI',
        'MT-User-Tag': '0',
        'MT-K': mt_k,
        'MT-Info': '028e7f96f6369cafe1d105579c5b9377',
        'MT-APP-Version': mtVersion,
        'Accept-Language': 'zh-Hans-CN;q=1',
        'MT-Device-ID': deviceId,
        'MT-Bundle-ID': 'com.moutai.mall',
        'MT-Lng': lng,
        'MT-Lat': lat,
        'Content-Type': 'application/json',
        'userId': str(userId)
    }
    requestBody = {
        "itemInfoList": [{
            "count": 1,
            "itemId": str(itemId)
        }],
        "sessionId": sessionId,
        "userId": str(userId),
        "shopId": str(shopId)
    }
    actParam = aes_cbc_encrypt(json.dumps(requestBody), ENCRYPT_KEY,
                               ENCRYPT_IV)
    requestBody['actParam'] = actParam
    response = requests.post(
        'https://app.moutai519.com.cn/xhr/front/mall/reservation/add',
        headers=headers,
        json=requestBody)
    code = response.json().get('code', 0)
    if code == 2000:
        result = response.json().get('data', {}).get('successDesc', "未知")
        logging.info(f"🛒 商品ID {itemId} ✅ 预约成功: {result}")
        return result
    else:
        message = response.json().get("message", "未知原因")
        error_msg = f'🚫 预约失败: 错误码 {code}, 错误信息: {message}'
        logging.error(f"🛒 商品ID {itemId} {error_msg}")


# 获取蛇年茅台商品信息
def get_snake_year_production_info():
    global timestamp_today

    # 发送请求
    api_url = f"https://h5.moutai519.com.cn/xhr/front/mall/index/special/session/getByType/5?__timestamp={timestamp_today}"
    response = requests.get(api_url)
    data = response.json()
    if data["code"] != 2000:
        raise Exception("🚫 获取蛇年茅台商品信息失败")

    # 解析响应
    session_id = data["data"]["sessionId"]
    item_list = data["data"]["itemList"]
    # 商品 ID
    product_id = item_list[0]["itemCode"]
    # 店铺信息
    shop_info_list = item_list[0]["shopList"]
    return session_id, product_id, shop_info_list


# i茅台~ 启动！
def start(user, session_id, product_id, shop_info_list):

    logging.info('--------------------------')
    logging.info(f"🧾 用户：{user['PHONE_NUMBER']}，开始预约蛇茅。")

    logging.info(f"🏁 如果查询到支持预约蛇茅的店铺数量大于1，会自动选择离你最近的店铺。不支持库存最多的模式。")
    try:
        shop_id = get_shop_id(user["LAT"], user["LNG"], shop_info_list)

        reserve_product(itemId=product_id,
                        shopId=shop_id,
                        sessionId=session_id,
                        userId=user["USER_ID"],
                        token=user["TOKEN"],
                        deviceId=user["DEVICE_ID"],
                        mtVersion=user["MT_VERSION"],
                        lat=user["LAT"],
                        lng=user["LNG"])
    except Exception as e:
        logging.error(f"🚫 预约商品ID {product_id} 失败: {e}")


# 获取两个地点之间的距离
def haversine(lat1, lng1, lat2, lng2):
    # 将经纬度转换为弧度
    lat1, lng1, lat2, lng2 = map(math.radians, [lat1, lng1, lat2, lng2])

    # Haversine 公式
    dlat = lat2 - lat1
    dlng = lng2 - lng1
    a = math.sin(
        dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    # 地球半径（公里）
    R = 6371.0
    distance = R * c
    # 保留三位小数
    return round(distance, 3)


# 根据 SHOP_MODE 获取店铺ID
def get_shop_id(lat, lng, shop_info_list):
    # 判断入参是否为空
    if not lat or not lng or not shop_info_list:
        logging.warning("🚫 获取店铺ID失败，请检查入参")
        return ""

    if len(shop_info_list) > 1:
        # 计算用户位置到店铺的距离，并且按照距离近到远排序，把距离添加到 shop_info_list 中
        for shop in shop_info_list:
            distance = haversine(float(lat), float(lng), float(shop["lat"]),
                                 float(shop["lng"]))
            shop["distance"] = distance
        shop_info_list.sort(key=lambda x: x["distance"])
        if DEBUG:
            debug_log(f"--- 🏁 用户位置到各个店铺的距离: ")
            for shop in shop_info_list:
                debug_log(
                    f"--- 🏁 --- 店铺名称: {shop.get('name')}, 店铺ID：{shop.get('shopId')}，距离: {shop.get('distance')} 公里"
                )
        debug_log(
            f"--- 🏁 找到最近的店铺：{shop_info_list[0].get('name')}, 店铺ID：{shop_info_list[0].get('shopId')}，距离：{shop_info_list[0].get('distance')} 公里"
        )
    else:
        debug_log(f"--- 🏁 只有一个店铺，直接使用该店铺ID：{shop_info_list[0].get('shopId')}")

    logging.info(
        f"--- 🏁 获取店铺ID成功，店铺ID：{shop_info_list[0].get('shopId')}，店铺名：{shop_info_list[0].get('name')}"
    )
    return shop_info_list[0]["shopId"]


if __name__ == "__main__":
    if not DEBUG:
        # 判断当前时间是否是 9:00 到 10:00 期间
        now = datetime.datetime.now()
        if now.hour < 9 or now.hour > 10:
            err_msg = "🚫 当前时间不在 9:00 到 10:00 期间，不执行预约"
            logger.warning(err_msg)
            send("i茅台预约日志：", err_msg)
            exit()

    # 生成时间戳
    timestamp_today = str(
        int(time.mktime(datetime.date.today().timetuple())) * 1000)

    session_id, product_id, shop_info_list = get_snake_year_production_info()
    for user in users:
        start(user, session_id, product_id, shop_info_list)

    logging.info('--------------------------')
    logging.info(" ✅ 所有用户预约完成")

    log_contents = log_stream.getvalue()
    send("i茅台预约日志：", log_contents)
