import time
import hashlib
import requests
import json
import logging
"""
2、登录，获取 USER_ID、TOKEN、COOKIE 等数据

上一步获取到验证码后，根据上一步输出的版本号和设备ID，填入下面信息进行登录请求，
运行后，输出用户信息，并记录用于后续预约。

"""
# ------ 填写以下 4 个变量值 --------

# 手机号码，和上一步的手机号码一致
PHONE_NUMBER = ''
# 验证码，填写收到的验证码
CODE = ""
# 设备 ID，和上一步的设备 ID 一致
DEVICE_ID = ""
# 版本号，和上一步的版本号一致
MT_VERSION = ""

# --------------------
'''
cron: 1 1 1 1 *
new Env("2_登录")
'''

# ***** 以下内容不用动 *****

SALT = "2af72f100c356273d46284f6fd1dfc08"
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


def signature(content, time):
    text = SALT + content + str(time)
    md5 = hashlib.md5(text.encode()).hexdigest()
    return md5


def login(mobile, code, device_id, mt_version):
    cur_time = int(time.time() * 1000)
    data = {
        "mobile": mobile,
        "vCode": code,
        "md5": signature(mobile + code, cur_time),
        "timestamp": str(cur_time),
        "MT-APP-Version": mt_version
    }
    headers = {
        "MT-Device-ID": device_id,
        "MT-APP-Version": mt_version,
        "User-Agent": "iOS;16.3;Apple;?unrecognized?",
        "Content-Type": "application/json"
    }
    url = "https://app.moutai519.com.cn/xhr/front/user/register/login"
    response = requests.post(url, headers=headers, data=json.dumps(data))
    json_response = response.json()

    # 输出登录请求的返回结果
    logging.info(f"「登录请求返回」：{json.dumps(json_response)}")

    if json_response.get("code") == 2000:
        logging.info("「登录请求-成功」")
        user_data = json_response.get("data", {})
        filtered_data = {
            k: v
            for k, v in user_data.items() if k not in
            ["idType", "verifyStatus", "idCode", "birthday", "userTag"]
        }
        return filtered_data
    else:
        logging.error("「登录请求-失败」")
        raise Exception("登录失败，本地错误日志已记录")


if __name__ == "__main__":
    # 判断入参
    if not PHONE_NUMBER or not CODE or not DEVICE_ID or not MT_VERSION:
        logging.error("「登录请求-失败」：缺少必要参数")
        raise Exception("缺少必要参数")

    result = login(PHONE_NUMBER, CODE, DEVICE_ID, MT_VERSION)
    logging.info(f"「结果：用户信息」：{json.dumps(result)}")

    logging.info("****************************")
    logging.info("记录以下信息用于后续预约：")
    logging.info(f"手机号码 - PHONE_NUMBER：{PHONE_NUMBER}")
    logging.info(f"设备ID - DEVICE_ID：{DEVICE_ID}")
    logging.info(f"版本号 - MT_VERSION：{MT_VERSION}")
    logging.info(f"用户ID - USER_ID：{result['userId']}")
    logging.info(f"Token - TOKEN：{result['token']}")
    logging.info(f"Cookie - COOKIE：{result['cookie']}")
