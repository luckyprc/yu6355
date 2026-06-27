#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
====================================================
CFLUE 题库自动下载转换器 v3（方案A）
====================================================
功能：
  1. 从 GitHub 仓库 aliyun/cflue 直接 clone 下载数据
  2. 提取经济师相关题目
  3. 自动识别公共科目/专业科目，chapter 格式为 "subject-细分章节"
  4. 转换为刷题系统标准 JSON 格式

依赖：
  pip install requests pandas

用法：
  python convert_cflue_v3.py
  输出：questions.json
"""

import json
import ast
import sys
import os
import re
import hashlib
import subprocess

OUTPUT_FILE = "questions.json"

# 专业科目关键词映射（题目内容匹配）
SUBJECT_KEYWORDS = {
    "经济基础知识": ["经济学基础", "市场需求", "供给", "GDP", "CPI", "财政政策", "货币政策",
                  "统计调查", "会计要素", "资产负债表", "物权", "合同法", "公司法", "劳动法",
                  "消费者行为", "生产函数", "成本曲线", "市场结构", "国民收入", "失业", "通货膨胀",
                  "财政支出", "税收", "预算", "国债", "货币供求", "中央银行", "商业银行",
                  "金融风险", "财务报表", "会计报表", "现金流量", "所有者权益", "经济法",
                  "物权", "合同", "公司", "商标", "反垄断", "反不正当竞争", "劳动合同"],
    "工商管理": ["企业战略", "市场营销", "品牌", "生产管理", "物流", "技术创新", "筹资", "投资", "并购重组",
               "目标市场", "定价", "渠道", "促销", "新产品开发", "生产能力", "库存", "质量",
               "技术转移", "专利", "筹资决策", "投资决策", "现金流", "财务分析", "并购重组"],
    "人力资源": ["招聘", "培训", "绩效", "薪酬", "劳动关系", "人力资源规划", "工作分析", "员工",
               "甄选", "面试", "离职", "绩效评价", "绩效考核", "薪酬管理", "福利", "劳动合同",
               "劳动争议", "仲裁", "社会保险", "人力资本", "激励", "领导", "沟通", "组织"],
    "金融": ["银行", "证券", "金融市场", "利率", "汇率", "通货膨胀", "商业银行", "金融风险", "巴塞尔",
            "股票", "债券", "基金", "期货", "期权", "信托", "租赁", "外汇", "国际收支",
            "货币供给", "货币需求", "货币政策工具", "金融监管", "金融深化", "金融危机"],
    "财政税收": ["增值税", "所得税", "关税", "税收征管", "税务", "预算", "国债", "转移支付", "政府购买",
               "消费税", "营业税", "房产税", "车船税", "印花税", "资源税", "土地增值税",
               "税务登记", "纳税申报", "税务稽查", "税务代理", "发票", "税收筹划"],
    "建筑与房地产": ["房地产", "建筑工程", "造价", "土地", "房地产开发", "物业管理",
                   "建设用地", "土地使用权", "房屋", "建筑物", "工程造价", "招标投标",
                   "施工", "监理", "竣工验收", "房地产市场", "房地产估价", "物业管理"],
    "知识产权": ["专利", "商标", "著作权", "知识产权", "地理标志", "商业秘密",
               "发明专利", "实用新型", "外观设计", "商标注册", "商标权", "版权",
               "知识产权管理", "知识产权保护", "知识产权运营"],
    "农业经济": ["农业", "农村", "农产品", "土地制度", "粮食", "农业政策", "农村金融",
               "农业现代化", "农业产业化", "农业技术", "农业补贴", "农村土地", "耕地",
               "农民收入", "农业保险", "农产品市场", "农业合作社"],
    "保险": ["保险合同", "人寿保险", "财产保险", "再保险", "保险市场", "保险监管", "保险原则",
            "投保人", "被保险人", "受益人", "保险标的", "保险费", "保险金额", "理赔",
            "保险代理", "保险经纪", "保险公估", "社会保险", "商业保险", "健康保险"],
    "运输经济": ["运输", "交通", "航运", "铁路", "公路", "航空", "管道运输", "运输成本",
               "物流", "货运", "客运", "港口", "车站", "机场", "运输市场", "运输价格",
               "运输政策", "运输规划", "多式联运", "集装箱", "运输企业"],
    "旅游经济": ["旅游", "旅行社", "酒店", "景区", "旅游服务", "旅游市场", "旅游产品",
               "导游", "饭店", "客房", "餐饮", "旅游资源", "旅游规划", "旅游投资",
               "旅游消费", "旅游收入", "旅游政策", "旅游法规", "旅游安全"]
}


def download_github_clone():
    """Git clone 仓库并读取数据文件"""
    try:
        print("[*] 尝试 GitHub clone: https://github.com/aliyun/cflue.git")
        tmp_dir = "/tmp/cflue_repo"
        if os.path.exists(tmp_dir):
            subprocess.run(["rm", "-rf", tmp_dir], check=False)
        result = subprocess.run(
            ["git", "clone", "--depth", "1", "https://github.com/aliyun/cflue.git", tmp_dir],
            capture_output=True, text=True, timeout=120
        )
        if result.returncode != 0:
            print(f"[!] git clone 失败: {result.stderr[:200]}")
            return None
        data_path = os.path.join(tmp_dir, "data/knowledge")
        if not os.path.exists(data_path):
            print(f"[!] 数据路径不存在: {data_path}")
            return None
        data = []
        for filename in os.listdir(data_path):
            filepath = os.path.join(data_path, filename)
            if filename.endswith('.json'):
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if content.startswith('['):
                        data.extend(json.loads(content))
                    else:
                        for line in content.split('\n'):
                            if line.strip():
                                data.append(json.loads(line))
            elif filename.endswith('.jsonl'):
                with open(filepath, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            data.append(json.loads(line))
        if data:
            print(f"[+] 成功: {len(data)} 条")
            return data
        return None
    except Exception as e:
        print(f"[!] 失败: {e}")
        return None


def load_local():
    """查找本地已有的数据文件"""
    local_patterns = [
        "cflue_knowledge.json", "cflue.json", "data.json",
        "train.json", "train.jsonl", "dev.json", "test.json"
    ]
    for pattern in local_patterns:
        for f in os.listdir('.'):
            if f.endswith(pattern) or f == pattern:
                print(f"[*] 发现本地文件: {f}")
                with open(f, 'r', encoding='utf-8') as fp:
                    content = fp.read().strip()
                    if content.startswith('['):
                        return json.loads(content)
                    else:
                        return [json.loads(line) for line in content.split('\n') if line.strip()]
    return None


def parse_choices(choices_str):
    """解析 CFLUE 的 choices 字符串"""
    if isinstance(choices_str, dict):
        keys = sorted(choices_str.keys())
        return [choices_str.get(k, "") for k in keys]
    if isinstance(choices_str, list):
        return choices_str
    try:
        d = ast.literal_eval(choices_str)
        if isinstance(d, dict):
            keys = sorted(d.keys())
            return [d.get(k, "") for k in keys]
    except:
        pass
    matches = re.findall(r"['\"]([A-D])['\"]\s*:\s*['\"](.*?)['\"](?:,|\})", choices_str)
    if matches:
        return [m[1] for m in sorted(matches, key=lambda x: x[0])]
    return []


def detect_subject(question):
    """根据题目内容自动识别专业科目"""
    for subject, keywords in SUBJECT_KEYWORDS.items():
        for kw in keywords:
            if kw in question:
                return subject
    return "经济基础知识"  # 默认归公共科目


def convert_item(item):
    """将 CFLUE 单条数据转换为标准格式"""
    name = item.get("名称", item.get("name", item.get("exam_type", "")))
    if "中级经济师" not in name:
        return None

    question = item.get("question", item.get("题目", item.get("q", "")))
    if not question:
        return None

    options = parse_choices(item.get("choices", item.get("选项", item.get("options", {}))))
    if len(options) < 2:
        return None

    ans = item.get("answer", item.get("答案", item.get("correct", "A")))
    if isinstance(ans, int):
        answer = [ans]
    elif isinstance(ans, str) and len(ans) == 1 and ans.upper() in "ABCD":
        answer = [ord(ans.upper()) - ord("A")]
    elif isinstance(ans, list):
        answer = [ord(a.upper()) - ord("A") if isinstance(a, str) and len(a) == 1 else int(a) for a in ans]
    else:
        answer = [0]

    task = item.get("task", item.get("题型", ""))
    q_type = "multiple" if "多" in task or len(answer) > 1 else "single"

    # 检测专业科目
    subject = detect_subject(question)

    # 细分章节（从原始数据中找）
    sub_chapter = item.get("sub_type", item.get("subject", item.get("专业", "")))
    if not sub_chapter:
        # 根据题目内容推测细分章节
        sub_chapter = guess_sub_chapter(question, subject)

    # chapter 格式：subject-细分章节
    chapter = f"{subject}-{sub_chapter}" if sub_chapter else subject

    explain = item.get("analysis", item.get("解析", item.get("explanation", item.get("explain", ""))))
    uuid = hashlib.md5((name + question).encode("utf-8")).hexdigest()[:16]

    return {
        "uuid": uuid,
        "chapter": chapter,
        "type": q_type,
        "question": question,
        "options": options,
        "answer": answer,
        "explain": explain,
        "sourceName": "CFLUE-" + name
    }


def guess_sub_chapter(question, subject):
    """根据题目内容推测细分章节"""
    if subject == "经济基础知识":
        if any(k in question for k in ["需求", "供给", "弹性", "消费者", "生产者", "成本", "市场结构", "价格", "效用"]):
            return "经济学基础"
        elif any(k in question for k in ["财政", "税收", "预算", "国债", "转移支付", "政府购买", "增值税", "所得税"]):
            return "财政"
        elif any(k in question for k in ["货币", "银行", "利率", "通货膨胀", "通货紧缩", "中央银行", "商业银行", "金融市场"]):
            return "货币与金融"
        elif any(k in question for k in ["统计", "抽样", "调查", "变量", "相关系数", "回归", "时间序列"]):
            return "统计"
        elif any(k in question for k in ["会计", "资产", "负债", "利润", "现金流量", "财务报表", "会计要素"]):
            return "会计"
        elif any(k in question for k in ["物权", "合同", "公司", "商标", "专利", "反垄断", "劳动法", "法律"]):
            return "法律"
        else:
            return "综合"
    elif subject == "工商管理":
        if any(k in question for k in ["战略", "SWOT", "竞争", "差异化", "集中化"]):
            return "企业战略"
        elif any(k in question for k in ["市场", "营销", "品牌", "定价", "渠道", "促销"]):
            return "市场营销"
        elif any(k in question for k in ["生产", "库存", "质量", "物流", "供应链"]):
            return "生产与物流"
        elif any(k in question for k in ["技术", "创新", "研发", "专利"]):
            return "技术创新"
        elif any(k in question for k in ["筹资", "投资", "财务", "现金流", "并购", "重组"]):
            return "财务与投融资"
        else:
            return "综合"
    elif subject == "人力资源":
        if any(k in question for k in ["规划", "需求", "供给", "预测"]):
            return "人力资源规划"
        elif any(k in question for k in ["招聘", "甄选", "面试", "录用"]):
            return "招聘与甄选"
        elif any(k in question for k in ["培训", "开发", "学习", "教育"]):
            return "培训与开发"
        elif any(k in question for k in ["绩效", "考核", "评价", "KPI"]):
            return "绩效管理"
        elif any(k in question for k in ["薪酬", "福利", "工资", "奖金"]):
            return "薪酬管理"
        elif any(k in question for k in ["劳动", "合同", "争议", "仲裁", "社保"]):
            return "劳动关系"
        else:
            return "综合"
    elif subject == "金融":
        if any(k in question for k in ["市场", "工具", "同业拆借", "票据", "债券", "股票"]):
            return "金融市场"
        elif any(k in question for k in ["商业", "贷款", "存款", "中间业务", "资产负债"]):
            return "商业银行"
        elif any(k in question for k in ["中央", "货币供给", "货币政策", "公开市场", "准备金"]):
            return "中央银行与货币政策"
        elif any(k in question for k in ["风险", "监管", "巴塞尔", "审慎"]):
            return "金融风险与监管"
        elif any(k in question for k in ["外汇", "汇率", "国际收支", "储备"]):
            return "国际金融"
        else:
            return "综合"
    elif subject == "财政税收":
        if any(k in question for k in ["公共", "财政", "支出", "收入", "职能"]):
            return "公共财政"
        elif any(k in question for k in ["税收", "税制", "增值税", "所得税", "消费税", "关税"]):
            return "税收制度"
        elif any(k in question for k in ["税务", "征管", "登记", "申报", "稽查", "代理"]):
            return "税务管理"
        elif any(k in question for k in ["预算", "决算", "国库", "政府采购"]):
            return "政府预算"
        else:
            return "综合"
    else:
        return "综合"


def main():
    print("="*60)
    print("CFLUE 题库自动下载转换器 v3（方案A：科目细分）")
    print("="*60)

    data = download_github_clone()
    if data is None:
        print("\n[*] 尝试查找本地文件...")
        data = load_local()

    if data is None or len(data) == 0:
        print("\n[!] 未能获取 CFLUE 数据")
        print("[*] 请手动下载数据文件后重命名为 cflue.json 或 train.jsonl 放到仓库根目录")
        print("[*] 下载地址: https://github.com/aliyun/cflue")
        sys.exit(1)

    print(f"\n[*] 原始数据: {len(data)} 条")

    questions = [q for q in (convert_item(item) for item in data) if q]
    print(f"[*] 经济师相关题目: {len(questions)} 条")

    seen = set()
    uniq = []
    for q in questions:
        if q["uuid"] not in seen:
            seen.add(q["uuid"])
            uniq.append(q)

    print(f"[*] 去重后: {len(uniq)} 条")

    # 统计科目分布
    subjects = {}
    chapters = {}
    for q in uniq:
        parts = q["chapter"].split("-", 1)
        subj = parts[0]
        subjects[subj] = subjects.get(subj, 0) + 1
        chap = parts[1] if len(parts) > 1 else "未分类"
        chapters[chap] = chapters.get(chap, 0) + 1

    print("\n[*] 科目分布:")
    for s, n in sorted(subjects.items(), key=lambda x: -x[1]):
        print(f"    {s}: {n} 题")

    print("\n[*] 细分章节分布（前10）:")
    for c, n in sorted(chapters.items(), key=lambda x: -x[1])[:10]:
        print(f"    {c}: {n} 题")

    output = {
        "title": "CFLUE-经济师题库（科目细分）",
        "count": len(uniq),
        "updateTime": __import__("datetime").datetime.now().isoformat(),
        "questions": uniq
    }
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n[OK] 已保存: {OUTPUT_FILE} ({len(uniq)} 题)")

    try:
        import csv
        csv_file = OUTPUT_FILE.replace(".json", ".csv")
        with open(csv_file, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["chapter", "type", "question", "optionA", "optionB", "optionC", "optionD", "answer", "explain"])
            for q in uniq:
                opts = q["options"] + [""] * (4 - len(q["options"]))
                writer.writerow([
                    q["chapter"], q["type"], q["question"],
                    opts[0], opts[1], opts[2], opts[3],
                    ",".join(str(a + 1) for a in q["answer"]),
                    q["explain"]
                ])
        print(f"[OK] 已导出 CSV: {csv_file}")
    except Exception as e:
        print(f"[!] CSV 导出失败: {e}")


if __name__ == "__main__":
    main()
