import logging
import requests
import time
import datetime
"""
3、查询可预约的商品 和 售卖商店，获取 SHOP_ID、LAT、LNG 等数据

如果省份城市填写有问题，可以直接查看这个网址的 json 内容，找到自己的想要预约的商店信息。也可找到正确的省份城市信息后填入下面变量值运行脚本获取完整数据。
https://resource.moutai519.com.cn/mt-resource/resource/myserviceshops/1726025401183/myserviceshops.json
（若过期无法访问，可参考脚本里 get_shop_info 函数逻辑，查看 ["data"]["myserviceshops"]["url"] 获取最新网址）
"""

# ------ 填写以下 2 个变量值 --------

# 示例调用，省份和市区需要填写完整，
# 省份
PROVINCE_NAME = "广西壮族自治区"
# 城市
CITY_NAME = "南宁市"

# --------------------

# ***** 以下内容不用动 *****

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


# 获取可预约的商品信息
def get_item_info():
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
    # 提取itemCode和title
    item_list = data["data"]["itemList"]
    result = [{
        "itemCode": item["itemCode"],
        "title": item["title"]
    } for item in item_list]

    return {"sessionId": sessionId, "itemList": result}


# 获取售卖商店信息
def get_shop_info(province_name, city_name):
    # 第一步：获取myserviceshops的URL
    api_url = "https://static.moutai519.com.cn/mt-backend/xhr/front/mall/resource/get"
    response = requests.get(api_url)
    data = response.json()

    if data["code"] != 2000:
        raise Exception("获取资源信息失败")

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
                "shopId": shop_info["shopId"],
                "fullAddress": shop_info["fullAddress"],
                "cityName": shop_info["cityName"],
                "provinceName": shop_info["provinceName"]
            })

    return result


if __name__ == "__main__":
    # 获取商店信息
    if not PROVINCE_NAME or not CITY_NAME:
        logging.error("「获取商店信息-失败」：缺少必要参数")
        raise Exception("缺少必要参数")

    logging.info(f"「获取商店信息-开始」：{PROVINCE_NAME} - {CITY_NAME}")
    shop_info = get_shop_info(PROVINCE_NAME, CITY_NAME)

    logging.info(f"「查找到的商店信息」：")
    logging.info("-------------------------")
    for shop in shop_info:
        logging.info(f"店铺名称: {shop['name']}")
        logging.info(f"店铺ID: {shop['shopId']}")
        logging.info(f"地址: {shop['fullAddress']}")
        logging.info(f"纬度: {shop['lat']}")
        logging.info(f"经度: {shop['lng']}")
        logging.info("-------------------------")
    logging.info(f"**** 请自行选择上面一个商店，可以选离你最近的，想要选出货量最多的店，可以上 i茅台APP 查看再选择 ****")

    logging.info("-------------------------")

    # 获取可以预约的商品信息
    result = get_item_info()
    logging.info(
        f"获取到 SessionId(可以理解为申购活动批次，每天都会变化，一般+1): {result['sessionId']}")
    for item in result['itemList']:
        logging.info(
            f"获取到可预约商品：itemCode: {item['itemCode']}, title: {item['title']}")

    logging.info("****************************")
    logging.info("记录以下信息用于后续预约：")
    logging.info(f"店铺 ID - SHOP_ID：对应 shopId 字段")
    logging.info(f"纬度 - LAT：对应 lat 字段")
    logging.info(f"经度 - LNG：对应 lng 字段")
    logging.info(
        f"需要预约的商品 ID(对应 itemCode) - PRODUCT_ID_LIST，例如：['10941', '10923', '2478', '10942']"
    )
