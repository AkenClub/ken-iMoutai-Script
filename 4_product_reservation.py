"""
4、预约商品

通知：运行结果会调用青龙面板的通知渠道。

配置环境变量：KEN_IMAOTAI_ENV
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

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from notify import send

# 每日 9:10 开始预约
'''
cron: 10 9 * * *
new Env("4_预约申购")
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
# 会话 ID
session_id = None
# 全部店铺信息
all_shops_info = None

# 调试模式
DEBUG = False

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
            PHONE_NUMBER, USER_ID, DEVICE_ID, MT_VERSION, PRODUCT_ID_LIST, SHOP_INFO, LAT, LNG, TOKEN, COOKIE = env.split(
                '$')

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

base_url_game = "https://h5.moutai519.com.cn/game"


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
                    mtVersion, lat, lng, shop_mode, province, city):
    if shop_mode is None:
        logger.info(f"⚡ 重新预约：店铺 ID：{shopId}, 商品 ID：{itemId}")

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
        # 如果 message 包含 "请选择另外的门店申购"，则根据店铺缺货模式获取可预约的店铺 ID
        if "请选择另外的门店申购" in message:
            if shop_mode:
                try:
                    logging.info(f"--- 🏁 根据店铺缺货模式 {shop_mode} 获取可预约的店铺 ID")
                    shop_id_new = get_shop_id_by_mode(lat, lng, shop_mode,
                                                      province, city, itemId)
                    if shop_id_new:
                        logging.info(
                            f"--- 🏁 获取可预约的店铺 ID 成功，店铺 ID: {shop_id_new}，重新预约商品"
                        )
                        # 这里特地传 None，在尝试自动预约其他店铺失败时，不再递归调用
                        reserve_product(itemId, shop_id_new, sessionId, userId,
                                        token, deviceId, mtVersion, lat, lng,
                                        None, None, None)
                    else:
                        logging.info(
                            f"--- 🚫 获取可预约的店铺 ID 失败，请检查店铺缺货模式 SHOP_ID^SHOP_MODE^PROVINCE^CITY 值 是否正确"
                        )
                except Exception as e:
                    logging.error(f"--- 🚫 获取可预约的店铺 ID 失败: {e}")
            else:
                logging.info(
                    f"🚫 店铺缺货模式未设置，无法自动预约其他店铺，请手动在APP上预约 或者 设置 SHOP_ID^SHOP_MODE^PROVINCE^CITY 值"
                )


# 获取申购耐力值
def get_energy_award(cookie, device_id, mt_version, lat, lng):
    try:
        url = f"{base_url_game}/isolationPage/getUserEnergyAward"
        headers = generate_headers(device_id, mt_version, cookie, lat, lng)

        response = requests.post(url, headers=headers)
        body = response.text

        json_object = json.loads(body)
        if json_object.get("code") != 200:
            message = json_object.get("message")
            raise Exception(message)

        award_rule = json_object.get("data", {}).get("awardRule", [])
        award_result = ""
        if award_rule:
            for item in award_rule:
                if item and 'goodName' in item and 'count' in item:
                    award_result += f"{item['goodName']} - {item['count']};"
        else:
            award_result += "未找到耐力值奖励信息"
        logging.info(f"🎁 获得耐力值奖励: {award_result}")

    except Exception as e:
        logging.error(f"🚫 获取耐力值奖励失败: {e}")


# 查询累计申购的天数
def get_xmy_applying_reward(cookie, device_id, mt_version, lat, lng):
    url = f"{base_url_game}/xmyApplyingReward/cumulativelyApplyingDays"
    headers = generate_headers(device_id, mt_version, cookie, lat, lng)

    response = requests.post(url, headers=headers)
    body = response.text

    json_object = json.loads(body)
    if json_object.get("code") != 2000:
        message = json_object.get("message")
        raise Exception(f"🚫 查询累计申购奖励失败: {message}")
    # 奖励是否已经领取
    reward_received = json_object['data']['rewardReceived']
    #  当前申购的天数
    previous_days = json_object['data']['previousDays'] + 1

    logging.info(f"📅 查询累计申购奖励成功: 累计申购天数: {previous_days} 天")

    for day in [7, 14, 21, 28]:
        if reward_received.get(str(day)):
            # 如果值 true，则表示已经领取了奖励，继续查询下一个奖励值
            continue
        if previous_days < day:
            # 如果当前申购奖励 false，而且累计申购的天数小于当前奖励的天数，则无需继续查询
            logging.info(f"🚫 累计申购不满足奖励要求，下一等级：{day}天，继续加油！")
            return -1
        # 找到能领取奖励的天数
        return day


# 领取累计申购奖励
def receive_xmy_applying_reward(cookie, device_id, mt_version, lat, lng,
                                cumulativelyApplyingDays):
    url = f"{base_url_game}/xmyApplyingReward/receiveCumulativelyApplyingReward"
    headers = generate_headers(device_id, mt_version, cookie, lat, lng)

    requestBody = {"cumulativelyApplyingDays": cumulativelyApplyingDays}

    response = requests.post(url, headers=headers, json=requestBody)
    body = response.text

    json_object = json.loads(body)
    if json_object.get("code") != 2000:
        message = json_object.get("message")
        raise Exception(f"领取累计申购奖励失败: {message}")

    # 领取的奖励值
    reward_amount = json_object['data']['rewardAmount']
    logging.info(
        f"🎁 领取累计申购奖励成功: 📅 累计申购天数: {cumulativelyApplyingDays} 天，奖励小茅运: {reward_amount}"
    )


# 查询 & 领取累计申购的小茅运
def get_receive_xmy_applying_reward(cookie, deviceId, mtVersion, lat, lng):
    try:
        cumulativelyApplyingDays = get_xmy_applying_reward(
            cookie, deviceId, mtVersion, lat, lng)
        if cumulativelyApplyingDays > 0:
            receive_xmy_applying_reward(cookie, deviceId, mtVersion, lat, lng,
                                        cumulativelyApplyingDays)
    except Exception as e:
        logging.error(f"🚫 查询 & 领取累计申购的小茅运失败: {e}")


# 7 日连续申购领取小茅运奖励
def receive_7_day_reward(cookie, device_id, mt_version, lat, lng):
    try:
        url = f"{base_url_game}/xmyApplyingReward/7DaysContinuouslyApplyingProgress"
        headers = generate_headers(device_id, mt_version, cookie, lat, lng)

        progress_response = requests.post(url, headers=headers)
        progress_data = json.loads(progress_response.text)
        if progress_data.get("code") != 2000:
            message = progress_data.get("message")
            raise Exception(f"🚫 查询 7 日连续申购失败: {message}")

        # 当前连续申购天数
        current_progress = progress_data['data']['previousProgress'] + 1
        if current_progress < 7:
            logging.info(f"🚫 当前连续申购天数: {current_progress} 天，不满足 7 天奖励要求")
            return

        # 领取奖励
        url = f"{base_url_game}/xmyApplyingReward/receive7DaysContinuouslyApplyingReward"

        reward_response = requests.post(url, headers=headers)
        reward_data = json.loads(reward_response.text)
        if reward_data.get("code") != 2000:
            message = reward_data.get("message")
            raise Exception(f"领取失败: {message}")
        reward_amount = reward_data['data']['rewardAmount']
        logging.info(f"🎁 领取 7 日连续申购领取小茅运奖励成功，奖励小茅运: {reward_amount}")

    except Exception as e:
        logging.error(f"🚫 7 日连续申购领取小茅运奖励异常: {e}")


# 获取 Session ID，每天都会变化
def get_session_id():
    global timestamp_today

    # 发送请求
    api_url = f"https://static.moutai519.com.cn/mt-backend/xhr/front/mall/index/session/get/{timestamp_today}"
    response = requests.get(api_url)
    data = response.json()
    if data["code"] != 2000:
        raise Exception("🚫 获取 Session ID 失败")

    # 解析响应
    sessionId = data["data"]["sessionId"]
    return sessionId


# i茅台~ 启动！
def start(user):
    global session_id

    logging.info('--------------------------')
    logging.info(f"🧾 用户：{user['PHONE_NUMBER']}，开始预约商品")

    if user["SHOP_ID"] == "AUTO":
        logging.info(f"🏁 店铺 ID 为 AUTO，根据店铺模式 {user['SHOP_MODE']} 获取店铺 ID")

    for product_id in user["PRODUCT_ID_LIST"]:
        shop_id = user["SHOP_ID"]

        # 判断 SHOP_ID 是否为 AUTO，如果是，则根据 SHOP_MODE 获取店铺 ID
        if user["SHOP_ID"] == "AUTO":
            shop_id = get_shop_id_by_mode(user["LAT"], user["LNG"],
                                          user["SHOP_MODE"], user["PROVINCE"],
                                          user["CITY"], product_id)
            logging.info(f"🚩 商品ID：{product_id}，获取店铺 ID（{shop_id}）成功")

        reserve_product(itemId=product_id,
                        shopId=shop_id,
                        sessionId=session_id,
                        userId=user["USER_ID"],
                        token=user["TOKEN"],
                        deviceId=user["DEVICE_ID"],
                        mtVersion=user["MT_VERSION"],
                        lat=user["LAT"],
                        lng=user["LNG"],
                        shop_mode=user["SHOP_MODE"],
                        province=user["PROVINCE"],
                        city=user["CITY"])

    logging.info("🎁 所有商品预约完成, 3 秒后获取耐力值奖励")

    # 延迟 3 秒
    time.sleep(3)
    logging.info("🏁 开始获取耐力值奖励")
    get_energy_award(user["COOKIE"], user["DEVICE_ID"], user["MT_VERSION"],
                     user["LAT"], user["LNG"])

    # 延迟 3 秒
    time.sleep(3)
    logging.info("🏁 查询 & 领取累计申购的小茅运")
    get_receive_xmy_applying_reward(user["COOKIE"], user["DEVICE_ID"],
                                    user["MT_VERSION"], user["LAT"],
                                    user["LNG"])

    # 延迟 3 秒
    time.sleep(3)
    logging.info("🏁 查询 & 领取 7 日连续申购领取小茅运")
    receive_7_day_reward(user["COOKIE"], user["DEVICE_ID"], user["MT_VERSION"],
                         user["LAT"], user["LNG"])


# 获取售卖商店信息
def get_shop_info(province_name, city_name):
    # 第一步：获取myserviceshops的URL
    api_url = "https://static.moutai519.com.cn/mt-backend/xhr/front/mall/resource/get"
    response = requests.get(api_url)
    data = response.json()

    if data["code"] != 2000:
        raise Exception("🚫 获取资源信息失败")

    myserviceshops_url = data["data"]["myserviceshops"]["url"]

    # 第二步：下载并解析myserviceshops.json
    response = requests.get(myserviceshops_url)
    shops_data = response.json()

    # 第三步：根据provinceName和cityName过滤数据
    result = []
    for _, shop_info in shops_data.items():
        if shop_info["provinceName"] == province_name and shop_info[
                "cityName"] == city_name:
            result.append({
                "lat": shop_info["lat"],
                "lng": shop_info["lng"],
                "name": shop_info["name"],
                "shopId": shop_info["shopId"]
            })

    return result


# 获取指定商品可以预约的店铺信息
def get_shop_by_product_id(province_name, product_id):
    global timestamp_today
    global session_id

    api_url = f"https://static.moutai519.com.cn/mt-backend/xhr/front/mall/shop/list/slim/v3/{session_id}/{province_name}/{product_id}/{timestamp_today}"
    response = requests.get(api_url)
    data = response.json()

    if data["code"] != 2000:
        raise Exception("🚫 获取指定商品可以预约的店铺信息失败")

    # 解析响应，获取 product_id = itemId 的店铺 shopId、inventory
    result = []
    for shop in data["data"]["shops"]:
        for item in shop["items"]:
            if item["itemId"] == product_id:
                result.append({
                    "shopId": shop["shopId"],
                    "inventory": item["inventory"]
                })
    return result


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
def get_shop_id_by_mode(lat, lng, shop_mode, province_name, city_name,
                        product_id):
    # 判断入参是否为空
    if not lat or not lng or not shop_mode or not province_name or not city_name or not product_id:
        logging.warning("🚫 缺货模式 - 获取店铺ID失败，请检查入参")
        return ""

    global all_shops_info, DEBUG
    # 判断 all_shops_info 是否为空，如果为空，则获取所有店铺信息
    if all_shops_info is None:
        all_shops_info = get_shop_info(province_name, city_name)
        debug_log(f"--- 🏁 获取本城市（{province_name}-{city_name}）所有店铺信息 成功")

    # 不同的商品 ID 获取到的数量不同，需要重新获取
    shops_by_product_id = get_shop_by_product_id(province_name, product_id)
    debug_log(f"--- 🏁 获取本省份（{province_name}）指定商品（{product_id}）可以预约的店铺信息 成功")

    # 筛选 省份内所有能预约的店铺 在 用户选的城市店铺 中有哪些
    filter_shops = []
    for shop_province in shops_by_product_id:
        for shop_city in all_shops_info:
            if shop_province["shopId"] == shop_city["shopId"]:
                # 把 inventory 库存数量 添加到 shop_city 中，复制 shop_city 不改变原来 all_shops_info 数据
                shop_city_copy = shop_city.copy()
                shop_city_copy["inventory"] = shop_province["inventory"]
                filter_shops.append(shop_city_copy)
                debug_log(f"--- 🏁 --- 店铺信息: {shop_city_copy}")
                break

    # 根据 SHOP_MODE 是 NEAREST 或 INVENTORY，获取店铺ID
    if shop_mode == "NEAREST":
        debug_log("--- 🏁 店铺缺货模式：NEAREST（距离最近）")
        # 计算用户位置到店铺的距离，并且按照距离近到远排序，把距离添加到 filter_shops 中
        for shop in filter_shops:
            distance = haversine(float(lat), float(lng), float(shop["lat"]),
                                 float(shop["lng"]))
            shop["distance"] = distance
        filter_shops.sort(key=lambda x: x["distance"])
        if DEBUG:
            logging.info(f"--- 🏁 用户位置到各个店铺的距离: ")
            for shop in filter_shops:
                logging.info(
                    f"--- 🏁 --- 店铺名称: {shop.get('name')}, 店铺ID：{shop.get('shopId')}，距离: {shop.get('distance')} 公里"
                )

        debug_log(
            f"--- 🏁 找到最近的店铺：{filter_shops[0].get('name')}, 店铺ID：{filter_shops[0].get('shopId')}，距离：{filter_shops[0].get('distance')} 公里"
        )

    elif shop_mode == "INVENTORY":
        debug_log("--- 🏁 店铺缺货模式：INVENTORY（库存最多）")
        filter_shops.sort(key=lambda x: x["inventory"], reverse=True)
        debug_log(
            f"--- 🏁 找到库存最多的店铺：{filter_shops[0].get('name')}, 店铺ID：{filter_shops[0].get('shopId')}，库存：{filter_shops[0].get('inventory')}"
        )

    # 返回店铺ID，如果 filter_shops 为空，则返回异常
    if len(filter_shops) == 0:
        raise Exception("--- 🚫 没有找到可以预约的店铺")
    return filter_shops[0]["shopId"]


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

    session_id = get_session_id()
    for user in users:
        start(user)

    logging.info('--------------------------')
    logging.info(" ✅ 所有用户预约完成")

    log_contents = log_stream.getvalue()
    send("i茅台预约日志：", log_contents)
