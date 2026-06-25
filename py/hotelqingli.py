import os
import re
import requests
import time
import sys

# ===============================
# 配置区
# ===============================
M3U_DIR = "hotel"
HISTORY_FILE = os.path.join(M3U_DIR, "hotel_history.txt")
SAMPLE_COUNT = 3
CHECK_TIMEOUT = 10
HEADERS = {"User-Agent": "Mozilla/5.0"}

def check_link(url):
    """检测单个直播源链接"""
    try:
        # stream=True 配合实时读取少量字节，判断是否真正有流
        response = requests.get(url, headers=HEADERS, timeout=CHECK_TIMEOUT, stream=True)
        return response.status_code == 200
    except:
        return False

def is_m3u_alive(file_path):
    """判断 m3u 文件是否还有效"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        links = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', content)
        if not links: return False
        
        # 顺序抽测，只要有一个通了就返回 True
        for link in links[:SAMPLE_COUNT]:
            if check_link(link):
                return True
        return False
    except:
        return False

def main():
    if not os.path.exists(M3U_DIR):
        print(f"❌ 目录 {M3U_DIR} 不存在")
        return

    print(f"🔍 开始清理酒店源 (目录: {M3U_DIR})...")
    files = [f for f in os.listdir(M3U_DIR) if f.endswith(".m3u")]
    
    removed_ips = []
    removed_count = 0

    for filename in files:
        # 实时打印正在处理的文件名，不换行
        sys.stdout.write(f"📡 正在检测: {filename} ... ")
        sys.stdout.flush()

        file_path = os.path.join(M3U_DIR, filename)
        if not is_m3u_alive(file_path):
            # 提取 IP
            parts = filename.split('_')
            if len(parts) >= 5:
                ip = ".".join(parts[-5:-1])
                removed_ips.append(ip)
            
            os.remove(file_path)
            sys.stdout.write("❌ 失效 (已删除)\n")
            removed_count += 1
        else:
            sys.stdout.write("✅ 有效\n")
        sys.stdout.flush()
        # 稍微停顿一下，防止请求过快
        time.sleep(0.5)

    # --- 同步清理黑名单 ---
    if removed_ips and os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            for line in lines:
                if not any(ip in line for ip in removed_ips):
                    f.write(line)
        print(f"♻️  同步清理黑名单记录: {len(removed_ips)} 条")

    print(f"\n✨ 清理完成！共删除 {removed_count} 个失效文件。")

if __name__ == "__main__":
    main()
