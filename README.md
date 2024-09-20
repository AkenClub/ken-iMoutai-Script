# ken-iMoutai-Script

`ken-iMoutai-Script` 是一个青龙脚本，旨在自动化完成 i茅台的预约申购、登录、短信验证码处理、耐力值和小茅运领取、旅行功能以及自动化选择店铺等功能。



## 功能

- **登录**
- **短信验证码**
- **预约申购**
- **耐力值和小茅运领取**
- **旅行功能**
- **自动化选择店铺** 🆕




> **青龙版本**：**正式版 v2.17.10**，已知 2.13.8 版本会运行报错，升级版本可以解决。

## 使用方法

> 第 1、2、3 步都是修改**脚本里面**开头的变量值，然后手动运行一下，查看日志并且记录所需的数据。
>
> 之后将上述步骤获得的数据组成**青龙面板里面**的环境变量`KEN_IMAOTAI_ENV`，就能定时执行第 4、5 步的脚本了。
>
> TOKEN 有效期一般一个月，过期了重新执行一下第 1、2 步拿到数据修改`KEN_IMAOTAI_ENV`值即可。

0. **拉取仓库：**

     在青龙面板-订阅管理-创建订阅，复制以下命令到`名称`输入框即可自动配置订阅链接，定时规则自定，例如`0 5 * * *`，添加完成后点击列表行`运行`，脚本会自动添加到`定时任务`。

     ```
     ql repo https://github.com/AkenClub/ken-iMoutai-Script.git
     ```

1. **获取登录验证码**

   运行 `1_generate_code.py` 脚本以获取登录验证码，并记录设备ID、版本号等数据。

   - （脚本文件内）变量配置：

   ```
   # 填写手机号码，收到验证码后在 2_login.py 中填写验证码
   PHONE_NUMBER = ''
   ```

2. **登录**

   使用获取到的验证码、设备ID 和版本号进行登录请求，输出用户信息并记录以备后续使用。请运行 `2_login.py` 脚本。

   - （脚本文件内）变量配置：

   ```
   # 手机号码，和上一步的手机号码一致
   PHONE_NUMBER = ''
   # 验证码，填写收到的验证码
   CODE = ""
   # 设备 ID，和上一步的设备 ID 一致
   DEVICE_ID = ""
   # 版本号，和上一步的版本号一致
   MT_VERSION = ""
   ```

3. **查询可预约商品和售卖商店**

   运行 `3_retrieve_shop_and_product_info.py` 脚本查询可预约的商品和商店信息，获取 SHOP_ID、LAT、LNG 、省份、城市 等数据。

   - （脚本文件内）变量配置：

   ```
   # 省份
   PROVINCE_NAME = "广西壮族自治区"
   # 城市
   CITY_NAME = "南宁市"
   ```

4. **预约商品**

   每日 9:10 开始预约，并根据青龙面板的通知渠道进行通知。请运行 `4_reserve_product.py` 脚本。

   - **配置环境变量 `KEN_IMAOTAI_ENV`：**

     ~~内容格式为：    PHONE_NUMBER$USER_ID$DEVICE_ID$MT_VERSION$PRODUCT_ID_LIST$SHOP_ID$LAT$LN G$TOKEN$COOKIE~~

     ~~**解释**：手机号码$用户ID$设备ID$版本号$商品ID列表$店铺ID$纬度$经度$TOKEN$COOKIE~~
     
     **内容格式为**：PHONE_NUMBER$USER_ID$DEVICE_ID$MT_VERSION$PRODUCT_ID_LIST$SHOP_ID^SHOP_MODE^PROVINCE^CITY$LAT$LNG$TOKEN$COOKIE
     
     **解释**：手机号码$用户ID$设备ID$版本号$商品ID列表$店铺ID^店铺缺货时自动采用的模式^省份^城市$纬度$经度$TOKEN$COOKIE
     
     
     
     **多个用户时使用 & 连接**。
     
     
     
     常量。
     - PHONE_NUMBER: 用户的手机号码。            --- 自己手机号码
     
     - CODE: 短信验证码。                                         --- 运行 1_generate_code.py 获取
     
     - DEVICE_ID: 设备的唯一标识符。                     --- 运行 1_generate_code.py 获取
     
     - MT_VERSION: 应用程序的版本号。                 --- 运行 1_generate_code.py 获取
     
     - USER_ID: 用户的唯一标识符。                          --- 运行 2_login.py 获取
     
     - TOKEN: 用于身份验证的令牌。                          --- 运行 2_login.py 获取
     
     - COOKIE: 用于会话管理的Cookie。                     --- 运行 2_login.py 获取
     
     - PRODUCT_ID_LIST: 商品ID列表，表示用户想要预约的商品。--- 运行 3_retrieve_shop_and_product_info.py 获取
     
     - SHOP_ID: 店铺的唯一标识符。                       --- 运行 3_retrieve_shop_and_product_info.py 获取
     
       ​                 可**设置为 AUTO**，则根据 SHOP_MODE 的值来选择店铺 ID。
     
     - SHOP_MODE：店铺缺货模式，可选值为 **NEAREST**（距离最近）或 **INVENTORY**（库存最多）。设置该值时，需要同时设置 PROVINCE 和 CITY。
     
       ​                 非必填，但 SHOP_ID 设置 AUTO 时为必填，需要同时设置 SHOP_MODE、PROVINCE 和 CITY。
     
     - PROVINCE: 用户所在的省份。                        --- 与 3_retrieve_shop_and_product_info.py 填写的省份一致
     
       ​                非必填，但 SHOP_MODE 设置为 NEAREST 或 INVENTORY 时为必填。
     
     - CITY: 用户所在的城市。                                  --- 与 3_retrieve_shop_and_product_info.py 填写的城市一致
     
       ​                非必填，但 SHOP_MODE 设置为 NEAREST 或 INVENTORY 时为必填。
     
     - LAT: 用户所在位置的纬度。                           --- 运行 3_retrieve_shop_and_product_info.py 获取
     - LNG: 用户所在位置的经度。                          --- 运行 3_retrieve_shop_and_product_info.py 获取
     
     **注意**：PRODUCT_ID_LIST 里面的 ID 值需要**用单引号**，整个环境变量里的标点符号都是用**英文符号**。

5. **旅行 & 获取小茅运、首次分享奖励**

   每日从早上 9 点到晚上 8 点之间，每 7 个小时执行一次旅行任务。请运行 `5_travel_and_rewards.py` 脚本。9:15、16:15 执行，每日旅行两次应该足够用完耐力值了，可自行修改。

   - **配置环境变量 `KEN_IMAOTAI_ENV`：同上**

6. **配置通知**

   在控制面板 - 配置文件 - 右上角确定是 `config.sh` 里，例如配置企业微信机器人，则填写 `QYWX_KEY` 的值即可。

   不需要通知的内容末尾添加随机句子，可以配置
   
   ```sh
   ## 禁用一言（随机句子）
   export HITOKOTO="false"
   ```



## 环境变量示例

### 示例 1：使用 `AUTO` + `NEAREST` 模式自动选择距离最近的店铺

**注意**：设置 SHOP_MODE 为  NEAREST 值后，需要**同时设置** 省份(PROVINCE) 和 城市(CITY) 的值

```
KEN_IMAOTAI_ENV="13812345678$9876543210$abcd1234-5678-90ef-ghij-klmn01234567$1.8.0$['12345', '54321']$AUTO^NEAREST^北京市^北京市$39.904202$116.407394$eyJhbGciOiJIUzI1$eyJzZXNzaW9uX2lk"
```

**说明**：该配置会根据用户所在位置北京市，自动选择距离最近的店铺进行商品预订。



### 示例 2：使用  `AUTO` + `INVENTORY` 模式选择库存最多的店铺

**注意**：设置 SHOP_MODE 为  INVENTORY 值后，需要**同时设置** 省份(PROVINCE) 和 城市(CITY) 的值

```
KEN_IMAOTAI_ENV="13987654321$1029384756$abcd-1234-efgh-5678-ijkl90123456$1.8.1$['98765', '56789']$AUTO^INVENTORY^上海市^上海市$31.230391$121.473701$eyJzZXNzaW9uIjoxMjM0$eyJ1c2VyX2Nvb2tpZQ"
```

**说明**：此配置在上海市自动选择库存最多的店铺来完成预订。



### 示例 3：指定店铺ID且不使用自动选择模式

**注意**：可能会出现“商品ID XXX 申购失败:当前选择的门店不参与本场申购，请选择另外的门店申购”情况，建议设置 SHOP_MODE、PROVINCE  和 CITY 值，在店铺缺货时根据指定模式自动选择店铺。

```
KEN_IMAOTAI_ENV="13656789012$1122334455$1234abcd-5678-efgh-9012-ijkl34567890$1.9.0$['11223']$45678$22.543096$114.057865$eyJzdG9yZV9jb29raWVfZGF0YQ$eyJ0b2tlbiI6"
```

**说明**：此配置使用用户指定的店铺 ID `45678`，无自动选择店铺。



### 示例 4：多个用户配置

使用 **&** 连接。

```
KEN_IMAOTAI_ENV="13876543210$9988776655$abcd1234-5678-efgh-ijkl-901234567890$1.8.2$['10999']$AUTO^INVENTORY^广东省^广州市$23.129163$113.264435$eyJzaWduZWRfY29va2ll$eyJ0b2tlbiIgY2hlY2s&13965432108$7766554433$dcba4321-8765-ghij-klmn-098765432109$1.9.0$['10500']$45678^NEAREST^江苏省^南京市$32.060255$118.796877$eyJ1c2VyX2Nvb2tpZQ$eyJvcGVuX3Nlc3Npb25fa2V5"
```

**说明**：该配置包含**两个**用户的信息：第一个用户在广东省广州市使用 `AUTO` +  `INVENTORY` 模式自动选择库存最多的店铺；第二个用户在江苏省南京市指定店铺 ID `45678`，使用 `NEAREST` 模式选择距离最近的店铺。



## 常见问题

1. 缺少依赖，`ModuleNotFoundError: No module named 'Crypto'`。

   **解决**：单独安装 `pycryptodome` 依赖

   ```shell
   docker exec -it 青龙容器名 /bin/bash
   ```

   在容器内使用 pip 安装 pycryptodome：

   ```shell
   pip install pycryptodome
   ```

2. 运行日志显示`申购完成`，但是在 i茅台 APP 上的预约申购页面还是显示 `预约申购` 按钮。

   **解决**：如果继续点击`预约申购`，最后会提示你已经申购的了。

   也可以在 i茅台APP - 我的 - 我的申购单 里面能看到`静候申购结果`。 有小伙伴已经申购成功，证明该方式可行。



## 计划

- ~~增加累计申购N天的小茅运检测和领取功能~~  [`ad4101c`](https://github.com/AkenClub/ken-iMoutai-Script/commit/ad4101c51a73f2b7336f600386de85437be46774) 已完成，需重新拉库
- ~~增加 7 日连续申购领取小茅运奖励功能~~ [`673dda4`](https://github.com/AkenClub/ken-iMoutai-Script/commit/673dda46bdb162c62742775b5c9537bede6499ea) 已完成，需重新拉库
- ~~增加判断目标店铺不支持某个商品预约时，自动选择可预约的其他店铺~~[81971ad](https://github.com/AkenClub/ken-iMoutai-Script/commit/81971add48f18beab5f5ce15d8fa554afcb6c697) 已完成，需重新拉库。环境变量做了兼容，建议**设置** 自动化选择店铺 相关变量值
- 增加周末欢乐购



## 参考与致谢

本项目参考了以下两个项目：

- [yize8888/maotai](https://github.com/yize8888/maotai) - 提供了实现思路。
- [oddfar/campus-imaotai](https://github.com/oddfar/campus-imaotai) - 提供了基础实现。

感谢这些项目的作者和贡献者，他们的工作为本项目提供了宝贵的参考和灵感。

>  `yize8888/maotai` 项目是青龙脚本，但没有登录、验证码获取、店铺信息、旅行相关等功能，使用时候需要额外抓包；
>
> `oddfar/campus-imaotai` 虽然功能齐全，但不是青龙脚本，对于原本已经运行青龙面板的用户来说，增加了额外的运行压力。
>
> 本项目将两者的优缺点融合在一起，主要用 python 重写了 oddfar/campus-imaotai 相关 Java 接口。



## 免责声明

本项目涉及抓取接口数据，仅用于学习和交流目的。请注意以下几点：

1. **合法性和合规性**： 使用本脚本时，请确保遵守所有相关法律法规以及服务条款。本项目的使用可能涉及到法律风险，用户需要对使用本脚本的行为负责。
2. **数据隐私**： 本脚本涉及对接口数据的抓取，用户需自行保证对其账号、数据和隐私的保护，避免泄露敏感信息。
3. **风险提示**： 由于抓取接口数据可能会受到系统限制或变更，脚本的正常运行和功能实现无法得到保证。使用本项目的风险由用户自行承担。
4. **第三方服务**： 本项目的部分功能可能依赖于第三方服务或接口，这些服务的变更或不可用可能会影响脚本的正常工作。
5. **学习和交流**： 本项目仅用于学习和交流目的，旨在帮助用户了解接口抓取和自动化处理的技术。请勿用于商业用途或其他非法活动。
6. **责任声明**： 本项目作者不对因使用本脚本而产生的任何直接或间接损失负责。请用户在使用前充分理解相关风险，并确保合法合规使用。



## 许可证

本项目使用 [Apache-2.0 许可证](LICENSE) 进行许可。有关更多详细信息，请参阅 `LICENSE` 文件。
