"""
5、旅行 & 获取小茅运、首次分享奖励

通知：运行结果会调用青龙面板的通知渠道。


配置环境变量：KEN_IMAOTAI_ENV
内容格式为：PHONE_NUMBER$USER_ID$DEVICE_ID$MT_VERSION$PRODUCT_ID_LIST$SHOP_ID$LAT$LNG$TOKEN$COOKIE
解释：手机号码$用户ID$设备ID$版本号$商品ID列表$店铺ID$纬度$经度$TOKEN$COOKIE
多个用户时使用 & 连接。

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

"""

import requests
import json
from datetime import datetime
import logging
import os
import ast
import time
import io

from notify import send

# 每日 9-20/7：从早上 9 点到晚上 8 点（20 时）之间，每 7 个小时执行一次， 开始旅行
# 9:25、16:25 执行，每日旅行两次应该足够用完耐力值了，可自行修改
'''
cron: 25 9-20/7 * * *
new Env("i茅台旅行")
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


# 获得旅行奖励
def travel_reward(device_id, mt_version, cookie, lat, lng):
    # 9-20点才能领取旅行奖励
    current_hour = datetime.now().hour
    if not (9 <= current_hour < 20):
        raise Exception("活动未开始，开始时间9点-20点")

    page_data = get_user_isolation_page_data(device_id, mt_version, cookie)
    logging.info(f"【旅行前】用户数据：")

    status = page_data.get("status")
    remain_chance = page_data.get("remainChance")
    energy_reward_value = page_data.get("energy_reward_value")
    energy = page_data.get("energy")
    end_time = page_data.get("end_time")

    # 打印旅行前获得的用户数据
    log_travel_status(page_data)

    # 如果存在未领取的耐力值奖励，则领取
    if energy_reward_value > 0:
        # 获取申购耐力值
        get_energy_award(cookie, device_id, mt_version, lat, lng)
        energy += energy_reward_value

    # 本月剩余旅行奖励
    current_period_can_convert_xmy_num = get_exchange_rate_info(
        device_id, mt_version, cookie)
    if current_period_can_convert_xmy_num <= 0:
        raise Exception("当月无可领取奖励，直接结束旅行。")
    logging.info(f"当月可领取小茅运数量：{current_period_can_convert_xmy_num}")

    # 未开始
    if status == 1:
        if energy < 100:
            raise Exception(f"无法旅行，耐力不足100, 当前耐力值:{energy}")
    # 进行中
    elif status == 2:
        formatted_date = datetime.fromtimestamp(
            end_time / 1000).strftime("%Y-%m-%d %H:%M:%S")
        raise Exception(f"旅行暂未结束,本次旅行结束时间:{formatted_date}")
    # 已完成
    if status == 3:
        travel_reward_xmy = get_xm_travel_reward(device_id, mt_version, cookie)
        logging.info(f"本次旅行将奖励小茅运：{travel_reward_xmy}")

        try:
            # 领取旅行获取的小茅运
            reward_result = receive_reward(device_id, lat, lng, cookie,
                                           mt_version)
            logging.info(f"领取小茅运结果：{reward_result}")
        except Exception as e:
            logging.error(f"领取小茅运失败: {e}")

        try:
            # 首次分享获取耐力
            share_result = share_reward(device_id, lat, lng, cookie,
                                        mt_version)
            logging.info(f"分享奖励结果：{share_result}")
        except Exception as e:
            logging.error(f"分享奖励失败: {e}")

        # 本次旅行奖励领取后, 当月实际剩余旅行奖励
        if travel_reward_xmy > current_period_can_convert_xmy_num:
            raise Exception("当月无可领取奖励，当月不再旅行")

    if remain_chance < 1:
        raise Exception("当日旅行次数已耗尽")
    else:
        # 小茅运旅行活动
        start_travel_result = start_travel(device_id, mt_version, cookie)
        time.sleep(2)
        page_data = get_user_isolation_page_data(device_id, mt_version, cookie)
        logging.info(f"【旅行后】用户数据：")
        log_travel_status(page_data)
        return start_travel_result


def log_travel_status(page_data):
    status = page_data.get("status")
    remain_chance = page_data.get("remainChance")
    xmy = page_data.get("xmy")
    energy = page_data.get("energy")
    energy_reward_value = page_data.get("energy_reward_value")

    logging.info(
        f"--- 当前旅行状态: {'未开始' if status == 1 else '进行中' if status == 2 else '已完成'}"
    )
    logging.info(f"--- 当日剩余旅行次数: {remain_chance}")
    logging.info(f"--- 小茅运: {xmy}")
    logging.info(f"--- 耐力值: {energy}")
    logging.info(f"--- 未领取的耐力值奖励: {energy_reward_value}")


# 领取旅行获取的小茅运
def receive_reward(device_id, lat, lng, cookie, mt_version):
    url = "https://h5.moutai519.com.cn/game/xmTravel/receiveReward"
    headers = generate_headers(device_id, mt_version, cookie, lat, lng)
    response = requests.post(url, headers=headers)
    body = response.json()
    if body.get("code") != 2000:
        raise Exception(body)
    return body


# 领取每日首次分享获取耐力
def share_reward(device_id, lat, lng, cookie, mt_version):
    url = "https://h5.moutai519.com.cn/game/xmTravel/shareReward"
    headers = generate_headers(device_id, mt_version, cookie, lat, lng)
    response = requests.post(url, headers=headers)
    body = response.json()
    if body.get("code") != 2000:
        raise Exception(body)
    return body


# 开始旅行
def start_travel(device_id, mt_version, cookie):
    url = "https://h5.moutai519.com.cn/game/xmTravel/startTravel"
    headers = generate_headers(device_id, mt_version, cookie)
    response = requests.post(url, headers=headers)
    body = response.json()
    if body.get("code") != 2000:
        raise Exception(f"开始旅行失败：{body.get('message')}")
    return json.dumps(body)


# 查询 可获取小茅运
def get_xm_travel_reward(device_id, mt_version, cookie):
    url = "https://h5.moutai519.com.cn/game/xmTravel/getXmTravelReward"
    headers = generate_headers(device_id, mt_version, cookie)
    response = requests.get(url, headers=headers)
    body = response.json()
    if body.get("code") != 2000:
        raise Exception(body.get("message"))
    # 例如 1.95，可能会返回 None
    travel_reward_xmy = body.get("data").get("travelRewardXmy")
    return travel_reward_xmy if travel_reward_xmy is not None else 0


# 获取用户数据，查询旅行状态、剩余可领取小茅运数量等
def get_user_isolation_page_data(device_id, mt_version, cookie):
    url = "https://h5.moutai519.com.cn/game/isolationPage/getUserIsolationPageData"
    headers = generate_headers(device_id, mt_version, cookie)
    params = {"__timestamp": int(datetime.now().timestamp())}
    response = requests.get(url, headers=headers, params=params)
    body = response.json()
    if body.get("code") != 2000:
        raise Exception(f"获取用户数据 失败:{body.get('message')}")

    data = body.get("data")
    # xmy: 小茅运值
    xmy = data.get("xmy")
    # energy: 耐力值
    energy = data.get("energy")
    xm_travel = data.get("xmTravel")
    energy_reward = data.get("energyReward")
    # status: 1. 未开始 2. 进行中 3. 已完成
    status = xm_travel.get("status")
    # travelEndTime: 旅行结束时间
    travel_end_time = xm_travel.get("travelEndTime")
    # remainChance 今日剩余旅行次数
    remain_chance = xm_travel.get("remainChance")
    # 可领取申购耐力值奖励
    energy_value = energy_reward.get("value")

    end_time = travel_end_time * 1000

    result = {
        "remainChance": remain_chance,
        "status": status,
        "xmy": xmy,
        "energy_reward_value": energy_value,
        "energy": energy,
        "end_time": end_time
    }
    return result


# 获取申购耐力值
def get_energy_award(cookie, device_id, mt_version, lat, lng):
    url = "https://h5.moutai519.com.cn/game/isolationPage/getUserEnergyAward"
    headers = generate_headers(device_id, mt_version, cookie, lat, lng)
    response = requests.post(url, headers=headers)
    body = response.text
    json_object = json.loads(body)
    if json_object.get("code") != 200:
        message = json_object.get("message")
        raise Exception(message)
    return body


# 获取本月剩余奖励耐力值
def get_exchange_rate_info(device_id, mt_version, cookie):
    url = "https://h5.moutai519.com.cn/game/synthesize/exchangeRateInfo"
    headers = generate_headers(device_id, mt_version, cookie)
    params = {"__timestamp": int(datetime.now().timestamp())}
    response = requests.get(url, headers=headers, params=params)
    body = response.json()
    if body.get("code") != 2000:
        raise Exception(body.get("message"))
    # 返回本月剩余奖励耐力值
    return body.get("data").get("currentPeriodCanConvertXmyNum")


if __name__ == "__main__":
    for user in users:
        logging.info('--------------------------')
        logging.info(f"用户：{user['PHONE_NUMBER']}，执行旅行")
        try:
            result = travel_reward(user['DEVICE_ID'], user['MT_VERSION'],
                                   user['COOKIE'], user['LAT'], user['LNG'])
            logging.info(f"用户：{user['PHONE_NUMBER']}，旅行成功，结果：{result}")
        except Exception as e:
            logging.error(f"用户：{user['PHONE_NUMBER']}，旅行失败: {e}")
        logging.info('--------------------------')

    logging.info("所有用户旅行完成")

    log_contents = log_stream.getvalue()
    send("i茅台旅行-日志：", log_contents)
