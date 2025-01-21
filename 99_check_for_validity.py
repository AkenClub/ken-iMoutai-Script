"""
99、检查 TOKEN、COOKIE 有效期

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
import jwt
import logging
import re

from notify import send

# 每日 18:05 定时检查并通知
'''
cron: 05 18 * * *
new Env("99_检查 TOKEN、COOKIE 有效期")
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


# 检查 JWT 有效期
def check_jwt(jwt_value):
    # 解码 JWT
    try:
        # 注意：此处的密钥应与生成 JWT 时使用的密钥一致
        decoded = jwt.decode(jwt_value, options={"verify_signature": False})

        # 获取 exp 时间戳
        exp_timestamp = decoded.get("exp")
        if exp_timestamp:
            # 转换为日期
            exp_date = datetime.datetime.fromtimestamp(
                exp_timestamp, tz=datetime.timezone.utc)

            # 获取当前时间
            current_date = datetime.datetime.now(datetime.timezone.utc)

            exp_date_str = exp_date.strftime('%Y-%m-%d %H:%M:%S')

            # 判断是否过期
            if current_date > exp_date:
                logging.info(
                    f"⚠️ TOKEN 已过期: {exp_date_str}，请重新执行 第1、2步 脚本获取最新 TOKEN、COOKIE 值。"
                )
            else:
                logging.info(f"✅ TOKEN 有效: 过期时间为 {exp_date_str}")
        else:
            logging.warning("⚠️ TOKEN 中没有 'exp' 字段")
    except jwt.DecodeError:
        logging.error("⚠️ TOKEN 解析失败")


# 获取用户信息 测试 API 是否调用成功
def check_api(cookie, device_id, mt_version, lat, lng):
    global DEBUG
    try:
        timestamp = str(
            int(time.mktime(datetime.date.today().timetuple())) * 1000)
        url = f"https://h5.moutai519.com.cn/game/userinfo?__timestamp={timestamp}&"
        headers = generate_headers(device_id, mt_version, cookie, lat, lng)

        response = requests.post(url, headers=headers)
        progress_data = json.loads(response.text)
        if progress_data.get("code") != 2000:
            message = progress_data.get("message")
            raise Exception({message})
        if DEBUG:
            logging.info(f"✅ 测试通过: {progress_data}")
            return
        logging.info("✅ 测试通过")
    except Exception as e:
        logging.error(f"🚫 测试不通过: {e}")
        logging.error(f"⚠️ TOKEN、COOKIE 值真的失效啦！建议及时更新！否则无法正常预约和旅行咯！")


if __name__ == "__main__":

    logging.info('--------------------------')
    logging.info(
        '💬 TOKEN 有效期时间不一定准确，一般上下浮动 6 小时，以真实 API 连接的结果为准。同时建议临近有效期时手动更新 TOKEN、COOKIE，不用等到过期再去更新。'
    )

    for user in users:
        try:
            logging.info('--------------------------')
            logging.info(f"📞 用户 {user['PHONE_NUMBER']} 开始检查")
            logging.info(f"🔍 开始检查 TOKEN 有效期")
            check_jwt(user['TOKEN'])

            logging.info(f"🔍 开始测试真实 API 连接")
            check_api(user['COOKIE'], user['DEVICE_ID'], user['MT_VERSION'],
                      user['LAT'], user['LNG'])
        except Exception as e:
            logging.error(
                f"🚫 用户 {user['PHONE_NUMBER']} 检查异常: {e}，请手动执行 4、5 脚本，检查 TOKEN、COOKIE 是否过期"
            )

    logging.info('--------------------------')
    logging.info("✅ 所有用户检查完成")

    log_contents = log_stream.getvalue()
    send("i茅台 TOKEN、COOKIE 有效期检查日志：", log_contents)
