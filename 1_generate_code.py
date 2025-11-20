import time
import hashlib
import uuid
import requests
import logging
import json
import re
"""
1、获取登录验证码，获取 DEVICE_ID、MT_VERSION 等数据
"""

# ------ 填写以下 1 个变量值 --------

# 填写手机号码，收到验证码后在 login.py 中填写验证码
PHONE_NUMBER = ""
# --------------------

# -------- 非必填 ------------
# 设备 ID，留空则自动生成；
# 若是想要保留之前的设备 ID，可以在这里填写之前的值，则不会生成新的设备 ID。
DEVICE_ID_DEFAULT = ""
# --------------------
'''
cron: 1 1 1 1 *
new Env("1_获取登录验证码")
'''

# ***** 以下内容不用动 *****

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

SALT = "2af72f100c356273d46284f6fd1dfc08"


def get_device_id():
    if DEVICE_ID_DEFAULT:
        return DEVICE_ID_DEFAULT
    return str(uuid.uuid4())


def signature(content, time):
    text = SALT + content + str(time)
    md5 = hashlib.md5(text.encode()).hexdigest()
    return md5


def send_code(mobile, device_id, mt_version):
    cur_time = int(time.time() * 1000)
    data = {
        "mobile": mobile,
        "md5": signature(mobile, cur_time),
        "timestamp": str(cur_time)
    }
    headers = {
        "MT-Device-ID": device_id,
        "MT-APP-Version": mt_version,
        "User-Agent": "iOS;16.3;Apple;?unrecognized?",
        "Content-Type": "application/json"
    }
    url = "https://app.moutai519.com.cn/xhr/front/user/register/vcode"
    response = requests.post(url, headers=headers, data=json.dumps(data))
    json_response = response.json()

    if json_response.get("code") == 2000:
        logging.info(f"「发送验证码返回」：{json.dumps(json_response)}")
        return True
    else:
        logging.error(f"「发送验证码-失败」：{json.dumps(json_response)}")
        raise Exception("发送验证码错误")


def get_mt_version():
    url = "https://apps.apple.com/cn/app/i%E8%8C%85%E5%8F%B0/id1600482450"
    with requests.get(url) as response:
        response.encoding = 'utf-8'  # 确保使用正确的编码
        html_content = response.text

    # 使用正则表达式匹配版本号（已过时，这里只是作为兼容，避免又使用回这种规则）
    pattern = re.compile(r'new__latest__version">(.*?)</p>', re.DOTALL)
    match = pattern.search(html_content)

    if not match:
        # 新的匹配方式
        pattern = re.compile(r'class="metadata[^"]*">\s*<h4[^>]*>(.*?)</h4>', re.DOTALL)
        match = pattern.search(html_content)

    if match:
        mt_version = match.group(1).strip().replace('版本 ', '')  # 去掉前后的空白字符
        return mt_version

    raise Exception("获取版本号失败")


if __name__ == "__main__":
    # 判断 PHONE_NUMBER 是否为空
    if not PHONE_NUMBER:
        logging.error("「发送验证码-失败」：请填写手机号码")
        raise Exception("请填写手机号码")

    try:
        mt_version = get_mt_version()
        device_id = get_device_id()

        # 发送验证码
        if send_code(PHONE_NUMBER, device_id, mt_version):
            logging.info(f"{PHONE_NUMBER}：验证码发送成功，请注意查收!")

            logging.info("****************************")
            logging.info("记录以下信息用于后续登录：")
            logging.info(f"设备ID - DEVICE_ID：{device_id}")
            logging.info(f"版本号 - MT_VERSION：{mt_version}")
    except Exception as e:
        logging.error(e)
