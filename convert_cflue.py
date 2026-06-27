#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
====================================================
CFLUE 题库自动下载转换器
====================================================
功能：
  1. 从 HuggingFace / ModelScope 自动下载 CFLUE 数据集
  2. 提取经济师相关题目（中级/初级/高级经济师）
  3. 转换为刷题系统标准 JSON 格式
  4. 去重、格式化、输出固定文件名

依赖：
  pip install datasets huggingface_hub requests

用法：
  python convert_cflue.py
  输出：questions.json（直接可被刷题系统引用）
"""

import json
import ast
import sys
import os
import re
import hashlib

# 尝试导入 datasets，如果失败则降级为 requests 直接下载
try:
    from datasets import load_dataset
    HAS_DATASETS = True
except ImportError:
    HAS_DATASETS = False
    print("[!] datasets 库未安装，尝试用 requests 直接下载...")

try:
    import requests
except ImportError:
    print("[!] 缺少 requests，请安装: pip install requests")
    raise SystemExit(1)

OUTPUT_FILE = "questions.json"

# CFLUE 在 HuggingFace 上的数据集名称
HF_DATASET_NAME = "tongyi_dianjin/CFLUE"


def download_via_datasets():
    """使用 huggingface datasets 库下载"""
    if not HAS_DATASETS:
        return None
    try:
        print("[*] 尝试从 HuggingFace 下载 CFLUE...")
        # 只下载 knowledge 部分（选择题）
        ds = load_dataset(HF_DATASET_NAME, "knowledge", split="train", trust_remote_code=True)
        data = []
        for item in ds:
            data.append(dict(item))
        print(f"[+] HuggingFace 下载成功: {len(data)} 条")
        return data
    except Exception as e:
        print(f"[!] HuggingFace 下载失败: {e}")
        return None


def download_via_requests():
    """降级：尝试从已知 URL 直接下载（如果数据集有公开直链）"""
    # CFLUE 数据通常需要通过 git-lfs 或 datasets 库下载
    # 这里提供一个备选方案：如果用户已手动下载到本地
    local_files = [
        "cflue_knowledge.json",
        "cflue.json",
        "data.json",
        "train.json"
    ]
    for f in local_files:
        if os.path.exists(f):
            print(f"[*] 发现本地文件: {f}")
            with open(f, "r", encoding="utf-8") as fp:
                return json.load(fp)
    return None


def parse_choices(choices_str):
    """解析 CFLUE 的 choices 字符串"""
    if isinstance(choices_str, dict):
        return [choices_str.get(k, "") for k in sorted(choices_str.keys())]
    if isinstance(choices_str, list):
        return choices_str
    # 字符串形式: "{'A': '...', 'B': '...'}"
    try:
        d = ast.literal_eval(choices_str)
        if isinstance(d, dict):
            return [d.get(k, "") for k in sorted(d.keys())]
    except:
        pass
    # 兜底：正则提取
    matches = re.findall(r"['\"]([A-D])['\"]\s*:\s*['\"](.*?)['\"](?:,|\})", choices_str)
    if matches:
        return [m[1] for m in sorted(matches, key=lambda x: x[0])]
    return []


def convert_item(item):
    """将 CFLUE 单条数据转换为标准格式"""
    name = item.get("名称", item.get("name", item.get("exam_type", "")))

    # 只保留经济师相关
    if "经济师" not in name:
        return None

    question = item.get("question", item.get("题目", item.get("q", "")))
    if not question:
        return None

    # 解析选项
    options = parse_choices(item.get("choices", item.get("选项", item.get("options", {}))))
    if len(options) < 2:
        return None

    # 解析答案
    ans = item.get("answer", item.get("答案", item.get("correct", "A")))
    if isinstance(ans, int):
        answer = [ans]
    elif isinstance(ans, str) and len(ans) == 1 and ans.upper() in "ABCD":
        answer = [ord(ans.upper()) - ord("A")]
    elif isinstance(ans, list):
        answer = [ord(a.upper()) - ord("A") if isinstance(a, str) and len(a) == 1 else int(a) for a in ans]
    else:
        answer = [0]  # 兜底

    # 题型判断
    task = item.get("task", item.get("题型", ""))
    q_type = "multiple" if "多" in task or len(answer) > 1 else "single"

    # 章节映射
    chapter_map = {
        "中级经济师": "中级经济师",
        "初级经济师": "初级经济师",
        "高级经济师": "高级经济师",
    }
    chapter = "经济师"
    for k, v in chapter_map.items():
        if k in name:
            chapter = v
            break

    # 子分类（如果有）
    sub = item.get("sub_type", item.get("subject", item.get("专业", "")))
    if sub:
        chapter += "-" + sub

    explain = item.get("analysis", item.get("解析", item.get("explanation", item.get("explain", ""))))

    # 生成 UUID
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


def main():
    # 1. 下载数据
    data = download_via_datasets()
    if data is None:
        data = download_via_requests()

    if data is None or len(data) == 0:
        print("[!] 未能获取 CFLUE 数据，请检查网络或手动下载后放置到本地")
        print("[*] 手动下载方法：")
        print("    1. 访问 https://modelscope.cn/datasets/tongyi_dianjin/CFLUE")
        print("    2. 下载 knowledge 部分数据")
        print("    3. 保存为 cflue.json 后重新运行此脚本")
        sys.exit(1)

    print(f"[*] 原始数据: {len(data)} 条")

    # 2. 转换
    questions = []
    for item in data:
        q = convert_item(item)
        if q:
            questions.append(q)

    print(f"[*] 经济师相关题目: {len(questions)} 条")

    # 3. 去重（基于 uuid）
    seen = set()
    uniq = []
    for q in questions:
        if q["uuid"] not in seen:
            seen.add(q["uuid"])
            uniq.append(q)

    print(f"[*] 去重后: {len(uniq)} 条")

    # 4. 统计
    chapters = {}
    for q in uniq:
        c = q["chapter"]
        chapters[c] = chapters.get(c, 0) + 1

    print("[*] 章节分布:")
    for c, n in sorted(chapters.items(), key=lambda x: -x[1]):
        print(f"    {c}: {n} 题")

    # 5. 输出
    output = {
        "title": "CFLUE-经济师题库",
        "count": len(uniq),
        "updateTime": __import__("datetime").datetime.now().isoformat(),
        "questions": uniq
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"[OK] 已保存: {OUTPUT_FILE} ({len(uniq)} 题)")

    # 6. 同时输出 CSV 方便查看
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
