import os
import re
import requests
import time

# ===============================
# 配置区
# ===============================
ZUBO_DIR = "zubo"
# 明确不参与清理的文件名
EXCLUDE_FILES = ["zuboall.m3u"] 

SAMPLE_COUNT = 3               # 每个文件抽测 3 个频道
CHECK_TIMEOUT = 15             # 连接超时 15s
STREAM_READ_TIMEOUT = 10       # 读取流数据等待 10s
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

def check_zubo_stream(url):
    """
    深度检测：连通性 + 缓冲推流检测
    """
    try:
        # 1. 尝试建立连接
        response = requests.get(url, headers=HEADERS, timeout=CHECK_TIMEOUT, stream=True)
        
        if response.status_code == 200:
            # 2. 核心：给流一点起步时间（2秒）
            time.sleep(2) 
            
            # 3. 尝试读取数据块
            # 只要能在 10s 内读到任何内容，说明此源在推流，即为有效
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    return True 
                break 
        return False
    except:
        return False
    finally:
        try:
            response.close()
        except:
            pass

def is_zubo_file_alive(file_path):
    """判断组播 m3u 文件是否有效"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # 提取链接
        links = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', content)
        if not links:
            return False
        
        # 顺序抽测样本，只要有一个频道通了，整个 IP 文件就保留
        test_links = links[:SAMPLE_COUNT]
        for link in test_links:
            if check_zubo_stream(link):
                return True
            time.sleep(1.5) # 频道间稍作停顿
            
        return False
    except Exception as e:
        print(f" ⚠️ 读档异常: {e}", end="")
        return False

def main():
    if not os.path.exists(ZUBO_DIR):
        print(f"❌ 目录 {ZUBO_DIR} 不存在")
        return

    print(f"🔍 开始深度维护组播源目录: {ZUBO_DIR}")
    # 获取所有 m3u 文件，但排除掉 zuboall.m3u
    files = [f for f in os.listdir(ZUBO_DIR) if f.endswith(".m3u") and f not in EXCLUDE_FILES]
    
    # 打印一下排除信息，心里有底
    for ex_file in EXCLUDE_FILES:
        if os.path.exists(os.path.join(ZUBO_DIR, ex_file)):
            print(f"🛡️  已保护文件: {ex_file} (跳过清理)")

    removed_count = 0
    for filename in files:
        file_path = os.path.join(ZUBO_DIR, filename)
        print(f"📡 正在检测状态: {filename} ... ", end="", flush=True)
        
        if not is_zubo_file_alive(file_path):
            print("❌ 无推流 (已清理)")
            os.remove(file_path)
            removed_count += 1
        else:
            print("✅ 正常")
        
        # 文件间冷却，防止请求太密集
        time.sleep(2)

    print(f"\n✨ 清理工作结束！共移除 {removed_count} 个失效源文件。")

if __name__ == "__main__":
    main()
