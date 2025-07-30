"""
98、查询申购结果

*** 需要安装依赖 PyJWT ***

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
import os
import ast
import io
import logging
import re

from notify import send

# 每日 18:03 定时查询并通知
'''
cron: 03 18 * * *
new Env("98_查询申购结果")
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

# 调试模式
DEBUG = False

# 读取 KEN_IMAOTAI_ENV 环境变量
KEN_IMAOTAI_ENV = os.getenv('KEN_IMAOTAI_ENV', '')

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
                    if SHOP_MODE not in ['NEAREST', 'INVENTORY', '']:
                        raise Exception(
                            "🚫 店铺缺货模式值错误，请检查 SHOP_MODE 值是否为 NEAREST（<默认> 距离最近） 或 INVENTORY（库存最多） 或 空字符串（不选择其他店铺）"
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
            # 检查字段是否完整且有值，不检查 SHOP_MODE、PROVINCE、CITY 字段（PROVINCE 和 CITY 用于 SHOP_MODE 里，而 SHOP_MODE 可选）
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


# 生成请求头
def generate_headers(device_id, mt_version, token):
    mt_k = f'{int(time.time() * 1000)}'
    headers = {
        "User-Agent": "iOS;16.3;Apple;?unrecognized?",
        "MT-Device-ID": device_id,
        "MT-APP-Version": mt_version,
        'MT-Token': token,
        'MT-Network-Type': 'WIFI',
        'MT-User-Tag': '0',
        'MT-K': mt_k,
        'MT-Bundle-ID': 'com.moutai.mall',
        'MT-R': 'clips_OlU6TmFRag5rCXwbNAQ/Tz1SKlN8THcecBp/HGhHdw==',
        'MT-SN': 'clips_ehwpSC0fLBggRnJAdxYgFiAYLxl9Si5PfEl/TC0afkw='
    }
    return headers


# 查询申购结果
def check_reservation_result(token, device_id, mt_version):
    global DEBUG
    try:
        url = f"https://app.moutai519.com.cn/xhr/front/mall/reservation/list/pageOne/queryV2"
        headers = generate_headers(device_id, mt_version, token)

        response = requests.get(url, headers=headers)
        resultData = json.loads(response.text)
        resultCode = resultData.get("code")
        if resultCode == 4820:
            message = resultData.get("data", {}).get("updateDesc", "API 可能限制了 APP 版本，可以尝试重新生成环境变量")
            raise Exception(f"({resultCode}){message}")
        elif resultCode != 2000:
            message = resultData.get("message")
            raise Exception(f"({resultCode}){message}")

        # 处理预约结果
        reservations = resultData.get("data", {}).get("reservationItemVOS", [])
        if not reservations:
            logging.info("🚫 暂无申购记录")
            return

        # 获取当天日期
        today = datetime.datetime.now().date()
        today_str = today.strftime("%Y-%m-%d")
        logging.info(f"📅 今天的日期是: {today_str}")

        for item in reservations:
            # 获取预约时间
            reservation_time = datetime.datetime.fromtimestamp(
                item.get("reservationTime") / 1000).date()
            # 筛选今天预约的商品
            if reservation_time == today:
                status_text = {
                    0: "⌛️ 静候申购结果",
                    1: "❌ 申购失败",
                    2: "🎉 申购成功"
                }.get(item.get("status"), "未知状态")

                session_name = f"[{item.get('sessionName', '')}]" if item.get(
                    'sessionName') else ""
                item_name = item.get("itemName", "")
                item_id = item.get("itemId", "")

                # 输出结果
                logging.info(
                    f"🍺 {session_name}[{item_id}] {item_name}：{status_text}。")

    except Exception as e:
        logging.error(f"🚫 查询申购结果失败: {e}")


if __name__ == "__main__":

    logging.info('--------------------------')
    logging.info("💬 申购成功后将以短信形式通知您，请您在申购成功次日18:00前选择支付方式，并根据提示完成支付。")
    for user in users:
        try:
            logging.info('--------------------------')
            logging.info(f"📞 用户 {user['PHONE_NUMBER']} 开始查询申购结果")

            check_reservation_result(user['TOKEN'],
                                     user['DEVICE_ID'], user['MT_VERSION'])
        except Exception as e:
            logging.error(
                f"🚫 用户 {user['PHONE_NUMBER']} 查询异常: {e}，请到 App 上查看申购结果。")

    logging.info('--------------------------')
    logging.info("✅ 所有用户查询完成")

    log_contents = log_stream.getvalue()
    send("i茅台 查询申购结果日志：", log_contents)
