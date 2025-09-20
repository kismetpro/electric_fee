import json
import os
import re
import time
from datetime import datetime, timedelta

from flask import Flask, request, jsonify, render_template
from flask_cors import CORS

import requests
from bs4 import BeautifulSoup

# --- 全局配置 ---
BASE_URL = "https://electricfee.vip.cpolar.cn"
LOGIN_URL = f"{BASE_URL}/default.aspx"
RESULTS_URL = f"{BASE_URL}/usedRecord.aspx"
# 获取当前文件 (app.py) 所在的目录的绝对路径
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
# 将 JSON 文件名与基础目录拼接成一个绝对路径
JSON_DATABASE_FILE = os.path.join(BASE_DIR, "electricity_data_single_room.json")
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Origin': BASE_URL,
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3',
    'Accept-Encoding': 'gzip, deflate',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Referer': BASE_URL,
}
REQUEST_DELAY = 0.1

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev'
CORS(app)

def get_hidden_inputs(soup):
    form_data = {}
    for input_tag in soup.find_all('input', {'type': 'hidden'}):
        name = input_tag.get('name')
        value = input_tag.get('value', '')
        if name:
            form_data[name] = value
    return form_data

def parse_options_for_api(select_tag):
    if not select_tag:
        return []
    options = []
    for option in select_tag.find_all('option')[1:]:
        value = option.get('value')
        text = option.text.strip()
        if value and text:
            options.append({"text": text, "value": value})
    return options

def _parse_records_from_soup(soup):
    records = []
    rows = soup.select('table.dataTable tr.contentLine')
    for row in rows:
        cols = [td.text.strip() for td in row.find_all('td')]
        if len(cols) == 4:
            records.append({
                "date": cols[0],
                "meter_name": cols[1],
                "usage": cols[2],
                "price": cols[3]
            })
    return records

def scrape_room_data(session, building_value, floor_value, room_value, form_data, start_date, end_date):
    print(f"Scrape params: building_value={building_value}, floor_value={floor_value}, room_value={room_value}, dates={start_date} to {end_date}")  # 添加日志：参数
    try:
        payload_select_room = {
            **form_data,
            'drlouming': building_value,
            'drceng': floor_value,
            'drfangjian': room_value,
            'radio': 'usedR',
            'ImageButton1.x': '30',
            'ImageButton1.y': '10'
        }
        payload_select_room.pop('__EVENTTARGET', None)

        print("Posting to select room...")  # 添加日志
        time.sleep(REQUEST_DELAY)
        res_after_select = session.post(LOGIN_URL, data=payload_select_room, headers={'Referer': LOGIN_URL})
        print(f"Select room response status: {res_after_select.status_code}")  # 添加日志：状态
        res_after_select.raise_for_status()

        soup_results_page = BeautifulSoup(res_after_select.text, 'html.parser')
        results_page_form_data = get_hidden_inputs(soup_results_page)

        final_payload = {
            **results_page_form_data,
            'txtstart': start_date,
            'txtend': end_date,
            'btnser': '查询'
        }

        print("Posting query to results...")  # 添加日志
        time.sleep(REQUEST_DELAY)
        final_response = session.post(RESULTS_URL, data=final_payload, headers={'Referer': RESULTS_URL})
        print(f"Results response status: {final_response.status_code}")  # 添加日志：状态
        final_response.raise_for_status()

        final_soup = BeautifulSoup(final_response.text, 'html.parser')

        # 解析剩余电量
        total_remaining = None
        h6_tag = final_soup.find('h6')
        if h6_tag:
            spans = h6_tag.find_all('span', class_='number orange')
            if len(spans) == 3:
                total_remaining = spans[2].text.strip()
        print(f"Parsed remaining: {total_remaining}")  # 添加日志：剩余电量

        all_records = _parse_records_from_soup(final_soup)

        # 处理分页
        total_pages = 1
        pageer_div = final_soup.find('div', class_='pageer')
        if pageer_div:
            match = re.search(r'共\s*(\d+)\s*页', pageer_div.text)
            if match:
                total_pages = int(match.group(1))

        print(f"Total pages: {total_pages}")  # 添加日志：分页

        if total_pages > 1:
            for page_num in range(2, total_pages + 1):
                time.sleep(REQUEST_DELAY)
                next_page_url = f"{RESULTS_URL}?p={page_num}"
                print(f"Fetching page {page_num}...")  # 添加日志
                res_page = session.get(next_page_url, headers={'Referer': RESULTS_URL})
                print(f"Page {page_num} status: {res_page.status_code}")  # 添加日志
                res_page.raise_for_status()
                soup_page = BeautifulSoup(res_page.text, 'html.parser')
                records_from_page = _parse_records_from_soup(soup_page)
                all_records.extend(records_from_page)

        print(f"Total records scraped: {len(all_records)}")  # 添加日志：总记录
        return all_records, total_remaining

    except Exception as e:
        print(f"爬取过程中发生错误: {e}")
        import traceback
        traceback.print_exc()  # 添加详细异常日志
        return None, None

def get_buildings(session, max_retries=3):
    for attempt in range(1, max_retries + 1):
        print(f"Getting buildings... (attempt {attempt}/{max_retries})")  # 添加日志
        time.sleep(REQUEST_DELAY * attempt)  # 递增延迟
        try:
            response = session.get(LOGIN_URL)
            print(f"Buildings GET status: {response.status_code}, final URL: {response.url}")  # 简化日志
            print(f"Response headers: {dict(response.headers)}")  # 新增：打印响应头，检查重定向或内容类型
            if response.status_code >= 400:
                print(f"Status >=400, text preview: {response.text[:500]}")  # 错误预览
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            select = soup.find('select', {'id': 'drlouming'})
            print(f"Select tag found: {select is not None}, tag content if exists: {select.prettify()[:300] if select else 'None'}")  # 新增：详细 select 信息
            if not select:
                print(f"No select tag found, page preview: {soup.get_text()[:500]}")  # 修复格式
                print(f"Full HTML length: {len(response.text)}, contains 'drlouming': {'drlouming' in response.text}")  # 新增：检查关键字
                if attempt < max_retries:
                    print("Retrying...")
                    continue
            options = parse_options_for_api(select)
            print(f"Raw options from select: {[opt.get('value') for opt in select.find_all('option')]}")  # 新增：原始 options 值
            print(f"Parsed {len(options)} building options")  # 添加日志：解析结果
            return options
        except requests.exceptions.HTTPError as e:
            print(f"HTTP Error on attempt {attempt}: {e}, response preview: {response.text[:500] if 'response' in locals() else 'No response'}")
            if attempt < max_retries:
                continue
            raise
        except Exception as e:
            print(f"Unexpected error on attempt {attempt}: {e}")
            if attempt < max_retries:
                continue
            raise
    return []  # 如果所有重试失败，返回空

def get_floors(session, building_value):
    time.sleep(REQUEST_DELAY)
    response = session.get(LOGIN_URL)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')
    initial_form_data = get_hidden_inputs(soup)

    time.sleep(REQUEST_DELAY)
    res_floor = session.post(LOGIN_URL, data={**initial_form_data, '__EVENTTARGET': 'drlouming', 'drlouming': building_value})
    res_floor.raise_for_status()

    soup_floor = BeautifulSoup(res_floor.text, 'html.parser')
    select = soup_floor.find('select', {'id': 'drceng'})
    return parse_options_for_api(select)

def get_rooms(session, building_value, floor_value):
    time.sleep(REQUEST_DELAY)
    response = session.get(LOGIN_URL)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')
    initial_form_data = get_hidden_inputs(soup)

    time.sleep(REQUEST_DELAY)
    res_floor = session.post(LOGIN_URL, data={**initial_form_data, '__EVENTTARGET': 'drlouming', 'drlouming': building_value})
    res_floor.raise_for_status()

    soup_floor = BeautifulSoup(res_floor.text, 'html.parser')
    floor_form_data = get_hidden_inputs(soup_floor)

    time.sleep(REQUEST_DELAY)
    res_room = session.post(LOGIN_URL, data={**floor_form_data, '__EVENTTARGET': 'drceng', 'drlouming': building_value, 'drceng': floor_value})
    res_room.raise_for_status()

    soup_room = BeautifulSoup(res_room.text, 'html.parser')
    room_form_data = get_hidden_inputs(soup_room)
    select = soup_room.find('select', {'id': 'drfangjian'})
    options = parse_options_for_api(select)
    return options, room_form_data

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/api/options/<string:type_>', methods=['GET'])
def api_options(type_):
    print(f"API Options called: type={type_}, args={request.args.to_dict()}")  # 添加日志：API调用
    session = requests.Session()
    session.headers.update(HEADERS)
    try:
        if type_ == 'buildings':
            options = get_buildings(session)
            print(f"Buildings options length: {len(options)}")  # 添加日志：options长度
        elif type_ == 'floors':
            parent = request.args.get('building')
            if not parent:
                print("Error: 缺少 parent for floors")  # 添加日志
                return jsonify({"error": "缺少 parent (楼栋 value)"}), 400
            options = get_floors(session, parent)
            print(f"Floors options length: {len(options)}")  # 添加日志
        elif type_ == 'rooms':
            parent = request.args.get('parent')  # floor_value
            building = request.args.get('building')  # building_value
            if not parent or not building:
                print("Error: 缺少 building 和 parent for rooms")  # 添加日志
                return jsonify({"error": "缺少 building 和 parent (楼层 value)"}), 400
            options, _ = get_rooms(session, building, parent)
            print(f"Rooms options length: {len(options)}")  # 添加日志
        else:
            print(f"Error: 无效的 type {type_}")  # 添加日志
            return jsonify({"error": "无效的 type"}), 400
        response_data = {"options": options}
        print(f"Returning options: {response_data}")  # 添加日志：返回数据
        return jsonify(response_data)
    except Exception as e:
        print(f"API Options error: {str(e)}")  # 添加日志：异常
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    finally:
        session.close()

@app.route('/api/query', methods=['POST'])
def api_query():
    print("API Query called with data:", request.json)  # 添加日志：打印请求数据
    try:
        data = request.json
        if not data:
            print("Error: 缺少 JSON body")  # 添加日志
            return jsonify({"error": "缺少 JSON body"}), 400

        building_text = data.get('building')
        floor_text = data.get('floor')
        room_text = data.get('room')
        start_date = data.get('start_date', (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d'))
        end_date = data.get('end_date', datetime.now().strftime('%Y-%m-%d'))

        print(f"Query params: building={building_text}, floor={floor_text}, room={room_text}, dates={start_date} to {end_date}")  # 添加日志：打印参数

        if not all([building_text, floor_text, room_text]):
            print("Error: 缺少 building、floor 或 room")  # 添加日志
            return jsonify({"error": "缺少 building、floor 或 room"}), 400

        # 检查缓存
        now = datetime.now()
        use_cache = False
        cached_data = None
        if os.path.exists(JSON_DATABASE_FILE):
            try:
                with open(JSON_DATABASE_FILE, 'r', encoding='utf-8') as f:
                    cached_data = json.load(f)
                print(f"Cache file exists, data keys: {list(cached_data.keys()) if cached_data else 'None'}")  # 日志：缓存存在
                cached_info = cached_data.get('info', {})
                print(f"Cached info: building={cached_info.get('building')}, floor={cached_info.get('floor')}, room={cached_info.get('room')}")  # 日志：缓存匹配
                if (cached_info.get('building') == building_text and
                    cached_info.get('floor') == floor_text and
                    cached_info.get('room') == room_text):
                    scrape_time_str = cached_info.get('scrape_time')
                    if scrape_time_str:
                        scrape_time = datetime.strptime(scrape_time_str, "%Y-%m-%d %H:%M:%S")
                        cache_age = now - scrape_time
                        print(f"Cache age: {cache_age}, threshold: 1 hour")  # 日志：缓存年龄
                        if cache_age < timedelta(hours=1):
                            use_cache = True
                            remaining_str = cached_info.get('remaining_electricity')
                            remaining = float(remaining_str) if remaining_str else 0.0
                            records = cached_data.get('records', [])
                            print(f"Using cache data, records length: {len(records)}")  # 添加日志：使用缓存
                            return jsonify({
                                "info": {
                                    "building": building_text,
                                    "floor": floor_text,
                                    "room": room_text,
                                    "scrape_time": scrape_time_str
                                },
                                "records": records,
                                "remaining_electricity": remaining
                            })
                        else:
                            print("Cache too old, scraping fresh data")  # 日志：缓存过期
                    else:
                        print("No scrape_time in cache, scraping fresh")  # 日志：无时间
                else:
                    print("Cache mismatch, scraping fresh")  # 日志：不匹配
            except (json.JSONDecodeError, ValueError, KeyError) as e:
                print(f"缓存解析错误: {e}")
        else:
            print("No cache file, scraping fresh")  # 日志：无缓存

        if use_cache:
            pass  # 已返回

        # 获取 value 并爬取
        session = requests.Session()
        session.headers.update(HEADERS)
        try:
            # 获取 buildings value
            buildings = get_buildings(session)
            print(f"Available buildings options: {len(buildings)}, sample: {buildings[:2] if buildings else 'empty'}")  # 日志：可用选项
            building_value = next((opt['value'] for opt in buildings if opt['text'] == building_text), None)
            print(f"Matching building_text '{building_text}' to value: {building_value}")  # 日志：匹配结果
            if not building_value:
                print(f"Failed to match building: searched texts: {[opt['text'] for opt in buildings]}")  # 日志：搜索文本
                return jsonify({"error": f"未找到楼栋 {building_text} 的 value"}), 400

            # 获取 floors value
            floors = get_floors(session, building_value)
            print(f"Available floors for building {building_value}: {len(floors)}, sample: {floors[:2] if floors else 'empty'}")
            floor_value = next((opt['value'] for opt in floors if opt['text'] == floor_text), None)
            print(f"Matching floor_text '{floor_text}' to value: {floor_value}")
            if not floor_value:
                print(f"Failed to match floor: searched texts: {[opt['text'] for opt in floors]}")
                return jsonify({"error": f"未找到楼层 {floor_text} 的 value"}), 400

            # 获取 rooms value 和 form_data
            rooms_opts, room_form_data = get_rooms(session, building_value, floor_value)
            print(f"Available rooms for floor {floor_value}: {len(rooms_opts)}, sample: {rooms_opts[:2] if rooms_opts else 'empty'}")
            room_value = next((opt['value'] for opt in rooms_opts if opt['text'] == room_text), None)
            print(f"Matching room_text '{room_text}' to value: {room_value}")
            if not room_value:
                print(f"Failed to match room: searched texts: {[opt['text'] for opt in rooms_opts]}")
                return jsonify({"error": f"未找到房间 {room_text} 的 value"}), 400

            # 爬取数据
            print("Starting scrape for room data...")  # 添加日志：开始爬取
            records, remaining_str = scrape_room_data(session, building_value, floor_value, room_value, room_form_data, start_date, end_date)
            if records is None:
                print("Scrape failed, returning error")  # 添加日志：爬取失败
                return jsonify({"error": "爬取失败"}), 500

            remaining = float(remaining_str) if remaining_str else 0.0
            print(f"Scrape success: {len(records)} records, remaining: {remaining_str}")  # 添加日志：爬取成功

            # 保存更新
            info = {
                "building": building_text,
                "floor": floor_text,
                "room": room_text,
                "building_value": building_value,
                "floor_value": floor_value,
                "room_value": room_value,
                "scrape_time": now.strftime("%Y-%m-%d %H:%M:%S")
            }
            if remaining_str:
                info["remaining_electricity"] = remaining_str

            data_to_save = {
                "info": info,
                "records": records
            }

            with open(JSON_DATABASE_FILE, 'w', encoding='utf-8') as f:
                json.dump(data_to_save, f, ensure_ascii=False, indent=4)

            # 返回
            print("Returning query response")  # 添加日志：返回响应
            return jsonify({
                "info": {
                    "building": building_text,
                    "floor": floor_text,
                    "room": room_text,
                    "scrape_time": info["scrape_time"]
                },
                "records": records,
                "remaining_electricity": remaining
            })
        finally:
            session.close()

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/refresh', methods=['GET'])
def api_refresh():
    building_text = request.args.get('building')
    floor_text = request.args.get('floor')
    room_text = request.args.get('room')

    if building_text and floor_text and room_text:
        print(f"刷新指定房间: {building_text} - {floor_text} - {room_text}")
        session = requests.Session()
        session.headers.update(HEADERS)
        try:
            # 获取 buildings value
            buildings = get_buildings(session)
            building_value = next((opt['value'] for opt in buildings if opt['text'] == building_text), None)
            if not building_value:
                return jsonify({"error": "无效房间参数"}), 400

            # 获取 floors value
            floors = get_floors(session, building_value)
            floor_value = next((opt['value'] for opt in floors if opt['text'] == floor_text), None)
            if not floor_value:
                return jsonify({"error": "无效房间参数"}), 400

            # 获取 rooms options 和 form_data
            rooms_opts, room_form_data = get_rooms(session, building_value, floor_value)
            room_value = next((opt['value'] for opt in rooms_opts if opt['text'] == room_text), None)
            if not room_value:
                return jsonify({"error": "无效房间参数"}), 400

            # 爬取数据 (默认90天)
            default_start = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
            default_end = datetime.now().strftime('%Y-%m-%d')
            records, remaining_str = scrape_room_data(session, building_value, floor_value, room_value, room_form_data, default_start, default_end)
            if records is None:
                return jsonify({"error": "刷新爬取失败"}), 500

            # 保存更新
            now = datetime.now()
            new_info = {
                "building": building_text,
                "floor": floor_text,
                "room": room_text,
                "building_value": building_value,
                "floor_value": floor_value,
                "room_value": room_value,
                "scrape_time": now.strftime("%Y-%m-%d %H:%M:%S")
            }
            if remaining_str:
                new_info["remaining_electricity"] = remaining_str

            new_data = {
                "info": new_info,
                "records": records
            }

            with open(JSON_DATABASE_FILE, 'w', encoding='utf-8') as f:
                json.dump(new_data, f, ensure_ascii=False, indent=4)

            return jsonify({'success': True, 'message': '数据已刷新'})

        except Exception as e:
            return jsonify({"error": str(e)}), 500
        finally:
            session.close()
    else:
        # 原逻辑 (基于缓存)
        if not os.path.exists(JSON_DATABASE_FILE):
            return jsonify({"error": "无缓存数据可刷新"}), 400

        try:
            with open(JSON_DATABASE_FILE, 'r', encoding='utf-8') as f:
                cached_data = json.load(f)
            info = cached_data.get('info', {})
            building_value = info.get('building_value')
            floor_value = info.get('floor_value')
            room_value = info.get('room_value')
            if not all([building_value, floor_value, room_value]):
                return jsonify({"error": "缓存数据缺少必要 value"}), 400

            session = requests.Session()
            session.headers.update(HEADERS)
            try:
                # 重建选择流程获取 room_form_data
                time.sleep(REQUEST_DELAY)
                resp = session.get(LOGIN_URL)
                resp.raise_for_status()
                soup_init = BeautifulSoup(resp.text, 'html.parser')
                initial_form = get_hidden_inputs(soup_init)

                time.sleep(REQUEST_DELAY)
                res_floor_sel = session.post(LOGIN_URL, data={**initial_form, '__EVENTTARGET': 'drlouming', 'drlouming': building_value})
                res_floor_sel.raise_for_status()
                soup_floor = BeautifulSoup(res_floor_sel.text, 'html.parser')
                floor_form = get_hidden_inputs(soup_floor)

                time.sleep(REQUEST_DELAY)
                res_room_sel = session.post(LOGIN_URL, data={**floor_form, '__EVENTTARGET': 'drceng', 'drlouming': building_value, 'drceng': floor_value})
                res_room_sel.raise_for_status()
                soup_room = BeautifulSoup(res_room_sel.text, 'html.parser')
                room_form_data = get_hidden_inputs(soup_room)

                # 爬取 (默认90天)
                default_start = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
                default_end = datetime.now().strftime('%Y-%m-%d')
                records, remaining_str = scrape_room_data(session, building_value, floor_value, room_value, room_form_data, default_start, default_end)
                if records is None:
                    return jsonify({"error": "刷新爬取失败"}), 500

                now = datetime.now()
                new_info = {
                    "building": info["building"],
                    "floor": info["floor"],
                    "room": info["room"],
                    "building_value": building_value,
                    "floor_value": floor_value,
                    "room_value": room_value,
                    "scrape_time": now.strftime("%Y-%m-%d %H:%M:%S")
                }
                if remaining_str:
                    new_info["remaining_electricity"] = remaining_str

                new_data = {
                    "info": new_info,
                    "records": records
                }

                with open(JSON_DATABASE_FILE, 'w', encoding='utf-8') as f:
                    json.dump(new_data, f, ensure_ascii=False, indent=4)

                return jsonify({"success": True, "message": "缓存已刷新"})
            finally:
                session.close()

        except Exception as e:
            return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)