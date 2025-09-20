# 电费查询网站

## 项目结构
- `app.py`: Flask 后端应用，实现 API 端点。
- `electric_fee_scraper.py`: 电费数据爬取模块，使用 BeautifulSoup 解析网站数据。
- `templates/index.html`: 前端 HTML 模板。
- `static/js/script.js`: 前端 JavaScript，实现 AJAX 与后端交互。
- `run.py`: 应用启动脚本，支持本地开发运行。
- `requirements.txt`: 项目依赖列表。

## 安装步骤
1. 克隆或下载项目到本地目录。
2. 打开终端，进入项目目录。
3. 安装依赖：
   ```
   pip install -r requirements.txt
   ```

## 运行
1. 启动应用：
   ```
   python run.py
   ```
   这将以调试模式在 `http://localhost:5000` 启动服务器（支持从任意 IP 访问）。
2. 在浏览器打开 `http://localhost:5000`。
3. 为生产环境，可修改 `run.py` 中的 `debug=False`。

## 功能描述
- **电费查询**：通过下拉菜单选择楼栋、楼层、房间和日期，点击查询按钮显示剩余电费和历史记录。
- **刷新缓存**：点击刷新按钮更新数据缓存（JSON 文件），确保数据最新。
- 前端使用 AJAX 异步加载，避免页面刷新；后端处理爬取和缓存逻辑。

## 注意事项
- **依赖网站稳定**：应用爬取特定电费网站，若网站变更或不可用，可能需更新 `electric_fee_scraper.py` 中的 HEADERS 或解析逻辑。
- **数据缓存**：查询结果缓存在 `electricity_data_single_room.json`，刷新时会重新爬取。
- **错误处理**：API 返回 JSON 格式错误信息，如网络失败或无效输入。
- 已集成重试机制和 Cookies 处理，确保爬取成功。

## 部署建议
- **本地运行**：直接使用 `python run.py`，适合开发和测试。
- **Heroku 部署**：
  1. 创建 `Procfile` 文件（无扩展名），内容：`web: python run.py`
  2. 使用 Git 推送至 Heroku：`git init`, `git add .`, `git commit -m "init"`, `heroku create`, `git push heroku main`。
  3. 访问 Heroku 提供的 URL，端口自动分配为 5000。
- **其他平台**：如 Vercel 或 Railway，支持 Flask 应用；确保环境变量或 Procfile 配置正确。
- 生产环境建议：使用 Gunicorn 替换内置服务器，添加 `gunicorn app:app` 到 Procfile。

项目基于 Flask 开发，支持跨域请求。所有核心功能已测试验证：应用启动正常，数据加载和查询工作。