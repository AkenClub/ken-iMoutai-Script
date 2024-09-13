"""
4、预约商品

通知：运行结果会调用青龙面板的通知渠道。

配置环境变量：KEN_IMAOTAI_ENV
内容格式为：PHONE_NUMBER$USER_ID$DEVICE_ID$MT_VERSION$PRODUCT_ID_LIST$SHOP_ID$LAT$LNG$TOKEN$COOKIE
解释：手机号码$用户ID$设备ID$版本号$商品ID列表$店铺ID$纬度$经度$TOKEN$COOKIE
多个用户时使用 & 连接

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
- LAT: 用户所在位置的纬度。                           --- 运行 3_retrieve_shop_and_product_info.py 获取
- LNG: 用户所在位置的经度。                          --- 运行 3_retrieve_shop_and_product_info.py 获取


注意：可能会出现“商品ID XXX 申购失败:当前选择的门店不参与本场申购，请选择另外的门店申购”情况，则需要考虑是否要更换店铺。
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
            PHONE_NUMBER, USER_ID, DEVICE_ID, MT_VERSION, PRODUCT_ID_LIST, SHOP_ID, LAT, LNG, TOKEN, COOKIE = env.split(
                '$')
            user = {
                'PHONE_NUMBER': PHONE_NUMBER.strip(),
                'USER_ID': USER_ID.strip(),
                'DEVICE_ID': DEVICE_ID.strip(),
                'MT_VERSION': MT_VERSION.strip(),
                'PRODUCT_ID_LIST': ast.literal_eval(PRODUCT_ID_LIST.strip()),
                'SHOP_ID': SHOP_ID.strip(),
                'LAT': LAT.strip(),
                'LNG': LNG.strip(),
                'TOKEN': TOKEN.strip(),
                'COOKIE': COOKIE.strip()
            }
            # 检查字段是否完整且有值
            required_fields = [
                'PHONE_NUMBER', 'USER_ID', 'DEVICE_ID', 'MT_VERSION',
                'PRODUCT_ID_LIST', 'SHOP_ID', 'LAT', 'LNG', 'TOKEN', 'COOKIE'
            ]
            if all(user.get(field) for field in required_fields):
                # 判断 PRODUCT_ID_LIST 长度是否大于 0
                if len(user['PRODUCT_ID_LIST']) > 0:
                    users.append(user)
                else:
                    raise Exception("预约商品列表 - PRODUCT_ID_LIST 值为空，请添加后重试")
            else:
                logging.info(f"用户信息不完整: {user}")
        except Exception as e:
            logging.info(f"KEN_IMAOTAI_ENV 环境变量格式错误: {e}")

    logging.info("找到以下用户配置：")
    # 输出用户信息
    for index, user in enumerate(users):
        logging.info(f"用户 {index + 1}: {user['PHONE_NUMBER']}")

else:
    logging.info("KEN_IMAOTAI_ENV 环境变量未定义")

base_url_game = "https://h5.moutai519.com.cn/game"


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
    # 参数校验
    if not all([
            itemId, shopId, sessionId, userId, token, deviceId, mtVersion, lat,
            lng
    ]):
        logging.error("参数不完整，请检查输入参数")
        return "参数不完整"

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
        logging.info(f"商品ID {itemId} 预约成功: {result}")
        return result
    else:
        error_msg = '申购失败:' + response.json().get('message', "未知原因")
        logging.error(f"商品ID {itemId} {error_msg}")
        return error_msg


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

        items = json_object.get("data", {}).get("items", [])
        if items:
            item = items[0]
            logging.info(
                f"获取耐力值奖励成功: {'-'.join([item['goodName'], str(item['count'])])}"
            )
        else:
            raise Exception("未找到耐力值奖励信息")

    except Exception as e:
        logging.error(f"获取耐力值奖励失败: {e}")


# 查询累计申购的天数
def get_xmy_applying_reward(cookie, device_id, mt_version, lat, lng):
    url = f"{base_url_game}/xmyApplyingReward/cumulativelyApplyingDays"
    headers = generate_headers(device_id, mt_version, cookie, lat, lng)

    response = requests.post(url, headers=headers)
    body = response.text

    json_object = json.loads(body)
    if json_object.get("code") != 2000:
        message = json_object.get("message")
        raise Exception(f"查询累计申购奖励失败: {message}")
    # 奖励是否已经领取
    reward_received = json_object['data']['rewardReceived']
    #  当前申购的天数
    previous_days = json_object['data']['previousDays'] + 1

    logging.info(f"查询累计申购奖励成功: 累计申购天数: {previous_days} 天")

    for day in [7, 14, 21, 28]:
        if reward_received.get(str(day)):
            # 如果值 true，则表示已经领取了奖励，继续查询下一个奖励值
            continue
        if previous_days < day:
            # 如果当前申购奖励 false，而且累计申购的天数小于当前奖励的天数，则无需继续查询
            logging.info(f"累计申购不满足奖励要求，下一等级：{day}天，继续加油！")
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
        f"领取累计申购奖励成功: 累计申购天数: {cumulativelyApplyingDays} 天，奖励小茅运: {reward_amount}"
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
        logging.error(f"查询 & 领取累计申购的小茅运失败: {e}")


# 7 日连续申购领取小茅运奖励
def receive_7_day_reward(cookie, device_id, mt_version, lat, lng):
    try:
        url = f"{base_url_game}/xmyApplyingReward/7DaysContinuouslyApplyingProgress"
        headers = generate_headers(device_id, mt_version, cookie, lat, lng)

        progress_response = requests.post(url, headers=headers)
        progress_data = json.loads(progress_response.text)
        if progress_data.get("code") != 2000:
            message = progress_data.get("message")
            raise Exception(f"查询失败: {message}")

        # 当前连续申购天数
        current_progress = progress_data['data']['previousProgress'] + 1
        if current_progress < 7:
            logging.info(f"当前连续申购天数: {current_progress} 天，不满足 7 天奖励要求")
            return

        # 领取奖励
        url = f"{base_url_game}/xmyApplyingReward/receive7DaysContinuouslyApplyingReward"

        reward_response = requests.post(url, headers=headers)
        reward_data = json.loads(reward_response.text)
        if reward_data.get("code") != 2000:
            message = reward_data.get("message")
            raise Exception(f"领取失败: {message}")
        reward_amount = reward_data['data']['rewardAmount']
        logging.info(f"领取 7 日连续申购领取小茅运奖励成功，奖励小茅运: {reward_amount}")

    except Exception as e:
        logging.error(f"7 日连续申购领取小茅运奖励异常: {e}")


# 获取 Session ID，每天都会变化
def get_session_id():
    # 生成时间戳
    timestamp = str(int(time.mktime(datetime.date.today().timetuple())) * 1000)

    # 发送请求
    api_url = f"https://static.moutai519.com.cn/mt-backend/xhr/front/mall/index/session/get/{timestamp}"
    response = requests.get(api_url)
    data = response.json()
    if data["code"] != 2000:
        raise Exception("获取商品信息失败")

    # 解析响应
    sessionId = data["data"]["sessionId"]
    return sessionId


# i茅台~ 启动！
def start(session_id, user):
    logging.info('--------------------------')
    logging.info(f"用户：{user['PHONE_NUMBER']}，开始预约商品")
    for product_id in user["PRODUCT_ID_LIST"]:
        reserve_product(itemId=product_id,
                        shopId=user["SHOP_ID"],
                        sessionId=session_id,
                        userId=user["USER_ID"],
                        token=user["TOKEN"],
                        deviceId=user["DEVICE_ID"],
                        mtVersion=user["MT_VERSION"],
                        lat=user["LAT"],
                        lng=user["LNG"])

    logging.info("所有商品预约完成, 3 秒后获取耐力值奖励")

    # 延迟 3 秒
    time.sleep(3)
    logging.info("开始获取耐力值奖励")
    get_energy_award(user["COOKIE"], user["DEVICE_ID"], user["MT_VERSION"],
                     user["LAT"], user["LNG"])

    # 延迟 3 秒
    time.sleep(3)
    logging.info("查询 & 领取累计申购的小茅运")
    get_receive_xmy_applying_reward(user["COOKIE"], user["DEVICE_ID"],
                                    user["MT_VERSION"], user["LAT"],
                                    user["LNG"])

    # 延迟 3 秒
    time.sleep(3)
    logging.info("查询 & 领取 7 日连续申购领取小茅运")
    receive_7_day_reward(user["COOKIE"], user["DEVICE_ID"], user["MT_VERSION"],
                         user["LAT"], user["LNG"])


if __name__ == "__main__":
    session_id = get_session_id()
    for user in users:
        start(session_id, user)

    logging.info('--------------------------')
    logging.info("所有用户预约完成")

    log_contents = log_stream.getvalue()
    send("i茅台预约日志：", log_contents)
