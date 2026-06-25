import os
import re

# 配置路径
SOURCE_DIR = "zubo"
RTP_TARGET_DIR = "py/rtp"

def get_sort_key(line):
    if ',' not in line: return (1, [], line)
    name = line.split(',')[0].upper()
    is_sd = 1 if any(x in name for x in ["SD", "标清"]) else 0
    core_name = re.sub(r'(HD|SD|4K|8K|高清|标清|超清|频道)$', '', name).strip()
    parts = [int(s) if s.isdigit() else s for s in re.split(r'(\d+)', core_name)]
    return (is_sd, parts, name)

def extract_and_classify():
    if not os.path.exists(RTP_TARGET_DIR):
        os.makedirs(RTP_TARGET_DIR, exist_ok=True)

    storage = {}
    
    if not os.path.exists(SOURCE_DIR) or not os.listdir(SOURCE_DIR):
        print(f"❌ 错误: 目录 {SOURCE_DIR} 不存在或为空")
        return

    for filename in os.listdir(SOURCE_DIR):
        if not filename.endswith(".m3u"): continue
        
        with open(os.path.join(SOURCE_DIR, filename), 'r', encoding='utf-8') as f:
            current_group = "未知"
            current_name = "未知"
            
            for line in f:
                line = line.strip()
                if not line: continue
                
                if line.startswith("#EXTINF:"):
                    # --- 改进点：过滤掉 IP 和 端口 ---
                    group_match = re.search(r'group-title="(.*?)"', line)
                    if group_match:
                        raw_group = group_match.group(1).replace(" ", "")
                        # 正则逻辑：只保留中文字符。
                        # 如果你想保留"北京联通"，它会过滤掉后面的 _123.112...
                        clean_group = "".join(re.findall(r'[\u4e00-\u9fa5]+', raw_group))
                        current_group = clean_group if clean_group else "其他"
                    
                    if "," in line:
                        current_name = line.split(",")[-1].strip()
                
                elif "/rtp/" in line:
                    rtp_addr = line.split("/rtp/")[-1].strip()
                    rtp_url = f"rtp://{rtp_addr}"
                    
                    if current_group not in storage:
                        storage[current_group] = {}
                    
                    # 自动去重：如果同一个 RTP 地址在同一个省份出现多次，只保留一个
                    if rtp_url not in storage[current_group]:
                        storage[current_group][rtp_url] = []
                    
                    storage[current_group][rtp_url].append(current_name)

    count = 0
    for group, rtp_map in storage.items():
        processed = []
        for url, names in rtp_map.items():
            # 名字去重与优化
            best_name = sorted(names, key=len)[0]
            best_name = re.sub(r'(HD|高清)$', '', best_name, flags=re.IGNORECASE).strip()
            processed.append(f"{best_name},{url}")

        processed.sort(key=get_sort_key)
        
        # 写入文件（现在文件名将只是：北京联通.txt）
        with open(os.path.join(RTP_TARGET_DIR, f"{group}.txt"), 'w', encoding='utf-8') as f:
            f.write("\n".join(processed) + "\n")
        count += 1

    print(f"✅ 处理完成！已按【地区运营商】合并生成 {count} 个文件。")

if __name__ == "__main__":
    extract_and_classify()
