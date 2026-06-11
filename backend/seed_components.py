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
    s1 = add_system("热管理系统", "负责PACK温度控制，包含冷却和加热功能，确保电芯在适宜温度范围内工作")

    c1_1 = add_component(s1, "冷却板", "液冷系统核心散热部件，通常为铝制板式结构，内部有流道", is_core=1)
    add_function(c1_1, "散热", "primary", "通过流道内冷却液循环带走电芯热量", "电芯模组")
    add_function(c1_1, "均温", "supporting", "通过流道布局实现电芯间温度均匀分布", "电芯模组")

    c1_2 = add_component(s1, "冷却液", "循环流动的换热介质，通常为乙二醇水溶液")
    add_function(c1_2, "携带热量", "primary", "吸收冷却板传递的热量并输送到散热端", "冷却板")

    c1_3 = add_component(s1, "管路", "连接冷却板、水泵、散热器的管路系统")
    add_function(c1_3, "导通流路", "primary", "为冷却液提供循环通道", "冷却液")

    c1_4 = add_component(s1, "水泵", "驱动冷却液循环的动力元件")
    add_function(c1_4, "驱动循环", "primary", "提供冷却液循环动力", "冷却液")

    c1_5 = add_component(s1, "接头", "管路连接处的密封和固定元件")
    add_function(c1_5, "密封连接", "primary", "确保管路系统无泄漏", "管路")

    c1_6 = add_component(s1, "导热垫", "电芯与冷却板之间的导热界面材料（TIM）")
    add_function(c1_6, "传导热量", "primary", "填充间隙，降低接触热阻，传导电芯热量到冷却板", "冷却板")

    c1_7 = add_component(s1, "散热器", "将冷却液热量散发到环境的部件（风冷/水冷换热）")
    add_function(c1_7, "散热", "primary", "将冷却液携带的热量释放到环境中", "冷却液")

    c1_8 = add_component(s1, "加热膜/PTC", "低温环境下对电芯进行预加热的元件")
    add_function(c1_8, "加热", "primary", "低温时提升电芯温度到安全工作范围", "电芯模组")

    # 组件关系
    add_relation(c1_1, c1_6, "热传导", "面接触")
    add_relation(c1_6, c1_1, "热传导", "导热垫界面")  # 注意方向
    add_relation(c1_2, c1_1, "对流换热", "流道内壁面")
    add_relation(c1_3, c1_2, "导通", "管路内壁")
    add_relation(c1_4, c1_2, "驱动", "泵进出口")
    add_relation(c1_7, c1_2, "换热", "散热器进出口")

    # ═══════════════════════════════════════════
    # 2. 箱体结构
    # ═══════════════════════════════════════════
    s2 = add_system("箱体结构", "PACK的外壳结构，提供机械保护、密封、支撑和散热功能")

    c2_1 = add_component(s2, "上箱体", "PACK顶部盖板，通常为铝冲压或压铸件", is_core=1)
    add_function(c2_1, "密封", "primary", "与下箱体配合形成密封腔体", "下箱体")
    add_function(c2_1, "防护", "supporting", "保护内部电芯免受外部冲击和水尘侵入", "电芯模组")

    c2_2 = add_component(s2, "下箱体", "PACK底部承载结构，通常为铝型材焊接或压铸", is_core=1)
    add_function(c2_2, "承载", "primary", "承载电芯模组和热管理系统的全部重量", "电芯模组")
    add_function(c2_2, "散热", "supporting", "底部可作为散热面与冷却板集成", "冷却板")

    c2_3 = add_component(s2, "密封胶/密封圈", "箱体结合面的密封元件")
    add_function(c2_3, "密封", "primary", "防止水分和灰尘进入箱体内部", "上箱体")

    c2_4 = add_component(s2, "防爆阀", "箱体内压异常时自动泄压的安全元件")
    add_function(c2_4, "泄压", "primary", "热失控时释放箱体内高压气体", "箱体内腔")

    c2_5 = add_component(s2, "导向/定位结构", "箱体内用于电芯模组定位和固定的结构")
    add_function(c2_5, "定位固定", "primary", "确保电芯模组在箱体内的精确位置和固定", "电芯模组")

    add_relation(c2_1, c2_3, "密封配合", "结合面")
    add_relation(c2_2, c2_3, "密封配合", "结合面")
    add_relation(c2_1, c2_2, "螺栓连接", "法兰面")

    # ═══════════════════════════════════════════
    # 3. 电芯模组
    # ═══════════════════════════════════════════
    s3 = add_system("电芯模组", "由多个电芯通过串并联方式组成的基本供电单元")

    c3_1 = add_component(s3, "电芯", "单体电芯（方形铝壳/圆柱/软包）", is_core=1)
    add_function(c3_1, "储能", "primary", "储存和释放电能", "外部负载")
    add_function(c3_1, "产热", "useful", "工作时产生焦耳热", "环境")

    c3_2 = add_component(s3, "模组框架", "固定和支撑电芯的结构件")
    add_function(c3_2, "固定", "primary", "将多个电芯固定为一个模组整体", "电芯")

    c3_3 = add_component(s3, "汇流排", "连接电芯极柱的导电件")
    add_function(c3_3, "导电连接", "primary", "实现电芯间的串并联电气连接", "电芯")

    c3_4 = add_component(s3, "隔热垫", "电芯间的隔热元件")
    add_function(c3_4, "隔热", "primary", "防止单体热失控向相邻电芯蔓延", "电芯")

    c3_5 = add_component(s3, "膨胀管理结构", "预留电芯膨胀空间的结构（泡棉/弹簧等）")
    add_function(c3_5, "缓冲膨胀", "primary", "吸收电芯循环膨胀力，维持模组结构完整", "电芯")

    add_relation(c3_1, c3_2, "机械固定", "框架槽位")
    add_relation(c3_1, c3_3, "电气连接", "极柱面")
    add_relation(c3_1, c3_4, "隔热接触", "侧面")

    # ═══════════════════════════════════════════
    # 4. BMS（电池管理系统）
    # ═══════════════════════════════════════════
    s4 = add_system("BMS", "电池管理系统，负责电芯状态监测、安全保护和热管理策略控制")

    c4_1 = add_component(s4, "电压采集模块", "采集每个电芯的电压", is_core=1)
    add_function(c4_1, "电压监测", "primary", "实时采集单体电芯电压", "电芯")

    c4_2 = add_component(s4, "温度采集模块", "采集电芯和关键点温度", is_core=1)
    add_function(c4_2, "温度监测", "primary", "实时采集电芯表面和冷却液温度", "电芯")

    c4_3 = add_component(s4, "均衡模块", "电芯间电量均衡")
    add_function(c4_3, "均衡", "primary", "消除电芯间SOC差异", "电芯")

    c4_4 = add_component(s4, "热管理控制策略", "基于温度数据控制冷却/加热系统")
    add_function(c4_4, "控制冷却", "primary", "根据温度调节水泵转速和冷却功率", "水泵")
    add_function(c4_4, "控制加热", "primary", "低温时控制加热膜工作", "加热膜")

    c4_5 = add_component(s4, "通信接口", "与整车控制器通信")
    add_function(c4_5, "数据上报", "primary", "上报SOC/SOH/温度/告警等信息", "整车控制器")

    # ═══════════════════════════════════════════
    # 5. 电气系统
    # ═══════════════════════════════════════════
    s5 = add_system("电气系统", "PACK内部的高压和低压电气连接与保护系统")

    c5_1 = add_component(s5, "高压线束", "连接模组与输出端的高压导线", is_core=1)
    add_function(c5_1, "输电", "primary", "将电芯电能传输到PACK输出端", "高压输出端")

    c5_2 = add_component(s5, "低压线束", "BMS及传感器的信号线束")
    add_function(c5_2, "信号传输", "primary", "传输采集信号和控制指令", "BMS")

    c5_3 = add_component(s5, "熔断器", "过流保护元件")
    add_function(c5_3, "过流保护", "primary", "电流异常时切断电路保护系统", "高压线束")

    c5_4 = add_component(s5, "高压接插件", "PACK对外的高压连接接口")
    add_function(c5_4, "电气连接", "primary", "实现PACK与整车的高压连接", "整车高压系统")

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
        print(f"  [{s['id']}] {s['name']}：{', '.join(comps)}")


if __name__ == "__main__":
    seed()
