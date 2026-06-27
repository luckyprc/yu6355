#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
====================================================
CFLUE 题库自动下载转换器 v2
====================================================
修复：
  - datasets 5.0.0 不再支持 trust_remote_code
  - HuggingFace 数据集名称可能不存在，改用多源下载
  - 增加 ModelScope 直链下载作为备选

依赖：
  pip install datasets requests

用法：
  python convert_cflue.py
  输出：questions.json
"""

import json
import ast
import sys
import os
import re
import hashlib
import requests

OUTPUT_FILE = "questions.json"

# 多源下载配置
SOURCES = [
    {
        "name": "HuggingFace datasets API",
        "type": "hf_api",
        "dataset": "tongyi_dianjin/CFLUE",
        "config": "knowledge",
        "split": "train"
    },
    {
        "name": "ModelScope 直链",
        "type": "ms_direct",
        "url": "https://www.modelscope.cn/api/v1/datasets/tongyi_dianjin/CFLUE/repo?Revision=master&FilePath=knowledge%2Ftrain.jsonl"
    },
    {
        "name": "HuggingFace parquet",
        "type": "hf_parquet",
        "url": "https://huggingface.co/datasets/tongyi_dianjin/CFLUE/resolve/main/knowledge/train-00000-of-00001.parquet"
    }
]


def download_hf_api(source):
    """使用 datasets 库从 HuggingFace 下载"""
    try:
        from datasets import load_dataset
        print(f"[*] 尝试从 HuggingFace 下载: {source['dataset']}")
        ds = load_dataset(source["dataset"], source["config"], split=source["split"])
        data = []
        for item in ds:
            data.append(dict(item))
        print(f"[+] HuggingFace 下载成功: {len(data)} 条")
        return data
    except Exception as e:
        print(f"[!] HuggingFace API 失败: {e}")
        return None


def download_direct(source):
    """使用 requests 直接下载 JSON/JSONL"""
    try:
        url = source["url"]
        print(f"[*] 尝试直接下载: {url[:60]}...")
        resp = requests.get(url, timeout=120, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        resp.raise_for_status()

        content = resp.text.strip()
        # 判断是 JSON 数组还是 JSONL
        if content.startswith("["):
            data = json.loads(content)
        else:
            # JSONL 格式，每行一个 JSON
            data = []
            for line in content.split("\n"):
                line = line.strip()
                if line:
                    data.append(json.loads(line))

        print(f"[+] 直接下载成功: {len(data)} 条")
        return data
    except Exception as e:
        print(f"[!] 直接下载失败: {e}")
        return None


def download_parquet(source):
    """下载 parquet 文件并解析"""
    try:
        import pandas as pd
        url = source["url"]
        print(f"[*] 尝试下载 parquet: {url[:60]}...")
        resp = requests.get(url, timeout=120)
        resp.raise_for_status()

        # 保存临时文件
        tmp = "/tmp/cflue.parquet"
        with open(tmp, "wb") as f:
            f.write(resp.content)

        df = pd.read_parquet(tmp)
        data = df.to_dict("records")
        print(f"[+] Parquet 解析成功: {len(data)} 条")
        return data
    except ImportError:
        print("[!] 缺少 pandas，跳过 parquet 解析")
        return None
    except Exception as e:
        print(f"[!] Parquet 下载失败: {e}")
        return None


def download_all():
    """按优先级尝试所有下载源"""
    for source in SOURCES:
        print(f"\n{'='*50}")
        print(f"[*] 尝试下载源: {source['name']}")

        if source["type"] == "hf_api":
            data = download_hf_api(source)
        elif source["type"] == "ms_direct":
            data = download_direct(source)
        elif source["type"] == "hf_parquet":
            data = download_parquet(source)
        else:
            data = None

        if data and len(data) > 0:
            return data

    return None


def load_local():
    """查找本地已有的数据文件"""
    local_files = [
        "cflue_knowledge.json",
        "cflue.json",
        "data.json",
        "train.json",
        "train.jsonl"
    ]
    for f in local_files:
        if os.path.exists(f):
            print(f"[*] 发现本地文件: {f}")
            with open(f, "r", encoding="utf-8") as fp:
                content = fp.read().strip()
                if content.startswith("["):
                    return json.loads(content)
                else:
                    return [json.loads(line) for line in content.split("\n") if line.strip()]
    return None


def parse_choices(choices_str):
    """解析 CFLUE 的 choices 字符串"""
    if isinstance(choices_str, dict):
        return [choices_str.get(k, "") for k in sorted(choices_str.keys())]
    if isinstance(choices_str, list):
        return choices_str
    try:
        d = ast.literal_eval(choices_str)
        if isinstance(d, dict):
            return [d.get(k, "") for k in sorted(d.keys())]
    except:
        pass
    matches = re.findall(r"['\"]([A-D])['\"]\s*:\s*['\"](.*?)['\"](?:,|\})", choices_str)
    if matches:
        return [m[1] for m in sorted(matches, key=lambda x: x[0])]
    return []


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

    chapter = "中级经济师" if "中级" in name else ("初级经济师" if "初级" in name else "高级经济师")
    sub = item.get("sub_type", item.get("subject", item.get("专业", "")))
    if sub:
        chapter += "-" + sub

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


def main():
    print("="*60)
    print("CFLUE 题库自动下载转换器 v2")
    print("="*60)

    # 1. 尝试多源下载
    data = download_all()

    # 2. 降级到本地文件
    if data is None:
        print("\n[*] 尝试查找本地文件...")
        data = load_local()

    if data is None or len(data) == 0:
        print("\n[!] 未能获取 CFLUE 数据")
        print("[*] 请手动下载数据文件后重命名为 cflue.json 或 train.jsonl 放到仓库根目录")
        print("[*] 下载地址: https://modelscope.cn/datasets/tongyi_dianjin/CFLUE")
        sys.exit(1)

    print(f"\n[*] 原始数据: {len(data)} 条")

    # 3. 转换
    questions = [q for q in (convert_item(item) for item in data) if q]
    print(f"[*] 经济师相关题目: {len(questions)} 条")

    # 4. 去重
    seen = set()
    uniq = []
    for q in questions:
        if q["uuid"] not in seen:
            seen.add(q["uuid"])
            uniq.append(q)

    print(f"[*] 去重后: {len(uniq)} 条")

    # 5. 统计
    chapters = {}
    for q in uniq:
        c = q["chapter"]
        chapters[c] = chapters.get(c, 0) + 1
    print("[*] 章节分布:")
    for c, n in sorted(chapters.items(), key=lambda x: -x[1]):
        print(f"    {c}: {n} 题")

    # 6. 输出 JSON
    output = {
        "title": "CFLUE-经济师题库",
        "count": len(uniq),
        "updateTime": __import__("datetime").datetime.now().isoformat(),
        "questions": uniq
    }
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n[OK] 已保存: {OUTPUT_FILE} ({len(uniq)} 题)")

    # 7. 输出 CSV
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
