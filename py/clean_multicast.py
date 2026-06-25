import os

# ================= 配置区 =================
HOTEL_DIR = "./hotel"
# 组播特征：rtp协议，或者 224-239 开头的组播IP段
MULTICAST_FEATURES = [
    "rtp://",
    "224.", "225.", "226.", "227.", "228.", "229.",
    "230.", "231.", "232.", "233.", "234.", "235.", "236.", "237.", "238.", "239."
]
# ==========================================

def clean():
    print("🧹 开始清理混入的组播文件...")
    if not os.path.exists(HOTEL_DIR):
        print("❌ 文件夹不存在")
        return

    deleted_count = 0
    files = [f for f in os.listdir(HOTEL_DIR) if f.lower().endswith(".m3u")]
    
    for file in files:
        file_path = os.path.join(HOTEL_DIR, file)
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                
            # 检查是否包含任何组播特征
            is_multicast = any(feature in content for feature in MULTICAST_FEATURES)
            
            if is_multicast:
                os.remove(file_path)
                print(f"🗑️ 已删除组播文件: {file}")
                deleted_count += 1
        except Exception as e:
            print(f"⚠️ 处理 {file} 出错: {e}")

    print(f"\n✨ 清理完成！共删除 {deleted_count} 个组播文件。")

if __name__ == "__main__":
    clean()
