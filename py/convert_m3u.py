import requests
import re
from collections import OrderedDict

# --- 配置区 ---
M3U_URL = "https://raw.githubusercontent.com/yubaomo02/LIVE/refs/heads/main/zubo/zuboall.m3u"
OUTPUT_FILE = "live.txt"

# 频道分类逻辑
CATEGORIES = OrderedDict([
    ("央视频道", ["CCTV1", "CCTV2", "CCTV3", "CCTV4", "CCTV4欧洲", "CCTV4美洲", "CCTV5", "CCTV5+", "CCTV6", "CCTV7", "CCTV8", "CCTV9", "CCTV10", "CCTV11", "CCTV12", "CCTV13", "CCTV14", "CCTV15", "CCTV16", "CCTV17", "CCTV4K", "CCTV8K", "兵器科技", "风云音乐", "风云足球", "风云剧场", "怀旧剧场", "第一剧场", "女性时尚", "世界地理", "央视台球", "高尔夫网球", "央视文化精品", "卫生健康", "电视指南"]),
    ("卫视频道", ["湖南卫视", "浙江卫视", "江苏卫视", "东方卫视", "深圳卫视", "北京卫视", "广东卫视", "广西卫视", "东南卫视", "海南卫视", "河北卫视", "河南卫视", "湖北卫视", "江西卫视", "四川卫视", "重庆卫视", "贵州卫视", "云南卫视", "天津卫视", "安徽卫视", "山东卫视", "辽宁卫视", "黑龙江卫视", "吉林卫视", "内蒙古卫视", "宁夏卫视", "山西卫视", "陕西卫视", "甘肃卫视", "青海卫视", "新疆卫视", "西藏卫视", "三沙卫视", "山东教育卫视", "中国教育1台", "中国教育2台", "中国教育3台", "中国教育4台", "早期教育"]),
    ("数字频道", ["CHC动作电影", "CHC家庭影院", "CHC影迷电影", "淘电影", "淘精彩", "淘剧场", "淘4K", "淘娱乐", "淘BABY", "淘萌宠", "重温经典", "星空卫视", "ChannelV", "凤凰卫视中文台", "凤凰卫视资讯台", "凤凰卫视香港台", "凤凰卫视电影台", "求索纪录", "求索科学", "求索生活", "求索动物", "纪实人文", "金鹰纪实", "纪实科教", "睛彩青少", "睛彩竞技", "睛彩篮球", "睛彩广场舞", "魅力足球", "五星体育", "乐游", "生活时尚", "都市剧场", "欢笑剧场", "游戏风云", "金色学堂", "动漫秀场", "新动漫", "卡酷少儿", "金鹰卡通", "优漫卡通", "哈哈炫动", "嘉佳卡通","中国交通", "中国天气", "华数4K", "华数星影", "华数动作影院", "华数喜剧影院", "华数家庭影院", "华数经典电影", "华数热播剧场", "华数碟战剧场","华数军旅剧场", "华数城市剧场", "华数武侠剧场", "华数古装剧场", "华数魅力时尚", "华数少儿动画", "华数动画"]),
    ("4K频道", ["东方卫视4K","浙江卫视4K","江苏卫视4K","北京卫视4K","湖南卫视4K","广东卫视4K","四川卫视4K","深圳卫视4K","山东卫视4K","欢笑剧场4K"]),
    ("湖北", ["湖北公共新闻", "湖北经视频道", "湖北综合频道", "湖北垄上频道", "湖北影视频道", "湖北生活频道", "湖北教育频道", "武汉新闻综合", "武汉电视剧", "武汉科技生活","武汉文体频道", "武汉教育频道", "阳新综合", "房县综合", "蔡甸综合"]),
    ("安徽", ["安徽经济生活","安徽公共频道","安徽国际频道","安徽农业科教","安徽影视频道","安徽综艺体育","安庆经济生活","安庆新闻综合"])
])

def clean_suffix(suffix):
    """
    清洗后缀的核心逻辑：
    利用正则去掉下划线开头的数字、点号组成的 IP 和端口信息
    """
    if not suffix: return ""
    # 匹配 _ 后面跟着数字、点或下划线的情况，例如 _114.243.96.9_8888 或 _114_243_96_9
    cleaned = re.sub(r'_[0-9\._]+$', '', suffix)
    return cleaned.strip()

def parse_m3u(content):
    results = []
    lines = content.split('\n')
    for i in range(len(lines)):
        line = lines[i].strip()
        if line.startswith("#EXTINF:"):
            # 提取 group-title
            suffix = ""
            group_match = re.search(r'group-title="(.*?)"', line)
            if group_match:
                suffix = group_match.group(1)
            
            # 清洗后缀，去掉 ID 和端口
            final_suffix = clean_suffix(suffix)
            
            name = line.split(',')[-1].strip()
            
            if i + 1 < len(lines):
                url = lines[i+1].strip()
                if url.startswith("http"):
                    results.append({
                        "name": name, 
                        "url": url, 
                        "suffix": final_suffix
                    })
    return results

def process():
    try:
        r = requests.get(M3U_URL, timeout=30)
        r.encoding = 'utf-8'
        content = r.text
    except: return

    all_channels = parse_m3u(content)
    output_lines = []

    for cat_name, channel_list in CATEGORIES.items():
        matched_results = []
        for target_name in channel_list:
            for channel in all_channels:
                # 模糊名匹配
                clean_name = re.sub(r'\(.*?\)|\[.*?\]|HD|高清|标清|超清', '', channel['name']).strip()
                if clean_name == target_name:
                    # 拼接：频道名,URL$北京联通
                    line = f"{channel['name']},{channel['url']}${channel['suffix']}"
                    matched_results.append(line)
        
        if matched_results:
            output_lines.append(f"{cat_name},#genre#")
            # 去重并保持顺序
            unique_results = list(dict.fromkeys(matched_results))
            output_lines.extend(unique_results)
            output_lines.append("")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(output_lines))
    print(f"✅ 处理完成，后缀已精简。")

if __name__ == "__main__":
    process()
