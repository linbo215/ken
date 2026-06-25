import os
import re

# ================= 配置区 ================
SOURCE_DIR = "hotel"      # 酒店原始 M3U 存放目录
TARGET_DIR = "py/hotel"     # 规律总结存放目录
MAPPING_LOG = "py/hotel/酒店提取日志.txt"

def get_unique_filename(base_path):
    """如果文件已存在，自动增加数字后缀"""
    if not os.path.exists(base_path):
        return base_path
    name, ext = os.path.splitext(base_path)
    counter = 1
    while os.path.exists(f"{name}_{counter}{ext}"):
        counter += 1
    return f"{name}_{counter}{ext}"

def extract_id_from_url(url):
    """从 URL 中提取频道数字 ID (例如 0001_1 或 0002)"""
    # 匹配类似 /live/0001_1.m3u8 或 /live/123.m3u8 中的数字
    match = re.search(r'/live/(\w+)\.m3u8', url)
    return match.group(1) if match else "未知ID"

def process_hotel_rules():
    if not os.path.exists(TARGET_DIR):
        os.makedirs(TARGET_DIR, exist_ok=True)

    if not os.path.exists(SOURCE_DIR):
        print(f"错误: 找不到源目录 {SOURCE_DIR}")
        return

    for filename in os.listdir(SOURCE_DIR):
        if not filename.endswith(".m3u"):
            continue
        
        file_path = os.path.join(SOURCE_DIR, filename)
        # 提取当前文件的 IP
        ip_match = re.search(r'(\d+\.\d+\.\d+\.\d+)', filename)
        ip_addr = ip_match.group(1) if ip_match else "UnknownIP"

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 正则匹配
            pattern = re.compile(r'#EXTINF:-1.*?group-title="(.*?)",(.*?)\n(http.*)')
            matches = pattern.findall(content)

            if not matches:
                continue

            # 确定生成的分类文件名 (例如: 河南电信.txt)
            info_sample = matches[0][0]
            category_name = info_sample.split()[-1] if info_sample.split() else "酒店源"
            
            # 准备本次提取的数据列表
            results = []
            results.append(f"数据来源 IP: {ip_addr}")
            results.append(f"详细描述: {info_sample}")
            results.append("-" * 50)
            results.append(f"{'频道名':<15} | {'数字ID':<10} | {'完整链接及Key'}")

            for info, ch_name, url in matches:
                ch_id = extract_id_from_url(url)
                # 提取完整 URL（含 Key 信息）
                results.append(f"{ch_name.strip():<15} | {ch_id:<10} | {url.strip()}")

            # 写入文件，处理重名
            base_target = os.path.join(TARGET_DIR, f"{category_name}.txt")
            final_target = get_unique_filename(base_target)
            
            with open(final_target, 'w', encoding='utf-8') as f:
                f.write("\n".join(results))
            
            print(f"✅ 已生成规律文件: {os.path.basename(final_target)}")

        except Exception as e:
            print(f"处理文件 {filename} 出错: {e}")

if __name__ == "__main__":
    process_hotel_rules()
