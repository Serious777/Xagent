"""种子数据 — 动力电池PACK常见系统/组件/功能"""
from component_db import (
    init_db, add_system, add_component, add_function, add_relation,
    get_db
)

def seed():
    """写入电池PACK常见系统组件数据"""
    init_db()
    conn = get_db()

    # 检查是否已有数据
    count = conn.execute("SELECT COUNT(*) FROM systems").fetchone()[0]
    if count > 0:
        print(f"数据库已有 {count} 个系统，跳过种子写入。如需重新导入请先清空表。")
        conn.close()
        return

    conn.close()

    # ═══════════════════════════════════════════
    # 1. 热管理系统
    # ═══════════════════════════════════════════
    s1 = add_system("热管理系统",
        "负责PACK温度控制，确保电芯在15-35°C适宜温度范围工作。"
        "冷却方式包括液冷（主流）、风冷、直冷和浸没式冷却")

    # --- 冷却板 ---
    c1_1 = add_component(s1, "冷却板（液冷板）",
        "铝制板式结构，内部有蛇形/平行流道，是液冷系统核心散热部件。"
        "类型包括口琴管式、冲压板式、钎焊板式", is_core=1)
    add_function(c1_1, "散热", "通过流道内冷却液循环带走电芯热量，实现核心热交换", "primary", "电芯模组")
    add_function(c1_1, "均温", "通过流道布局实现电芯间温度均匀分布", "supporting", "电芯模组")

    # --- 冷却液 ---
    c1_2 = add_component(s1, "冷却液",
        "50%乙二醇水溶液，循环流动的换热介质，冰点-40°C，沸点110°C")
    add_function(c1_2, "携带热量", "吸收冷却板传递的热量并输送到散热端", "primary", "冷却板")

    # --- 水泵 ---
    c1_3 = add_component(s1, "水泵（电子冷却液泵）",
        "驱动冷却液循环的动力元件，流量10-20L/min，功率50-150W")
    add_function(c1_3, "驱动循环", "提供冷却液循环动力，驱动冷却液在管路中流动", "primary", "冷却液")

    # --- 散热器 ---
    c1_4 = add_component(s1, "散热器（冷凝器）",
        "将冷却液热量散发到环境的部件，铝制翅片结构")
    add_function(c1_4, "散热", "将冷却液携带的热量释放到环境中", "primary", "冷却液")

    # --- 膨胀水壶 ---
    c1_5 = add_component(s1, "膨胀水壶（补水壶）",
        "调节冷却液因温度变化产生的体积膨胀，容纳膨胀量，排出气泡")
    add_function(c1_5, "容积补偿", "容纳冷却液热胀冷缩产生的体积变化，排出系统气泡", "primary", "冷却液")

    # --- 加热膜/PTC ---
    c1_6 = add_component(s1, "加热膜/PTC加热器",
        "低温环境下对电芯进行预加热的元件，功率1-5kW，加热速度2-5°C/min")
    add_function(c1_6, "预加热", "低温时提升电芯温度到安全工作范围（>15°C）", "primary", "电芯模组")

    # --- 热管理控制阀 ---
    c1_7 = add_component(s1, "热管理控制阀（多通阀）",
        "控制冷却液流向，实现冷却/加热模式切换，常用三通阀/四通阀")
    add_function(c1_7, "流向控制", "控制冷却液流向，实现冷却和加热模式的切换", "primary", "冷却液")

    # --- 温度传感器 ---
    c1_8 = add_component(s1, "温度传感器（NTC）",
        "监测电芯表面和冷却液温度，精度±1°C，响应时间<1s")
    add_function(c1_8, "温度监测", "实时监测电芯表面温度和冷却液温度", "primary", "电芯模组")

    # --- 导热界面材料 ---
    c1_9 = add_component(s1, "导热界面材料（TIM）",
        "电芯与冷却板之间的导热介质，类型包括导热垫片（1-6W/mK）、"
        "导热硅脂（3-8W/mK）、相变材料（PCM）、导热凝胶。填充间隙降低接触热阻")
    add_function(c1_9, "传导热量", "填充电芯与冷却板间间隙，降低接触热阻，传导热量", "primary", "冷却板")

    # --- 冷却管路 ---
    c1_10 = add_component(s1, "冷却管路",
        "连接冷却板、水泵、散热器的耐压耐温胶管/铝管")
    add_function(c1_10, "导通流路", "为冷却液提供循环通道", "primary", "冷却液")

    # --- 接头 ---
    c1_11 = add_component(s1, "接头/快插接头",
        "管路连接处的密封和固定元件，密封等级IP67")
    add_function(c1_11, "密封连接", "确保管路系统连接处无泄漏", "primary", "冷却管路")

    # --- 热管理系统关系 ---
    add_relation(c1_9, c1_1, "热传导", "导热垫→冷却板，电芯底面→冷却板上表面")
    add_relation(c1_2, c1_1, "对流换热", "冷却液→冷却板，流道内壁面")
    add_relation(c1_3, c1_2, "驱动循环", "水泵→冷却液，泵进出口")
    add_relation(c1_10, c1_2, "导通", "管路→冷却液，管路内壁")
    add_relation(c1_4, c1_2, "换热", "散热器→冷却液，散热器进出口")
    add_relation(c1_5, c1_2, "容积补偿", "膨胀水壶→冷却液，连接管路")
    add_relation(c1_7, c1_2, "流向控制", "热管理控制阀→冷却液，阀进出口")
    add_relation(c1_8, c1_1, "温度监测", "温度传感器→冷却板，贴合面/插入式")
    add_relation(c1_8, c1_2, "温度监测", "温度传感器→冷却液，插入式测温")
    add_relation(c1_6, c1_1, "热传导", "加热膜→冷却板，贴合电芯表面")
    add_relation(c1_11, c1_10, "密封连接", "接头→管路，管路连接处")

    # ═══════════════════════════════════════════
    # 2. 箱体结构
    # ═══════════════════════════════════════════
    s2 = add_system("箱体结构",
        "PACK外壳结构，提供机械保护、密封、碰撞防护和热管理接口。"
        "防护等级IP67/IP68")

    # --- 下箱体 ---
    c2_1 = add_component(s2, "下箱体（底壳）",
        "PACK底部承载结构，通常为铝型材焊接或铝合金压铸，"
        "承载电芯模组全部重量，是结构核心", is_core=1)
    add_function(c2_1, "承载", "承载电芯模组和热管理系统的全部重量", "primary", "电芯模组")
    add_function(c2_1, "安装基座", "提供PACK与车身底盘的连接固定基础", "supporting", "车身底盘")

    # --- 上箱体 ---
    c2_2 = add_component(s2, "上箱体（顶盖）",
        "PACK顶部盖板，铝冲压或压铸件，与下箱体配合密封")
    add_function(c2_2, "密封防护", "与下箱体配合形成密封腔体，保护内部元件", "primary", "下箱体")

    # --- 密封胶/密封圈 ---
    c2_3 = add_component(s2, "密封胶/密封圈（FIPG/IPG）",
        "箱体结合面的密封元件，硅胶/EPDM材料，满足IP67防护，压缩率20-40%")
    add_function(c2_3, "密封", "防止水分和灰尘进入箱体内部，满足IP67防护等级", "primary", "上箱体")

    # --- 防爆阀 ---
    c2_4 = add_component(s2, "防爆阀（泄压阀/呼吸阀）",
        "箱体内压异常时自动泄压的安全元件，开启压力5-15kPa，防止热失控时箱体爆炸")
    add_function(c2_4, "泄压", "箱体内压异常时自动泄压，防止热失控时箱体爆炸", "primary", "上箱体")

    # --- 防撞梁 ---
    c2_5 = add_component(s2, "防撞梁/侧边梁",
        "箱体侧面碰撞防护结构，铝合金型材或高强度钢，满足碰撞法规要求")
    add_function(c2_5, "碰撞防护", "侧面碰撞时吸收冲击能量，保护内部电芯模组", "primary", "下箱体")

    # --- 横梁/纵梁 ---
    c2_6 = add_component(s2, "箱体内部横梁/纵梁",
        "分隔模组空间、增加箱体刚性的结构件")
    add_function(c2_6, "刚性增强", "增加箱体整体刚性，分隔模组安装空间", "primary", "下箱体")

    # --- 固定支架 ---
    c2_7 = add_component(s2, "箱体固定支架/安装点",
        "PACK与车身底盘的连接固定结构，满足NVH和碰撞要求")
    add_function(c2_7, "固定连接", "将PACK固定安装到车身底盘，满足NVH和碰撞要求", "primary", "下箱体")

    # --- 导轨 ---
    c2_8 = add_component(s2, "导轨/导向结构",
        "箱体内用于电芯模组定位和装配导向的结构")
    add_function(c2_8, "定位导向", "确保电芯模组在箱体内的精确位置和装配导向", "primary", "电芯模组")

    # --- 箱体结构关系 ---
    add_relation(c2_2, c2_1, "螺栓连接", "上箱体→下箱体，法兰面螺栓连接")
    add_relation(c2_3, c2_1, "密封配合", "密封胶→下箱体，下箱体结合面")
    add_relation(c2_3, c2_2, "密封配合", "密封胶→上箱体，上箱体结合面")
    add_relation(c2_4, c2_2, "泄压安装", "防爆阀→上箱体，上箱体开孔处")
    add_relation(c2_5, c2_1, "碰撞防护", "防撞梁→下箱体，侧面焊接/螺接")
    add_relation(c2_6, c2_1, "刚性增强", "横梁/纵梁→下箱体，内部焊接")

    # ═══════════════════════════════════════════
    # 3. 电芯模组
    # ═══════════════════════════════════════════
    s3 = add_system("电芯模组",
        "由多个电芯通过串并联方式组成的基本供电单元。"
        "当前主流为CTP（Cell-to-Pack）和CTC（Cell-to-Chassis）技术")

    # --- 电芯 ---
    c3_1 = add_component(s3, "电芯",
        "单体电池，类型包括方形铝壳（主流，宁德时代/比亚迪）、"
        "圆柱（4680/21700）、软包（SK/三星SDI）", is_core=1)
    add_function(c3_1, "储能", "储存和释放电能，是PACK的能量源", "primary", "外部负载")
    add_function(c3_1, "产热", "工作时产生焦耳热，需热管理系统控制温升", "useful", "环境")

    # --- 模组框架 ---
    c3_2 = add_component(s3, "模组框架（端板+侧板）",
        "固定和支撑电芯的结构件，铝合金/钢/复合材料")
    add_function(c3_2, "机械固定", "将多个电芯固定为一个模组整体", "primary", "电芯")

    # --- 汇流排 ---
    c3_3 = add_component(s3, "汇流排（Busbar）",
        "连接电芯极柱的导电件，铜/铝材质，激光焊接或螺接")
    add_function(c3_3, "电气连接", "实现电芯间的串并联电气连接", "primary", "电芯")

    # --- 隔热垫 ---
    c3_4 = add_component(s3, "隔热垫（气凝胶/云母板）",
        "电芯间的隔热元件，防止热失控蔓延，耐温>1000°C")
    add_function(c3_4, "隔热", "防止单体热失控向相邻电芯蔓延，耐温>1000°C", "primary", "电芯")

    # --- 膨胀缓冲结构 ---
    c3_5 = add_component(s3, "膨胀缓冲结构（泡棉/弹簧片）",
        "预留电芯膨胀空间，吸收循环膨胀力，维持模组结构完整")
    add_function(c3_5, "缓冲膨胀", "吸收电芯循环膨胀力，维持模组结构完整", "primary", "电芯")

    # --- 固定胶 ---
    c3_6 = add_component(s3, "电芯固定胶/结构胶",
        "将电芯粘接固定在模组框架中的结构胶")
    add_function(c3_6, "粘接固定", "将电芯粘接固定在模组框架中，增强结构强度", "primary", "电芯")

    # --- 模组端板 ---
    c3_7 = add_component(s3, "模组端板",
        "模组两端的封板，承受电芯膨胀力，铝合金材质")
    add_function(c3_7, "承力封板", "承受电芯膨胀力，封闭模组端面", "primary", "电芯")

    # --- FPC/线束 ---
    c3_8 = add_component(s3, "电压采集线束（FPC/线束）",
        "连接电芯极柱到BMS从板的信号采集线")
    add_function(c3_8, "信号采集", "将电芯电压和温度信号传输到BMS从板", "primary", "BMS从控模块")

    # --- 电芯模组关系 ---
    add_relation(c3_2, c3_1, "机械固定", "模组框架→电芯，框架槽位/端面固定")
    add_relation(c3_3, c3_1, "电气连接", "汇流排→电芯，极柱面（激光焊接）")
    add_relation(c3_4, c3_1, "隔热接触", "隔热垫→电芯，电芯侧面")
    add_relation(c3_5, c3_1, "缓冲膨胀", "膨胀缓冲结构→电芯，电芯顶面/底面")
    add_relation(c3_6, c3_1, "粘接固定", "固定胶→电芯，电芯底面/侧面")
    add_relation(c3_8, c3_1, "信号采集", "FPC/线束→电芯，极柱/壳体")

    # ═══════════════════════════════════════════
    # 4. BMS（电池管理系统）
    # ═══════════════════════════════════════════
    s4 = add_system("BMS（电池管理系统）",
        "电池智能管理核心，监控电芯状态、安全保护和热管理策略控制。"
        "架构从集中式向分布式演进")

    # --- BMU主控 ---
    c4_1 = add_component(s4, "BMU/BMS主控制器（Master）",
        "中央处理单元，运行SOC/SOH算法，执行保护策略，与整车VCU通信。"
        "芯片如英飞凌TC387/TC275", is_core=1)
    add_function(c4_1, "SOC/SOH估算", "运行电芯荷电状态和健康状态算法", "primary", "电芯模组")
    add_function(c4_1, "保护策略", "过压/欠压/过流/过温保护决策", "primary", "BDU电池配电单元")
    add_function(c4_1, "整车通信", "与VCU上报SOC/告警/执行控制指令", "supporting", "整车控制器")

    # --- CSC/CSU从控 ---
    c4_2 = add_component(s4, "CSC/CSU从控模块（Slave）",
        "电芯监控单元，就近采集电芯电压温度，每个模块管理一组电芯。"
        "芯片如TI BQ79616/ADI LTC6811，分布式架构下使用")
    add_function(c4_2, "电芯监控", "就近采集所辖电芯的电压和温度数据", "primary", "电芯")

    # --- AFE ---
    c4_3 = add_component(s4, "AFE模拟前端芯片",
        "高精度ADC采集电芯电压（±2mV）、温度，支持主动/被动均衡")
    add_function(c4_3, "电压采集", "高精度ADC采集单体电芯电压，精度±2mV", "primary", "电芯")
    add_function(c4_3, "温度采集", "采集电芯温度信号", "primary", "电芯")

    # --- 电流传感器 ---
    c4_4 = add_component(s4, "电流传感器（霍尔/分流器）",
        "测量PACK总电流，量程±500A，精度±0.5%")
    add_function(c4_4, "电流测量", "测量PACK总电流，量程±500A，精度±0.5%", "primary", "BMU主控")

    # --- BDU ---
    c4_5 = add_component(s4, "BDU电池配电单元（高压配电盒）",
        "集成高压继电器、熔断器、预充电路，控制高压回路通断")
    add_function(c4_5, "高压通断控制", "根据BMU指令控制高压回路的接通和断开", "primary", "高压线束")
    add_function(c4_5, "预充控制", "上电时通过预充回路防止大电流冲击负载电容", "primary", "高压负载")

    # --- 高压继电器 ---
    c4_6 = add_component(s4, "高压直流继电器",
        "高压回路主开关，承载200-500A电流，响应时间<5ms")
    add_function(c4_6, "高压通断", "承载大电流，快速通断高压回路，响应时间<5ms", "primary", "BDU")

    # --- 预充继电器+预充电阻 ---
    c4_7 = add_component(s4, "预充电继电器+预充电阻",
        "上电时防止大电流冲击负载电容")
    add_function(c4_7, "预充保护", "上电时限制初始电流，防止大电流冲击负载电容", "primary", "BDU")

    # --- 熔断器 ---
    c4_8 = add_component(s4, "熔断器（保险丝）",
        "过流保护元件，额定电流与整车匹配")
    add_function(c4_8, "过流保护", "电流异常超过额定值时熔断切断电路", "primary", "BDU")

    # --- 绝缘检测 ---
    c4_9 = add_component(s4, "绝缘检测模块",
        "检测高压系统对车身的绝缘电阻，满足功能安全要求")
    add_function(c4_9, "绝缘监测", "实时监测高压系统对车身的绝缘电阻", "primary", "BMU主控")

    # --- 温度采集模块 ---
    c4_10 = add_component(s4, "温度采集模块（NTC传感器组）",
        "多点温度监测，精度±1°C")
    add_function(c4_10, "温度监测", "多点监测电芯和关键部位温度，精度±1°C", "primary", "BMU主控")

    # --- 均衡模块 ---
    c4_11 = add_component(s4, "均衡模块（主动/被动）",
        "消除电芯间SOC差异，被动均衡通过电阻放电，主动均衡通过DC-DC转移能量")
    add_function(c4_11, "电量均衡", "消除电芯间SOC差异，提升PACK可用容量", "primary", "电芯")

    # --- CAN通信模块 ---
    c4_12 = add_component(s4, "CAN通信模块",
        "BMS与VCU/OBC/充电机的通信接口，CAN FD速率5Mbps")
    add_function(c4_12, "数据通信", "BMS与VCU/OBC/充电机的CAN FD通信，速率5Mbps", "primary", "整车控制器")

    # --- 无线BMS ---
    c4_13 = add_component(s4, "无线BMS模块（wBMS）",
        "无线通信替代线束，如TI/恩智浦方案，减少线束复杂度")
    add_function(c4_13, "无线通信", "以无线方式替代有线信号传输，减少线束复杂度", "primary", "BMU主控")

    # --- BMS关系 ---
    add_relation(c4_1, c4_2, "通信控制", "BMU→CSC，菊花链/CAN总线通信")
    add_relation(c4_2, c4_3, "信号采集", "CSC→AFE，芯片引脚连接")
    add_relation(c4_3, c4_1, "数据上报", "AFE→BMU，电压温度数据上传")
    add_relation(c4_4, c4_1, "电流信号输入", "电流传感器→BMU，电流信号采集")
    add_relation(c4_5, c4_1, "高压控制指令", "BDU→BMU，CAN/硬线连接")
    add_relation(c4_6, c4_5, "高压通断控制", "高压继电器→BDU，串联回路")
    add_relation(c4_7, c4_5, "预充回路", "预充继电器+预充电阻→BDU，预充支路")
    add_relation(c4_8, c4_5, "过流保护", "熔断器→BDU，串联回路")
    add_relation(c4_9, c4_1, "绝缘状态监测", "绝缘检测模块→BMU，监测信号")
    add_relation(c4_10, c4_1, "温度信号输入", "温度采集模块→BMU，NTC信号")
    add_relation(c4_11, c4_1, "均衡控制", "均衡模块→电芯，并联回路均衡")
    add_relation(c4_12, c4_1, "CAN通信", "CAN通信模块→BMU，CAN总线")
    add_relation(c4_13, c4_1, "无线通信", "wBMS→BMU，无线信号")

    # ═══════════════════════════════════════════
    # 5. 电气系统
    # ═══════════════════════════════════════════
    s5 = add_system("电气系统",
        "PACK内部的高压和低压电气连接与保护系统")

    # --- 高压线束 ---
    c5_1 = add_component(s5, "高压线束",
        "连接模组与输出端的高压导线，额定电压600-1000V，阻燃等级UL94 V-0", is_core=1)
    add_function(c5_1, "输电", "将电芯电能传输到PACK输出端，额定电压600-1000V", "primary", "高压输出端")

    # --- 低压线束 ---
    c5_2 = add_component(s5, "低压线束/BMS信号线束",
        "BMS及传感器的信号线束，CAN总线/模拟信号")
    add_function(c5_2, "信号传输", "传输BMS采集信号和控制指令，CAN总线/模拟信号", "primary", "BMS")

    # --- 高压接插件 ---
    c5_3 = add_component(s5, "高压接插件（连接器）",
        "PACK对外的高压连接接口，IP67防护，如TE/安费诺产品")
    add_function(c5_3, "电气连接", "实现PACK与整车的高压连接，IP67防护等级", "primary", "整车高压系统")

    # --- 低压接插件 ---
    c5_4 = add_component(s5, "低压接插件",
        "低压信号连接器，如Molex/TE产品")
    add_function(c5_4, "信号连接", "实现BMS与外部的低压信号连接", "primary", "BMS")

    # --- 铜排/铝排 ---
    c5_5 = add_component(s5, "铜排/铝排（Busbar）",
        "模组间或模组到BDU的大电流导电连接件")
    add_function(c5_5, "大电流导电", "模组间或模组到BDU的大电流传输", "primary", "电芯模组")

    # --- 接地点 ---
    c5_6 = add_component(s5, "接地点/接地线束",
        "高压系统接地保护连接")
    add_function(c5_6, "接地保护", "高压系统接地，保障人身和设备安全", "primary", "下箱体")

    # --- HVIL ---
    c5_7 = add_component(s5, "高压互锁回路（HVIL）",
        "检测高压连接器是否可靠的低压安全回路")
    add_function(c5_7, "安全检测", "检测高压连接器插接状态，未可靠连接时切断高压", "primary", "高压接插件")

    # --- Shunt ---
    c5_8 = add_component(s5, "电流分流器（Shunt）",
        "精密电流测量元件，配合BMS采集总电流")
    add_function(c5_8, "精密测流", "精密测量PACK总电流，配合BMS采集", "primary", "BMS")

    # --- 电气系统关系 ---
    add_relation(c5_1, c5_3, "电气连接", "高压线束→高压接插件，连接器端子")
    add_relation(c5_5, c5_1, "大电流连接", "铜排/铝排→模组，端板螺栓连接")
    add_relation(c5_2, c5_4, "信号连接", "低压线束→低压接插件，连接器接口")
    add_relation(c5_7, c5_3, "安全检测", "HVIL→高压接插件，互锁引脚")
    add_relation(c5_6, c5_1, "接地保护", "接地线束→高压线束，接地螺栓")
    add_relation(c5_8, c5_1, "电流测量", "Shunt→高压线束，串联回路")

    print("✅ 种子数据写入完成")
    print_systems()


def print_systems():
    """打印所有系统和组件概览"""
    from component_db import get_all_systems, get_system_components

    systems = get_all_systems()
    print(f"\n📦 共 {len(systems)} 个系统：")
    for s in systems:
        data = get_system_components(s["id"])
        comps = [c["name"] for c in data["components"]]
        relations = data["relations"]
        print(f"\n  [{s['id']}] {s['name']}")
        print(f"    描述：{s['description'][:60]}...")
        print(f"    组件({len(comps)}个)：")
        for c in data["components"]:
            core_mark = " ★" if c["is_core"] else ""
            funcs = [f["function_name"] for f in c["functions"]]
            print(f"      - {c['name']}{core_mark} → {', '.join(funcs)}")
        if relations:
            print(f"    关系({len(relations)}条)：")
            for r in relations:
                print(f"      {r['component_a']} --{r['relation_type']}--> {r['component_b']}")


if __name__ == "__main__":
    seed()
