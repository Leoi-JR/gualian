#!/usr/bin/env python3
"""
示例数据生成器
Sample Data Generator

生成虚构的示例 Parquet 数据和关键词规则表，
供用户在公开仓库中测试和演示使用。

用法:
    python scripts/generate_sample_data.py

输出:
    sample_data/keyword_rules.xlsx  - 虚构的关键词规则表
    sample_data/parquet_part01/     - Parquet 数据（第一部分字段）
    sample_data/parquet_part02/     - Parquet 数据（第二部分字段）
"""

import os
import sys
import uuid
from pathlib import Path

import pandas as pd

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent
SAMPLE_DATA_DIR = PROJECT_ROOT / "sample_data"
PARQUET_PART01 = SAMPLE_DATA_DIR / "parquet_part01"
PARQUET_PART02 = SAMPLE_DATA_DIR / "parquet_part02"
KEYWORD_RULES_PATH = SAMPLE_DATA_DIR / "keyword_rules.xlsx"


# ── 虚构示例数据 ──────────────────────────────────────────

COMPANIES = [
    {
        "record_id": "sample_001_cloud",
        "record_name": "示例云算科技有限公司",
        "company_status_clean": 1,
        "category_code": "I",
        "business_scope": "云计算技术开发、人工智能基础软件开发、大数据服务、计算机系统集成、互联网数据中心业务",
        "company_profile": "示例云算科技有限公司成立于2020年，是一家专注于云计算和人工智能领域的高科技企业。公司核心产品包括云算AI平台、智能数据分析系统和边缘计算解决方案，服务于智慧城市、智能制造和金融科技等多个行业。公司已获得多项国家发明专利和软件著作权。",
        "software_full_name": "云算AI智能分析平台V3.0",
        "bid_title": "某市智慧城市云计算平台建设项目中标公告",
        "text_field_1": "云计算服务、AI算法训练、大数据分析、边缘计算设备",
        "text_field_3": "领先的云计算和AI服务商，拥有自主知识产权的AI训练平台",
        "stock_introduction": "示例云算科技是国内领先的云计算和AI服务提供商，2023年营收超过5亿元。公司深耕智慧城市和智能制造场景，客户覆盖政府、金融、制造业等多个领域。",
        "stock_main_product": "云算AI平台、智能数据分析系统、边缘计算网关",
        "stock_business_scope": "云计算、人工智能、大数据、物联网、计算机系统集成",
        "text_field_4": "云计算服务资质、IDC经营许可证",
        "app_brief": "云算AI是一款面向客户的AI训练和部署平台",
        "text_field_5": "云算科技产业园建设项目",
        "patent_title": "一种基于云计算的人工智能模型训练方法和系统",
        "patent_abs": "本发明提供了一种基于云计算的人工智能模型训练方法和系统，通过分布式计算架构实现大规模AI模型的高效训练，显著降低了训练时间和计算资源消耗。",
        "text_field_2": "云算AI训练平台",
        "product_intro": "云算AI平台支持深度学习、机器学习和自然语言处理等多种AI模型的训练和部署",
    },
    {
        "record_id": "sample_002_energy",
        "record_name": "示例绿能新能源有限公司",
        "company_status_clean": 1,
        "category_code": "D",
        "business_scope": "新能源技术研发、太阳能光伏发电、风力发电设备制造、储能系统集成、新能源电站运营",
        "company_profile": "示例绿能新能源有限公司专注于可再生能源领域，主营业务包括太阳能光伏电站的投资建设与运营、风力发电设备制造以及大规模储能系统集成。公司拥有多项光伏发电和储能核心技术专利，在全国多个省份建设运营了超过50个新能源电站项目。",
        "software_full_name": "绿能新能源电站智能运维系统V2.0",
        "bid_title": "某省200MW光伏电站EPC总承包项目中标结果公示",
        "text_field_1": "光伏发电、风力发电、储能系统、新能源电站运维",
        "text_field_3": "新能源电站投资运营服务商，聚焦光伏和储能领域",
        "stock_introduction": "示例绿能新能源是区域领先的新能源电站投资运营商，累计装机容量超过500MW，年发电量约6亿千瓦时。公司业务涵盖光伏、风电和储能三大板块。",
        "stock_main_product": "光伏组件、风力发电机组、储能电池系统",
        "stock_business_scope": "新能源发电、储能技术、电站运营维护",
        "text_field_4": "电力业务许可证、新能源电站运营资质",
        "app_brief": "绿能运维是一款面向新能源电站的智能运维管理应用",
        "text_field_5": "绿能新能源100MW光伏电站项目",
        "patent_title": "一种光伏电站智能巡检与故障诊断系统",
        "patent_abs": "本发明公开了一种光伏电站智能巡检与故障诊断系统，结合无人机巡检和AI图像识别技术，实现对光伏组件缺陷的自动检测和定位。",
        "text_field_2": "光伏电站投资运营",
        "product_intro": "提供从电站选址、设计、建设到运营维护的全生命周期服务",
    },
    {
        "record_id": "sample_003_smart",
        "record_name": "示例智造智能装备有限公司",
        "company_status_clean": 1,
        "category_code": "C",
        "business_scope": "工业机器人制造、智能自动化生产线设计、数控机床制造、工业互联网平台开发",
        "company_profile": "示例智造智能装备有限公司是一家专注于工业自动化和智能制造的高端装备制造企业。公司主要产品包括六轴工业机器人、协作机器人、智能自动化生产线和数控加工中心，为汽车零部件、3C电子和医疗器械等行业提供智能制造整体解决方案。",
        "software_full_name": "智造工业互联网平台V1.0",
        "bid_title": "某汽车零部件客户智能化生产线改造项目招标公告",
        "text_field_1": "工业机器人、自动化生产线、数控机床、MES系统",
        "text_field_3": "高端工业机器人及智能装备制造商",
        "stock_introduction": "示例智造智能装备是国家高新技术企业，拥有省级工程技术研究中心。公司自主研发的六轴工业机器人处于国内领先水平，客户包括多家知名汽车零部件和电子制造企业。",
        "stock_main_product": "六轴工业机器人、协作机器人、智能物流系统",
        "stock_business_scope": "智能装备研发制造、工业自动化系统集成",
        "text_field_4": "工业产品生产许可证、高新技术企业认定",
        "app_brief": "智造MES是一款面向离散制造业的生产执行管理系统",
        "text_field_5": "智造智能装备产业园一期工程",
        "patent_title": "一种基于视觉引导的工业机器人精确定位方法和装置",
        "patent_abs": "本发明提供了一种基于视觉引导的工业机器人精确定位方法和装置，通过三维视觉传感器和标定算法实现机器人在复杂环境下的亚毫米级精确定位。",
        "text_field_2": "六轴工业机器人",
        "product_intro": "六轴工业机器人适用于焊接、搬运、装配等多种工业场景，重复定位精度达±0.02mm",
    },
    {
        "record_id": "sample_004_chip",
        "record_name": "示例华芯微电子有限公司",
        "company_status_clean": 1,
        "category_code": "C",
        "business_scope": "集成电路设计、半导体芯片制造、电子元器件销售、芯片封装测试服务",
        "company_profile": "示例华芯微电子有限公司是一家专注于模拟芯片和功率半导体研发的集成电路设计企业。公司产品线涵盖电源管理芯片、信号链芯片和功率器件，广泛应用于消费电子、工业控制和新能源汽车等领域。公司已通过ISO9001质量管理体系认证。",
        "software_full_name": "华芯EDA辅助设计软件V1.0",
        "bid_title": "某新能源汽车客户IGBT模块采购项目中标候选人公示",
        "text_field_1": "芯片设计、晶圆制造、封装测试、半导体器件",
        "text_field_3": "模拟芯片和功率半导体设计商",
        "stock_introduction": "示例华芯微电子是专注于模拟与混合信号芯片设计的高科技企业。公司核心团队来自国内外知名半导体企业，拥有完整的芯片设计、验证和测试能力。",
        "stock_main_product": "电源管理芯片、功率MOSFET、传感器信号调理芯片",
        "stock_business_scope": "集成电路设计、半导体技术研发",
        "text_field_4": "集成电路设计企业认定",
        "app_brief": "华芯选型是一款面向工程师的芯片选型辅助工具",
        "text_field_5": "华芯微电子研发中心建设项目",
        "patent_title": "一种低功耗高精度电源管理芯片及其控制方法",
        "patent_abs": "本发明公开了一种低功耗高精度电源管理芯片及其控制方法，采用自适应频率调节技术，在不同负载条件下实现最优转换效率，功耗降低30%以上。",
        "text_field_2": "电源管理芯片",
        "product_intro": "高效降压DC-DC转换器芯片，输入电压范围4.5V-60V，最大输出电流3A",
    },
    {
        "record_id": "sample_005_bio",
        "record_name": "示例海臻生物科技有限公司",
        "company_status_clean": 1,
        "category_code": "M",
        "business_scope": "生物技术研发、基因检测服务、体外诊断试剂生产、医学研究和试验发展",
        "company_profile": "示例海臻生物科技有限公司是一家专注于精准医学和分子诊断的生物科技企业。公司核心技术平台涵盖基因测序、荧光定量PCR和数字PCR技术，产品线包括肿瘤早筛试剂盒、遗传病检测试剂盒和病原微生物检测试剂盒。公司建有符合GMP标准的生产车间和通过CNAS认证的检测实验室。",
        "software_full_name": "海臻基因数据分析系统V2.1",
        "bid_title": "某市人民医院肿瘤精准检测服务采购项目成交公告",
        "text_field_1": "基因检测、体外诊断试剂、医学检验服务",
        "text_field_3": "精准医学和分子诊断领域的创新企业",
        "stock_introduction": "示例海臻生物科技是专注于精准医学领域的高新技术企业。公司已获得NMPA三类医疗器械注册证2项，累计服务客户超过500家医疗机构。",
        "stock_main_product": "肿瘤基因检测试剂盒、传染病核酸检测试剂盒",
        "stock_business_scope": "生物技术研发、医疗器械生产销售",
        "text_field_4": "医疗器械生产许可证、NMPA注册证",
        "app_brief": "海臻检验是一款面向临床检验科的分子诊断数据管理应用",
        "text_field_5": "海臻生物科技产业园建设项目",
        "patent_title": "一种基于数字PCR的肿瘤基因突变检测方法及试剂盒",
        "patent_abs": "本发明提供了一种基于数字PCR的肿瘤基因突变检测方法及试剂盒，可实现低至0.1%突变频率的高灵敏度检测，为肿瘤液体活检提供可靠技术方案。",
        "text_field_2": "肿瘤基因检测",
        "product_intro": "肺癌多基因联合检测试剂盒，可同时检测EGFR、ALK、ROS1等驱动基因突变",
    },
    {
        "record_id": "sample_006_drone",
        "record_name": "示例天御无人机技术有限公司",
        "company_status_clean": 1,
        "category_code": "C",
        "business_scope": "无人机研发制造、航空电子设备生产、无人机飞行服务、测绘航空摄影",
        "company_profile": "示例天御无人机技术有限公司是一家专注于工业无人机系统研发制造的高科技企业。公司产品涵盖多旋翼无人机、固定翼无人机和垂直起降固定翼无人机，应用于电力巡检、农业植保、测绘测绘和应急救灾等领域。公司拥有飞行控制系统、数据链路和地面站软件等全栈自研能力。",
        "software_full_name": "天御无人机地面站控制系统V3.0",
        "bid_title": "某省电力公司输电线路无人机巡检服务框架采购项目",
        "text_field_1": "无人机整机研发、飞控系统开发、无人机飞行服务",
        "text_field_3": "工业级无人机系统解决方案提供商",
        "stock_introduction": "示例天御无人机拥有完全自主知识产权的飞行控制与导航系统。公司产品已通过中国民用航空局适航认证，累计交付各类工业无人机超过5000架。",
        "stock_main_product": "多旋翼无人机、无人机飞控系统、地面站软件",
        "stock_business_scope": "无人机技术研发、航空摄影服务",
        "text_field_4": "民用无人驾驶航空器经营许可证",
        "app_brief": "天御飞手是一款面向无人机操作员的飞行任务规划应用",
        "text_field_5": "天御无人机研发测试基地项目",
        "patent_title": "一种基于多传感器融合的无人机自主避障导航方法",
        "patent_abs": "本发明公开了一种基于多传感器融合的无人机自主避障导航方法，融合激光雷达、视觉和IMU数据，实现无人机在未知环境中的自主导航与避障。",
        "text_field_2": "工业级无人机",
        "product_intro": "TY-500型工业四旋翼无人机，最大载荷5kg，续航时间45分钟，支持RTK高精度定位",
    },
]


# ── 虚构关键词规则 ────────────────────────────────────────

KEYWORD_RULES = [
    {
        "label_name": "示例分类",
        "label_level_1_name": "数字技术",
        "label_level_2_name": "云计算",
        "label_level_3_name": "AI平台",
        "label_level_4_name": "",
        "label_level_5_name": "",
        "source_type": "default",
        "type_filter": "I",
        "field_scope": "default",
        "like_keyword": "云计算|人工智能|AI训练|深度学习&&模型",
        "must_keyword": "云计算|AI|人工智能|科技",
        "unlike_keyword": "餐饮|零售|房地产|建筑",
    },
    {
        "label_name": "示例分类",
        "label_level_1_name": "数字技术",
        "label_level_2_name": "边缘计算",
        "label_level_3_name": "智能系统",
        "label_level_4_name": "",
        "label_level_5_name": "",
        "source_type": "default",
        "type_filter": "I",
        "field_scope": "default",
        "like_keyword": "云算&智能|大数据&分析",
        "must_keyword": "云服务|数据",
        "unlike_keyword": "餐厅|酒店|服装|食品",
    },
    {
        "label_name": "示例分类",
        "label_level_1_name": "新能源",
        "label_level_2_name": "光伏发电",
        "label_level_3_name": "光伏电站",
        "label_level_4_name": "",
        "label_level_5_name": "",
        "source_type": "default",
        "type_filter": "D",
        "field_scope": "default",
        "like_keyword": "光伏|太阳能|新能源电站|可再生能源",
        "must_keyword": "新能源|光伏|电站|发电",
        "unlike_keyword": "餐饮|零售|房地产|建筑",
    },
    {
        "label_name": "示例分类",
        "label_level_1_name": "新能源",
        "label_level_2_name": "储能",
        "label_level_3_name": "电池系统",
        "label_level_4_name": "",
        "label_level_5_name": "",
        "source_type": "default",
        "type_filter": "D",
        "field_scope": "default",
        "like_keyword": "储能&&系统|储能&电池",
        "must_keyword": "新能源|储能|电力",
        "unlike_keyword": "食品|服装|娱乐|教育",
    },
    {
        "label_name": "示例分类",
        "label_level_1_name": "智能制造",
        "label_level_2_name": "工业机器人",
        "label_level_3_name": "机器人本体",
        "label_level_4_name": "六轴机器人",
        "label_level_5_name": "",
        "source_type": "default",
        "type_filter": "C",
        "field_scope": "default",
        "like_keyword": "工业机器人|协作机器人|智能装备|数控机床",
        "must_keyword": "机器人|自动化|制造",
        "unlike_keyword": "餐饮|零售|房地产|医疗|教育",
    },
    {
        "label_name": "示例分类",
        "label_level_1_name": "智能制造",
        "label_level_2_name": "MES系统",
        "label_level_3_name": "生产执行",
        "label_level_4_name": "",
        "label_level_5_name": "",
        "source_type": "default",
        "type_filter": "C",
        "field_scope": "default",
        "like_keyword": "智造.{0,10}装备|智能装备.{0,5}制造",
        "must_keyword": "装备|制造|工业",
        "unlike_keyword": "食品|服装|娱乐|农业",
    },
    {
        "label_name": "示例分类",
        "label_level_1_name": "半导体",
        "label_level_2_name": "芯片设计",
        "label_level_3_name": "模拟芯片",
        "label_level_4_name": "电源管理",
        "label_level_5_name": "",
        "source_type": "default",
        "type_filter": "C",
        "field_scope": "default",
        "like_keyword": "芯片|集成电路|半导体|电源管理",
        "must_keyword": "芯片|半导体|集成电路",
        "unlike_keyword": "餐饮|零售|房地产|建筑|食品",
    },
    {
        "label_name": "示例分类",
        "label_level_1_name": "生物医药",
        "label_level_2_name": "分子诊断",
        "label_level_3_name": "基因检测",
        "label_level_4_name": "",
        "label_level_5_name": "",
        "source_type": "default",
        "type_filter": "M",
        "field_scope": "scope_b",
        "like_keyword": "基因检测|分子诊断|精准医学|体外诊断|核酸检测",
        "must_keyword": "基因|诊断|医疗器械|检测",
        "unlike_keyword": "餐饮|零售|房地产|建筑|游戏",
    },
    {
        "label_name": "示例分类",
        "label_level_1_name": "航空装备",
        "label_level_2_name": "无人机",
        "label_level_3_name": "工业无人机",
        "label_level_4_name": "",
        "label_level_5_name": "",
        "source_type": "default",
        "type_filter": "C",
        "field_scope": "default",
        "like_keyword": "无人机|航空|飞行器",
        "must_keyword": "无人机|飞行|航空",
        "unlike_keyword": "餐饮|零售|房地产|建筑|食品",
    },
    {
        "label_name": "示例分类",
        "label_level_1_name": "航空装备",
        "label_level_2_name": "无人机",
        "label_level_3_name": "飞控系统",
        "label_level_4_name": "",
        "label_level_5_name": "",
        "source_type": "default",
        "type_filter": "C",
        "field_scope": "default",
        "like_keyword": "天御&无人机|(多旋翼,固定翼,垂直起降)&&无人机",
        "must_keyword": "无人机|飞行|导航",
        "unlike_keyword": "餐饮|零售|房地产|建筑|食品",
    },
]


def generate_parquet_data():
    """生成虚构的 Parquet 示例数据"""
    print("生成 Parquet 示例数据...")

    part01_records = []
    part02_records = []

    for company in COMPANIES:
        record_id = company["record_id"]
        record_name = company["record_name"]
        status = company["company_status_clean"]

        # Part 01 字段
        part01_records.append({
            "record_id": record_id,
            "record_name": record_name,
            "company_status_clean": status,
            "business_scope": [company["business_scope"]],
            "text_field_4": [company["text_field_4"]],
            "app_brief": [company["app_brief"]],
            "text_field_2": [company["text_field_2"]],
            "product_intro": [company["product_intro"]],
            "text_field_5": [company["text_field_5"]],
            "patent_abs": [company["patent_abs"]],
            "patent_title": [company["patent_title"]],
        })

        # Part 02 字段
        part02_records.append({
            "record_id": record_id,
            "record_name": record_name,
            "company_status_clean": status,
            "company_profile": [company["company_profile"]],
            "software_full_name": [company["software_full_name"]],
            "bid_title": [company["bid_title"]],
            "text_field_1": [company["text_field_1"]],
            "text_field_3": [company["text_field_3"]],
            "stock_introduction": [company["stock_introduction"]],
            "stock_main_product": [company["stock_main_product"]],
            "stock_business_scope": [company["stock_business_scope"]],
            "category_code": company["category_code"],
        })

    df1 = pd.DataFrame(part01_records)
    df2 = pd.DataFrame(part02_records)

    # 确保目录存在
    PARQUET_PART01.mkdir(parents=True, exist_ok=True)
    PARQUET_PART02.mkdir(parents=True, exist_ok=True)

    # 写入 Parquet 文件（使用分片命名，与真实数据一致）
    file01_path = PARQUET_PART01 / "batch_split_001.parquet"
    file02_path = PARQUET_PART02 / "batch_split_001.parquet"

    df1.to_parquet(file01_path, index=False)
    df2.to_parquet(file02_path, index=False)

    print(f"  → {file01_path}  ({len(df1)} 条记录)")
    print(f"  → {file02_path}  ({len(df2)} 条记录)")


def generate_keyword_rules():
    """生成虚构的关键词规则表"""
    print("生成关键词规则表...")

    df = pd.DataFrame(KEYWORD_RULES)

    # 确保目录存在
    SAMPLE_DATA_DIR.mkdir(parents=True, exist_ok=True)

    df.to_excel(KEYWORD_RULES_PATH, sheet_name="原版", index=False)

    print(f"  → {KEYWORD_RULES_PATH}  ({len(df)} 条规则)")


def verify_sample_data():
    """验证生成的示例数据完整性"""
    print("\n验证示例数据...")

    errors = []

    # 检查文件是否存在
    required_files = [
        (KEYWORD_RULES_PATH, "关键词规则表"),
        (PARQUET_PART01 / "batch_split_001.parquet", "Parquet 数据 Part01"),
        (PARQUET_PART02 / "batch_split_001.parquet", "Parquet 数据 Part02"),
    ]

    for filepath, desc in required_files:
        if not filepath.exists():
            errors.append(f"  ❌ 文件缺失: {desc} ({filepath})")
        else:
            print(f"  ✓ {desc}: {filepath}")

    if errors:
        for e in errors:
            print(e)
        return False

    # 验证 Parquet 数据可合并
    try:
        df1 = pd.read_parquet(PARQUET_PART01 / "batch_split_001.parquet")
        df2 = pd.read_parquet(PARQUET_PART02 / "batch_split_001.parquet")
        merged = pd.merge(df1, df2, on=["record_id", "record_name"], how="inner")
        print(f"  ✓ Parquet 数据合并验证: 合并后 {len(merged)} 条记录")
    except Exception as e:
        errors.append(f"  ❌ Parquet 数据合并失败: {e}")
        return False

    # 验证关键词表可读取
    try:
        kw_df = pd.read_excel(KEYWORD_RULES_PATH, sheet_name="原版")
        print(f"  ✓ 关键词规则表读取验证: {len(kw_df)} 条规则, {len(kw_df.columns)} 列")
    except Exception as e:
        errors.append(f"  ❌ 关键词规则表读取失败: {e}")
        return False

    return len(errors) == 0


def print_usage_guide():
    """打印使用指南"""
    print("\n" + "=" * 60)
    print("示例数据生成完成！")
    print("=" * 60)
    print("\n首次使用步骤：")
    print("")
    print("  cp config.example.json config.json")
    print("")
    print("2. 然后启动项目：")
    print("")
    print("  python main.py")
    print("")
    print("3. 推荐操作顺序：")
    print("   1) 关键词规则验证")
    print("   2) 关键词模式转换")
    print("   3) 智能关键词匹配（随机选择单个文件测试）")
    print("   4) 匹配结果高亮导出")
    print("")
    print("说明：")
    print("  - 示例数据包含 6 家虚构企业和 10 条关键词规则")
    print("  - Parquet 数据分布为两个文件夹，按 record_id + record_name 合并")
    print("  - 关键词规则已根据虚构企业内容设计，可以正常匹配")


def main():
    """主函数"""
    print("=" * 60)
    print("示例数据生成器")
    print("=" * 60)
    print()
    print(f"数据目录: {SAMPLE_DATA_DIR}")
    print()

    generate_parquet_data()
    generate_keyword_rules()

    print()
    if verify_sample_data():
        print("\n✓ 所有数据验证通过！")
    else:
        print("\n❌ 数据验证失败，请检查错误信息")
        sys.exit(1)

    print_usage_guide()


if __name__ == "__main__":
    main()
