# ken-iMoutai-Script

`ken-iMoutai-Script` 是一个青龙脚本，旨在自动化完成 i 茅台的预约申购、登录、短信验证码处理、耐力值和小茅运领取、旅行、周末欢乐购以及自动化选择店铺等功能。

## 功能

- **登录**
- **短信验证码**
- **预约申购**
- **耐力值和小茅运领取**
- **旅行功能**
- **自动化选择店铺**
- **定时检查 TOKEN 有效期**
- **周末欢乐购**
- **查询申购结果**
- **配套前端界面生成环境变量**
- **"小茅好运"专场** 🆕

> **青龙版本**：**正式版 v2.17.10**

## 环境变量生成

### 方式 1：环境变量生成助手

需要自己部署，支持 docker。
项目地址：https://github.com/AkenClub/iMoutaiEnvGenerator

![首页界面](https://raw.githubusercontent.com/AkenClub/iMoutaiEnvGenerator/main/src/assets/md/img_home.png)

### 方式 2：手动生成

直接在青龙面板中修改**脚本中的**变量值进行调试即可，免部署。

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

   运行 `1_generate_code.py` 脚本以获取登录验证码，并记录设备 ID、版本号等数据。

   - （脚本文件内）变量配置：

   ```
   # 填写手机号码，收到验证码后在 2_login.py 中填写验证码
   PHONE_NUMBER = ''
   ```

2. **登录**

   使用获取到的验证码、设备 ID 和版本号进行登录请求，输出用户信息并记录以备后续使用。请运行 `2_login.py` 脚本。

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

   每日 9:10 开始预约，并根据青龙面板的通知渠道进行通知。对应 `4_reserve_product.py` 脚本。

   - **配置环境变量 `KEN_IMAOTAI_ENV`：**

     > 在旧版本青龙（例如 v2.13.8）中，使用 $ 作为分隔符时会出现解析环境变量失败，此时可以把 `$` 分隔符换为 `#` 作为分隔符。
     >
     > 📣 怕出错？**建议直接使用 `#` 作为分隔符即可** (2024-10-15 更新支持)。

     **内容格式为**：PHONE_NUMBER$USER_ID$DEVICE_ID$MT_VERSION$PRODUCT_ID_LIST$SHOP_ID^SHOP_MODE^PROVINCE^CITY$LAT$LNG$TOKEN$COOKIE

     **解释**：手机号码$用户ID$设备 ID$版本号$商品 ID 列表$店铺ID^店铺缺货时自动采用的模式^省份^城市$纬度$经度$TOKEN$COOKIE

     **多个用户时使用 & 连接**。

     常量。

     - PHONE_NUMBER: 用户的手机号码。 --- 自己手机号码

     - CODE: 短信验证码。 --- 运行 1_generate_code.py 获取

     - DEVICE_ID: 设备的唯一标识符。 --- 运行 1_generate_code.py 获取

     - MT_VERSION: 应用程序的版本号。 --- 运行 1_generate_code.py 获取

     - USER_ID: 用户的唯一标识符。 --- 运行 2_login.py 获取

     - TOKEN: 用于身份验证的令牌。 --- 运行 2_login.py 获取

     - COOKIE: 用于会话管理的 Cookie。 --- 运行 2_login.py 获取

     - PRODUCT_ID_LIST: 商品 ID 列表，表示用户想要预约的商品。--- 运行 3_retrieve_shop_and_product_info.py 获取

     - SHOP_ID: 店铺的唯一标识符。 --- 运行 3_retrieve_shop_and_product_info.py 获取

       ​ 可**设置为 AUTO**，则根据 SHOP_MODE 的值来选择店铺 ID。

     - SHOP_MODE：店铺缺货模式，可选值为 **NEAREST**（距离最近）或 **INVENTORY**（库存最多）。设置该值时，需要同时设置 PROVINCE 和 CITY。

       ​ 非必填，但 SHOP_ID 设置 AUTO 时为必填，需要同时设置 SHOP_MODE、PROVINCE 和 CITY。

     - PROVINCE: 用户所在的省份。 --- 与 3_retrieve_shop_and_product_info.py 填写的省份一致

       ​ 非必填，但 SHOP_MODE 设置为 NEAREST 或 INVENTORY 时为必填。

     - CITY: 用户所在的城市。 --- 与 3_retrieve_shop_and_product_info.py 填写的城市一致

       ​ 非必填，但 SHOP_MODE 设置为 NEAREST 或 INVENTORY 时为必填。

     - LAT: 用户所在位置的纬度。 --- 运行 3_retrieve_shop_and_product_info.py 获取
     - LNG: 用户所在位置的经度。 --- 运行 3_retrieve_shop_and_product_info.py 获取

     **注意**：PRODUCT_ID_LIST 里面的 ID 值需要**用单引号**，整个环境变量里的标点符号都是用**英文符号**。

5. **旅行 & 获取小茅运、首次分享奖励**

   每日 9: 12 执行一次旅行任务。对应 `5_travel.py` 脚本。

   - **配置环境变量 `KEN_IMAOTAI_ENV`：同上**

6. **配置通知**

   在控制面板 - 配置文件 - 右上角确定是 `config.sh` 里，例如配置企业微信机器人，则填写 `QYWX_KEY` 的值即可。

   不需要通知的内容末尾添加随机句子，可以配置

   ```sh
   ## 禁用一言（随机句子）
   export HITOKOTO="false"
   ```

7. **定时检查 TOKEN 有效期**

   **需要安装依赖 PyJWT**：面板 - 依赖管理 - 右上角新建依赖 - 类型 python3 - 拆分 否 - 名称 - PyJWT - 确定。

   等安装完成刷新页面去运行一次脚本 `99_check_for_validity.py`，测试没问题后，脚本会每天定时在 18:05 自动执行并通知。

8. **周末欢乐购**

   直接复用 日常预约商品的环境变量，找出 周末欢乐购 可预约的商品 和 日常预约的商品重合的商品 ID 进行预约。即 日常预约环境变量设置 A、B、C 商品，欢乐购可预约 B、D 商品，则脚本会自动筛选重合的 B 商品预约，D 商品不预约。

   店铺 ID 和 缺货店铺相关配置沿用日常预约的。

9. **查询申购结果**

   每日 18:03 定时查询并通知。

## 环境变量示例

**注意：编辑变量弹窗里，`名称`的输入框内填固定值**：KEN_IMAOTAI_ENV，**`值`的输入框填真实信息**：13312345678$..$..。下方示例中只展示`值`部分。

1. 使用 `指定店铺ID` + `NEAREST` 模式自动选择距离最近的店铺

   > **推荐**该配置，可以减少接口调用，加快运行效率。

   **注意**：设置 SHOP_MODE 为 NEAREST 值后，需要**同时设置** 省份(PROVINCE) 和 城市(CITY) 的值

   ```
   13812345678$9876543210$abcd1234-5678-90ef-ghij-klmn01234567$1.8.0$['12345', '54321']$45678^NEAREST^北京市^北京市$39.904202$116.407394$eyJhbGciOiJIUzI1$eyJzZXNzaW9uX2lk
   ```

   **说明**：此配置运行时先使用用户指定的店铺 ID `45678`预约，若商品支持在该店铺预约，则直接使用该店铺预约；若该店铺不支持预约这个商品，会根据用户所在位置北京市，自动选择距离最近的店铺进行商品预订。

2. 使用 `AUTO` + `NEAREST` 模式自动选择距离最近的店铺

   **注意**：设置 SHOP_MODE 为 NEAREST 值后，需要**同时设置** 省份(PROVINCE) 和 城市(CITY) 的值

   ```
   13812345678$9876543210$abcd1234-5678-90ef-ghij-klmn01234567$1.8.0$['12345', '54321']$AUTO^NEAREST^北京市^北京市$39.904202$116.407394$eyJhbGciOiJIUzI1$eyJzZXNzaW9uX2lk
   ```

   **说明**：该配置会根据用户所在位置北京市，自动选择距离最近的店铺进行商品预订。

3. 使用 `AUTO` + `INVENTORY` 模式选择库存最多的店铺

   **注意**：设置 SHOP_MODE 为 INVENTORY 值后，需要**同时设置** 省份(PROVINCE) 和 城市(CITY) 的值

   ```
   13987654321$1029384756$abcd-1234-efgh-5678-ijkl90123456$1.8.1$['98765', '56789']$AUTO^INVENTORY^上海市^上海市$31.230391$121.473701$eyJzZXNzaW9uIjoxMjM0$eyJ1c2VyX2Nvb2tpZQ
   ```

   **说明**：此配置在上海市自动选择库存最多的店铺来完成预订。

4. 指定店铺 ID 且不使用自动选择模式

   **注意**：可能会出现“商品 ID XXX 申购失败:当前选择的门店不参与本场申购，请选择另外的门店申购”情况，建议设置 SHOP_MODE、PROVINCE 和 CITY 值，在店铺缺货时根据指定模式自动选择店铺。

   ```
   13656789012$1122334455$1234abcd-5678-efgh-9012-ijkl34567890$1.9.0$['11223']$45678$22.543096$114.057865$eyJzdG9yZV9jb29raWVfZGF0YQ$eyJ0b2tlbiI6
   ```

   **说明**：此配置使用用户指定的店铺 ID `45678`，无自动选择店铺。

5. 多个用户配置

   使用 **&** 连接。

   ```
   13876543210$9988776655$abcd1234-5678-efgh-ijkl-901234567890$1.8.2$['10999']$AUTO^INVENTORY^广东省^广州市$23.129163$113.264435$eyJzaWduZWRfY29va2ll$eyJ0b2tlbiIgY2hlY2s&13965432108$7766554433$dcba4321-8765-ghij-klmn-098765432109$1.9.0$['10500']$45678^NEAREST^江苏省^南京市$32.060255$118.796877$eyJ1c2VyX2Nvb2tpZQ$eyJvcGVuX3Nlc3Npb25fa2V5
   ```

   **说明**：该配置包含**两个**用户的信息：第一个用户在广东省广州市使用 `AUTO` + `INVENTORY` 模式自动选择库存最多的店铺；第二个用户在江苏省南京市指定店铺 ID `45678`，使用 `NEAREST` 模式选择距离最近的店铺。

## 常见问题

1. 缺少依赖，`ModuleNotFoundError: No module named 'Crypto'`？

   **解决**：单独安装 `pycryptodome` 依赖

   ```shell
   docker exec -it 青龙容器名 /bin/bash
   ```

   在容器内使用 pip 安装 pycryptodome：

   ```shell
   pip install pycryptodome
   ```

2. 运行日志显示`申购完成`，但是在 i 茅台 APP 上的预约申购页面还是显示 `预约申购` 按钮？

   **解决**：如果继续点击`预约申购`，最后会提示你已经申购的了。

   也可以在 i 茅台 APP - 我的 - 我的申购单 里面能看到`静候申购结果`。 有小伙伴已经申购成功，证明该方式可行。

3. 正确定义了环境变量，但是还报错“环境变量未定义”？例如

   ```
   /ql/data/config/config.sh: line 291: '10941', '10942': syntax error: operand expected (error token is "'10941', '10942'")
   ## 开始执行... 2024-09-20 14:21:27

   无推送渠道，请检查通知变量是否正确
   Traceback (most recent call last):
     File "/ql/data/scripts/AkenClub_ken-iMoutai-Script/4_product_reservation.py", line 183, in <module>
       raise Exception(errText)
   Exception: 🚫 KEN_IMAOTAI_ENV 环境变量未定义
   ```

   **解决**：~~在旧版本 2.13.8 能复现，升级青龙版本解决。目前在 v2.17.10、v2.17.11 可用。升级青龙版本需自行检查对其他脚本有无影响。~~

   **在确定没有填错的前提下**，在旧版本青龙（例如 v2.13.8）中，使用 `$` 作为分隔符时会出现解析环境变量失败，此时可以把 `$` 分隔符换为 `#` 作为分隔符。(2024-10-15 更新支持)。

   初次判断是因为旧版本青龙会把环境变量值在 `back/services/env.ts` 里处理生成 `env_string`，但是看到 `/ql/data/config/env.sh` 并没有把 `$` 符号正确转义，导致 `env.sh` 执行时候把 `$` 后面字符作为变量了（`$` 符号在 shell 中会被解释为变量引用），导致奇奇怪怪的错误。

   目前测试在 **青龙版本**：**正式版 v2.17.10** 可以使用 **`$`** 作为分隔符了。

   > 有其他奇奇怪怪的报错？可以试试升级青龙版本到 v2.17.10+

4. 商品 ID XXX 🚫 预约失败: 错误码 4820, 错误信息: 未知原因？

   **解决：**已知 1.7.2 版本在 24-10-30 开始报错。错误代码 4820 一般是版本号过低，对应 MT_VERSION 变量值。可以执行第一步获取最新的版本号，最好重新执行第一二步把 Token 等信息一同更新，之后重新执行预约脚本即可。

5. 运行脚本返回 [ianus-token-auth] bad token; invalid signature 错误？

   **解决：** 检查环境变量是否设置正确。出现该错误一般是因为 `值` 填了 KEN_IMAOTAI_ENV="13312345678$..$.."，脚本解析环境变量时 COOKIE 部分多了一个 `"`，导致报错。去除 KEN_IMAOTAI_ENV=""即可，`值` 只填写真实获取到的数值就行。

6. "小茅好运"专场为什么预约了环境变量里不存在的商品？

   **解决：**与 周末欢乐购 脚本不同，"小茅好运"脚本会预约本次专场内查询到的所有商品。由于专场预约无论选择多少商品，都会扣除 50 点小茅运，为最大化利益且提升中奖概率，本脚本将预约全部可查询商品。此外，这也能避免因环境变量未涵盖专场特殊商品而错过预约机会。

   如果需要**只预约环境变量里的商品**，见分支：[AkenClub/ken-iMoutai-Script at feature_8_selective_booking](https://github.com/AkenClub/ken-iMoutai-Script/tree/feature_8_selective_booking)。在青龙面板创建订阅时候，分支请填写 feature_8_selective_booking

## 计划

- ~~增加累计申购 N 天的小茅运检测和领取功能~~ [`ad4101c`](https://github.com/AkenClub/ken-iMoutai-Script/commit/ad4101c51a73f2b7336f600386de85437be46774) 已完成，需重新拉库
- ~~增加 7 日连续申购领取小茅运奖励功能~~ [`673dda4`](https://github.com/AkenClub/ken-iMoutai-Script/commit/673dda46bdb162c62742775b5c9537bede6499ea) 已完成，需重新拉库
- ~~增加判断目标店铺不支持某个商品预约时，自动选择可预约的其他店铺~~ [81971ad](https://github.com/AkenClub/ken-iMoutai-Script/commit/81971add48f18beab5f5ce15d8fa554afcb6c697) 已完成，需重新拉库。环境变量做了兼容，建议**设置**自动化选择店铺相关变量值
- ~~增加周末欢乐购~~ [0df36c9](https://github.com/AkenClub/ken-iMoutai-Script/commit/0df36c9d7a85b0f05c88e5b6b68976f0ce843190) 已完成，需重新拉库。沿用日常预约的环境变量，无需额外设置
- ~~增加 2025 年蛇年茅台 1 月活动~~ [bcfd9cb](https://github.com/AkenClub/ken-iMoutai-Script/commit/bcfd9cb4332ef8505cbe689e0295b62d0ab796ea) 已完成，需重新拉库。
- ~~增加查询申购结果~~ [31e850d](https://github.com/AkenClub/ken-iMoutai-Script/commit/31e850d8878e099eca4d15343f03845e03bb2952) 已完成，需重新拉库。
- ~~增加"小茅好运"专场~~ [d9fecbe](https://github.com/AkenClub/ken-iMoutai-Script/commit/d9fecbe7f6795e7df3cfa359c73f153bfb3c74c5) 已完成，需重新拉库。

## 特别说明

1. 涉及更新了运行时间的任务，需要删除订阅时勾选`同时删除关联任务和脚本`，之后重新设置和运行订阅源，才能让新的运行时间生效。见 [qinglong issues #2622](https://github.com/whyour/qinglong/issues/2622#issuecomment-2585735517)
   - [1334aa6](https://github.com/AkenClub/ken-iMoutai-Script/commit/1334aa6e8023259400338ebb13e8182b18aab0af)：修改了 token 有效期检测和旅行一天两次运行 => 一天一次

## 参考与致谢

本项目参考了以下两个项目：

- [yize8888/maotai](https://github.com/yize8888/maotai) - 提供了实现思路。
- [oddfar/campus-imaotai](https://github.com/oddfar/campus-imaotai) - 提供了基础实现。

感谢这些项目的作者和贡献者，他们的工作为本项目提供了宝贵的参考和灵感。

> `yize8888/maotai` 项目是青龙脚本，但没有登录、验证码获取、店铺信息、旅行相关等功能，使用时候需要额外抓包；
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
