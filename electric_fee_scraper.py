import requests
from bs4 import BeautifulSoup
import json
import os
import sys
import time
from datetime import datetime, timedelta
import re

# --- 全局配置 ---
BASE_URL = "https://electricfee.vip.cpolar.cn"
LOGIN_URL = f"{BASE_URL}/default.aspx"
RESULTS_URL = f"{BASE_URL}/usedRecord.aspx"
JSON_DATABASE_FILE = "electricity_data_single_room.json"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Origin': BASE_URL,
}
REQUEST_DELAY = 0.1

# --- 辅助函数 (无变化) ---
def get_hidden_inputs(soup):
    form_data = {}
    for input_tag in soup.find_all('input', {'type': 'hidden'}):
        name, value = input_tag.get('name'), input_tag.get('value', '')
        if name: form_data[name] = value
    return form_data

def parse_options(select_tag):
    options = {}
    if not select_tag: return options
    for option in select_tag.find_all('option')[1:]:
        value, text = option.get('value'), option.text.strip()
        if value and text:
            options[text] = value
    return options

def get_user_choice(prompt, options_list):
    if not options_list:
        print(f"错误：没有可用的'{prompt}'选项。")
        return None
    print(f"\n--- 请选择 {prompt} ---")
    display_list = list(options_list)
    for i, option_text in enumerate(display_list):
        print(f"{i + 1}: {option_text}")
    while True:
        try:
            choice = int(input(f"请输入{prompt}的编号 (1-{len(display_list)}): "))
            if 1 <= choice <= len(display_list):
                return display_list[choice - 1]
            else:
                print("输入无效。")
        except ValueError:
            print("请输入一个数字。")

def _parse_records_from_soup(soup):
    records = []
    rows = soup.select('table.dataTable tr.contentLine')
    for row in rows:
        cols = [td.text.strip() for td in row.find_all('td')]
        if len(cols) == 4:
            records.append({
                "date": cols[0], "meter_name": cols[1],
                "usage": cols[2], "price": cols[3]
            })
    return records

# --- 核心爬取功能 (已修改) ---
def scrape_room_data(session, building_value, floor_value, room_value, form_data):
    """
    爬取一个指定房间过去90天的所有分页数据和剩余电量。
    返回: (记录列表, 剩余电量字符串) 的元组
    """
    try:
        payload_select_room = {**form_data, 'drlouming': building_value, 'drceng': floor_value,
                               'drfangjian': room_value, 'radio': 'usedR',
                               'ImageButton1.x': '30', 'ImageButton1.y': '10'}
        payload_select_room.pop('__EVENTTARGET', None)
        res_after_select = session.post(LOGIN_URL, data=payload_select_room, headers={'Referer': LOGIN_URL})
        res_after_select.raise_for_status()

        soup_results_page = BeautifulSoup(res_after_select.text, 'html.parser')
        results_page_form_data = get_hidden_inputs(soup_results_page)
        
        today = datetime.now()
        ninety_days_ago = today - timedelta(days=90)
        final_payload = {**results_page_form_data, 'txtstart': ninety_days_ago.strftime('%Y-%m-%d'),
                         'txtend': today.strftime('%Y-%m-%d'), 'btnser': '查询'}
                         
        final_response = session.post(RESULTS_URL, data=final_payload, headers={'Referer': RESULTS_URL})
        final_response.raise_for_status()

        final_soup = BeautifulSoup(final_response.text, 'html.parser')
        
        # ==================== 修改：只解析总剩余电量 ====================
        total_remaining = None
        h6_tag = final_soup.find('h6')
        if h6_tag:
            spans = h6_tag.find_all('span', class_='number orange')
            # 确保有三个span，我们取最后一个
            if len(spans) == 3:
                total_remaining = spans[2].text.strip()
        # ==========================================================

        # 解析用量记录
        all_records = _parse_records_from_soup(final_soup)
        
        # 处理分页
        total_pages = 1
        pageer_div = final_soup.find('div', class_='pageer')
        if pageer_div:
            match = re.search(r'共\s*(\d+)\s*页', pageer_div.text)
            if match:
                total_pages = int(match.group(1))

        if total_pages > 1:
            for page_num in range(2, total_pages + 1):
                time.sleep(REQUEST_DELAY)
                next_page_url = f"{RESULTS_URL}?p={page_num}"
                res_page = session.get(next_page_url, headers={'Referer': RESULTS_URL})
                res_page.raise_for_status()
                soup_page = BeautifulSoup(res_page.text, 'html.parser')
                records_from_page = _parse_records_from_soup(soup_page)
                all_records.extend(records_from_page)
        
        print(f"    [成功] 获取 {len(all_records)} 条用量记录 和 剩余电量信息。")
        return all_records, total_remaining

    except Exception as e:
        print(f"    [失败] 爬取过程中发生错误: {e}")
        return None, None

# --- 交互式爬取功能 (保存逻辑已修改) ---
def scrape_single_room_interactive():
    session = requests.Session()
    session.headers.update(HEADERS)
    
    try:
        # ... (选择房间的逻辑不变) ...
        print("正在获取楼栋列表...")
        response = session.get(LOGIN_URL)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        initial_form_data = get_hidden_inputs(soup)
        buildings = parse_options(soup.find('select', {'id': 'drlouming'}))
        building_text = get_user_choice("楼栋", buildings.keys())
        if not building_text: return
        building_value = buildings[building_text]

        print(f"正在获取 '{building_text}' 的楼层列表...")
        res_floor = session.post(LOGIN_URL, data={**initial_form_data, '__EVENTTARGET': 'drlouming', 'drlouming': building_value})
        soup_floor = BeautifulSoup(res_floor.text, 'html.parser')
        floor_form_data = get_hidden_inputs(soup_floor)
        floors = parse_options(soup_floor.find('select', {'id': 'drceng'}))
        floor_text = get_user_choice("楼层", floors.keys())
        if not floor_text: return
        floor_value = floors[floor_text]

        print(f"正在获取 '{building_text} - {floor_text}' 的房间列表...")
        res_room = session.post(LOGIN_URL, data={**floor_form_data, '__EVENTTARGET': 'drceng', 'drlouming': building_value, 'drceng': floor_value})
        soup_room = BeautifulSoup(res_room.text, 'html.parser')
        room_form_data = get_hidden_inputs(soup_room)
        rooms = parse_options(soup_room.find('select', {'id': 'drfangjian'}))
        room_text = get_user_choice("房间", rooms.keys())
        if not room_text: return
        room_value = rooms[room_text]

        print(f"\n准备爬取: {building_text} - {floor_text} - {room_text}")
        # ==================== 修改：接收单个返回值 ====================
        records, remaining_electricity = scrape_room_data(session, building_value, floor_value, room_value, room_form_data)

        if records is not None:
            # ==================== 修改：构建新的保存结构 ====================
            info_data = {
                "building": building_text,
                "floor": floor_text,
                "room": room_text,
                "scrape_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            # 如果爬取到了剩余电量，就添加到info字典中
            if remaining_electricity is not None:
                info_data["remaining_electricity"] = remaining_electricity

            data_to_save = {
                "info": info_data,
                "records": records
            }
            # ==========================================================
            
            with open(JSON_DATABASE_FILE, 'w', encoding='utf-8') as f:
                json.dump(data_to_save, f, ensure_ascii=False, indent=4)
            print(f"数据库 '{JSON_DATABASE_FILE}' 已被更新为该房间的数据！")

    except requests.exceptions.RequestException as e:
        print(f"网络请求失败: {e}", file=sys.stderr)
    except Exception as e:
        print(f"发生未知错误: {e}", file=sys.stderr)

# --- 查询功能 (已修改为显示单个剩余电量) ---
def query_local_data():
    if not os.path.exists(JSON_DATABASE_FILE):
        print(f"错误: 数据库文件 '{JSON_DATABASE_FILE}' 不存在。请先执行选项1爬取数据。")
        return

    try:
        with open(JSON_DATABASE_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        print(f"错误: '{JSON_DATABASE_FILE}' 文件不存在、格式不正确或已损坏。")
        return

    info = data.get("info", {})
    records = data.get("records", [])
    
    building = info.get("building", "未知楼栋")
    floor = info.get("floor", "未知楼层")
    room = info.get("room", "未知房间")
    scrape_time = info.get("scrape_time", "未知时间")

    print(f"\n--- 查询结果: {building} - {floor} - {room} ---")
    print(f"--- (数据更新于: {scrape_time}) ---")

    # ==================== 修改：只显示总剩余电量 ====================
    remaining = info.get("remaining_electricity")

    if remaining is not None:
        print("\n【当前剩余电量】")
        print(f"  剩余电量: {remaining} 度\n")
    # ==========================================================
        
    if not records:
        print("数据库中没有找到用量记录。")
        return
        
    print("【近期用量记录】")
    print("-" * 75)
    print(f"{'日期':<12} | {'电表名称':<22} | {'用量(度/吨)':<15} | {'单价(元/度/吨)':<15}")
    print("-" * 75)
    for r in records:
        print(f"{r['date']:<12} | {r['meter_name']:<22} | {r['usage']:<15} | {r['price']:<15}")
    print("-" * 75)
    print(f"共找到 {len(records)} 条用量记录。")

# --- 主程序入口 (无变化) ---
def main():
    while True:
        print("\n===== 电费查询系统 (单房间数据库版) =====")
        print("1. 更新/爬取指定房间的数据(含剩余电量, 近90天)")
        print("2. 查询本地已保存的数据")
        print("3. 退出")
        choice = input("请输入你的选择 (1/2/3): ")

        if choice == '1':
            start_time = time.time()
            scrape_single_room_interactive()
            end_time = time.time()
            print(f"\n本次操作耗时: {end_time - start_time:.2f} 秒")
        elif choice == '2':
            query_local_data()
        elif choice == '3':
            print("感谢使用，再见！")
            break
        else:
            print("无效输入。")

if __name__ == "__main__":
    main()