$(document).ready(function() {
    // DOM 元素引用
    const settingsButton = document.getElementById('settingsButton');
    const settingsModal = document.getElementById('settingsModal');
    const closeSettings = document.getElementById('closeSettings');
    const saveSettings = document.getElementById('saveSettings');
    const tabs = document.querySelectorAll('.tab');
    const tabContents = document.querySelectorAll('.tab-content');
    const buildingSelect = $('#building');
    const floorSelect = $('#floor');
    const roomSelect = $('#room');

    // 初始化
    setupEventListeners();
    loadOptions();  // 初始加载楼栋选项到模态

    function setupEventListeners() {
        // 设置模态框
        settingsButton.addEventListener('click', () => {
            settingsModal.style.display = 'flex';
        });

        closeSettings.addEventListener('click', () => {
            settingsModal.style.display = 'none';
        });

        // 点击模态外关闭
        window.addEventListener('click', (event) => {
            if (event.target === settingsModal) {
                settingsModal.style.display = 'none';
            }
        });

        // 保存设置
        saveSettings.addEventListener('click', () => {
            const buildingText = buildingSelect.find('option:selected').text();
            const floorText = floorSelect.find('option:selected').text();
            const roomText = roomSelect.find('option:selected').text();
            const frequency = $('#updateFrequency').val();
        
            if (!buildingText || !floorText || !roomText) {
                alert('请完整选择楼栋、楼层和房间');
                return;
            }
        
            console.log('保存设置前，选中的选项:', {buildingText, floorText, roomText, frequency});
            // 保存到 localStorage (JSON 对象)
            const settings = { building: buildingText, floor: floorText, room: roomText, frequency: frequency };
            localStorage.setItem('roomSettings', JSON.stringify(settings));
            console.log('保存 settings 到 localStorage:', settings);
        
            // 添加 loadingText 如果不存在
            if (!$('#loadingText').length) {
                $('.settings-content').append('<p id="loadingText" style="text-align: center; color: blue;">正在获取数据，请等待😘...</p>');
            }
            $('#loadingText').show();
            console.log('加载中...');
        
            // 调用 /api/refresh 触发爬取
            $.get('/api/refresh?building=' + buildingText + '&floor=' + floorText + '&room=' + roomText)
                .done(function(data) {
                    if (!data.success) {
                        $('#loadingText').hide();
                        alert('刷新失败: ' + (data.error || '未知错误'));
                        return;
                    }
                    console.log('刷新完成');
                    console.log('loadData.done called');
                    $('#loadingText').hide();
                    $('#loading').show();  // 显示 spinner for loadData
                    loadData().done(function(result) {
                        $('#loading').hide();
                        if (result.data && result.data.records && result.data.records.length > 0) {
                            updateDashboard(result.data);
                            updateCharts(result.weekly, result.monthly, result.distribution, result.distributions);
                            console.log('面板数据已自动刷新');
                        } else {
                            console.log('无新数据');
                            // 设置空值
                            document.getElementById('remainingElectricity').textContent = '--';
                            document.getElementById('remainingCost').textContent = '--';
                            document.getElementById('todayUsage').textContent = '--';
                            document.getElementById('todayCost').textContent = '--';
                            document.getElementById('yesterdayUsage').textContent = '--';
                            document.getElementById('yesterdayCost').textContent = '--';
                            document.getElementById('monthUsage').textContent = '--';
                            document.getElementById('monthCost').textContent = '--';
                            document.getElementById('lastUpdateTime').textContent = '--';
                        }
                        settingsModal.style.display = 'none';
                    }).fail(function(err) {
                        $('#loading').hide();
                        alert('数据加载失败: ' + err.message);
                        console.log('saveSettings loadData 失败');
                    });
                })
                .fail(function() {
                    alert('爬取失败，请重试');
                    $('#loading').hide();
                    $('#loadingText').hide();
                });
        });

        // 标签页切换
        tabs.forEach(tab => {
            tab.addEventListener('click', () => {
                const tabId = tab.getAttribute('data-tab');
                
                // 移除所有 active 类
                tabs.forEach(t => t.classList.remove('active'));
                tabContents.forEach(tc => tc.classList.remove('active'));
                
                // 添加 active 类到当前
                tab.classList.add('active');
                document.getElementById(`${tabId}Tab`).classList.add('active');
            });
        });

        // 刷新按钮
        $('#refreshBtn').click(function() {
            $('#loading').show();
            $.get('/api/refresh')
                .done(function(data) {
                    if (data.success) {
                        console.log('刷新完成');
                        loadData().done(function(result) {
                            $('#loading').hide();
                            if (result.data && result.data.records && result.data.records.length > 0) {
                                updateDashboard(result.data);
                                updateCharts(result.weekly, result.monthly, result.distribution, result.distributions);
                                console.log('刷新数据加载完成');
                            } else {
                                alert('刷新后无新数据');
                                // 设置空值
                                document.getElementById('remainingElectricity').textContent = '--';
                                document.getElementById('remainingCost').textContent = '--';
                                document.getElementById('todayUsage').textContent = '--';
                                document.getElementById('todayCost').textContent = '--';
                                document.getElementById('yesterdayUsage').textContent = '--';
                                document.getElementById('yesterdayCost').textContent = '--';
                                document.getElementById('monthUsage').textContent = '--';
                                document.getElementById('monthCost').textContent = '--';
                                document.getElementById('lastUpdateTime').textContent = '--';
                            }
                        }).fail(function(err) {
                            $('#loading').hide();
                            alert('数据加载失败: ' + err.message);
                            console.log('刷新加载失败');
                            // 设置空值
                            document.getElementById('remainingElectricity').textContent = '--';
                            document.getElementById('remainingCost').textContent = '--';
                            document.getElementById('todayUsage').textContent = '--';
                            document.getElementById('todayCost').textContent = '--';
                            document.getElementById('yesterdayUsage').textContent = '--';
                            document.getElementById('yesterdayCost').textContent = '--';
                            document.getElementById('monthUsage').textContent = '--';
                            document.getElementById('monthCost').textContent = '--';
                            document.getElementById('lastUpdateTime').textContent = '--';
                        });
                    } else {
                        $('#loading').hide();
                        alert('刷新失败: ' + (data.error || '未知错误'));
                    }
                })
                .fail(function() {
                    $('#loading').hide();
                    alert('网络错误，刷新失败');
                });
        });

        // 楼栋变化：加载楼层
        buildingSelect.change(function() {
            const buildingValue = $(this).val();
            const buildingText = $(this).find('option:selected').text();
            if (buildingValue) {
                floorSelect.prop('disabled', false).empty().append('<option value="">请选择楼层</option>');
                roomSelect.prop('disabled', true).empty().append('<option value="">请先选择楼层</option>');

                $.get(`/api/options/floors?building=${buildingValue}`, function(data) {
                    if (data && data.options) {
                        data.options.forEach(function(option) {
                            floorSelect.append(`<option value="${option.value}">${option.text}</option>`);
                        });
                    } else {
                        alert('加载楼层失败: ' + (data ? data.error || '未知错误' : '响应为空'));
                        floorSelect.prop('disabled', true);
                    }
                }).fail(function() {
                    alert('网络错误，加载楼层失败');
                    floorSelect.prop('disabled', true);
                });
            } else {
                floorSelect.prop('disabled', true);
                roomSelect.prop('disabled', true);
            }
        });

        // 楼层变化：加载房间
        floorSelect.change(function() {
            const floorValue = $(this).val();
            const buildingValue = buildingSelect.val();
            if (floorValue && buildingValue) {
                roomSelect.prop('disabled', false).empty().append('<option value="">请选择房间</option>');

                $.get(`/api/options/rooms?building=${buildingValue}&parent=${floorValue}`, function(data) {
                    if (data && data.options) {
                        data.options.forEach(function(option) {
                            roomSelect.append(`<option value="${option.value}">${option.text}</option>`);
                        });
                    } else {
                        alert('加载房间失败: ' + (data ? data.error || '未知错误' : '响应为空'));
                        roomSelect.prop('disabled', true);
                    }
                }).fail(function() {
                    alert('网络错误，加载房间失败');
                    roomSelect.prop('disabled', true);
                });
            } else {
                roomSelect.prop('disabled', true);
            }
        });
    }

    // 加载楼栋选项
    function loadOptions() {
        $.get('/api/options/buildings')
        .done(function(data) {
            if (data && data.options && data.options.length > 0) {
                buildingSelect.empty().append('<option value="">请选择楼栋</option>');
                data.options.forEach(function(option) {
                    buildingSelect.append(`<option value="${option.value}">${option.text}</option>`);
                });
            } else {
                alert('加载楼栋失败: ' + (data ? data.error || '无可用楼栋' : '响应为空'));
            }
        })
        .fail(function(xhr, status, error) {
            alert('网络错误，加载楼栋失败: ' + error);
        });
    }

    // (旧占位 loadData 已移除，统一使用下方完整实现)

    // 初始检查保存的设置
    const savedSettings = localStorage.getItem('roomSettings');
    console.log('页面加载时检查 localStorage roomSettings:', savedSettings);
    if (savedSettings) {
        const settings = JSON.parse(savedSettings);
        console.log('解析设置:', settings);
        if (settings.building && settings.floor && settings.room) {
            console.log('检测到保存的房间，调用 loadData()');
            loadData().done(function(result) {
                if (result.data && result.data.records && result.data.records.length > 0) {
                    updateDashboard(result.data);
                    updateCharts(result.weekly, result.monthly, result.distribution, result.distributions);
                    console.log('初始数据加载完成');
                } else {
                    console.log('初始加载无数据');
                    // 设置空值
                    document.getElementById('remainingElectricity').textContent = '--';
                    document.getElementById('remainingCost').textContent = '--';
                    document.getElementById('todayUsage').textContent = '--';
                    document.getElementById('todayCost').textContent = '--';
                    document.getElementById('yesterdayUsage').textContent = '--';
                    document.getElementById('yesterdayCost').textContent = '--';
                    document.getElementById('monthUsage').textContent = '--';
                    document.getElementById('monthCost').textContent = '--';
                    document.getElementById('lastUpdateTime').textContent = '--';
                }
            }).fail(function(err) {
                alert('数据加载失败: ' + err.message);
                console.log('初始加载失败');
                // 设置空值
                document.getElementById('remainingElectricity').textContent = '--';
                document.getElementById('remainingCost').textContent = '--';
                document.getElementById('todayUsage').textContent = '--';
                document.getElementById('todayCost').textContent = '--';
                document.getElementById('yesterdayUsage').textContent = '--';
                document.getElementById('yesterdayCost').textContent = '--';
                document.getElementById('monthUsage').textContent = '--';
                document.getElementById('monthCost').textContent = '--';
                document.getElementById('lastUpdateTime').textContent = '--';
            });
        } else {
            console.log('保存设置不完整，不加载数据');
        }
    } else {
        console.log('无保存房间，不加载数据');
    }
});
    // 电费率 (从模拟数据硬编码，可调整)
const charts = {
    weeklyChart: null,
    monthlyChart: null,
    pieChart: null,
    pieYesterday: null,
    pieThreeDays: null,
    pieWeekly: null,
    pieMonthly: null
};
    const ELECTRICITY_RATE = 0.55;

    // 计算指定日期用量 (sum usage)
    function getUsageByDate(records, targetDate) {
        return records
            .filter(record => record.date === targetDate)
            .reduce((sum, record) => sum + parseFloat(record.usage || 0), 0);
    }

    // 计算趋势数据 (group by date, sum total and by meter)
    function getTrendData(records, dates) {
        const meterNames = [...new Set(records.map(r => r.meter_name))];  // 动态获取 meter types
        const uniqueMeters = meterNames.length > 0 ? meterNames : ['空调', '照明'];  // fallback

        const totalData = dates.map(date => getUsageByDate(records, date));
        
        const meterData = uniqueMeters.map(meter => 
            dates.map(date => records
                .filter(record => record.date === date && record.meter_name.includes(meter))
                .reduce((sum, record) => sum + parseFloat(record.usage || 0), 0)
            )
        );

        return {
            dates,
            meters: uniqueMeters,
            total: totalData,
            byMeter: meterData
        };
    }

    // 获取周趋势 (最近 7 天)
    function getWeeklyData(records) {
        const today = new Date();
        const dates = [];
        for (let i = 6; i >= 0; i--) {
            const date = new Date(today);
            date.setDate(today.getDate() - i);
            dates.push(date.toISOString().split('T')[0]);
        }
        return getTrendData(records, dates);
    }

    // 获取月趋势 (最近 4 周，每周 sum)
    function getMonthlyData(records) {
        const today = new Date();
        const weeks = ['第一周', '第二周', '第三周', '第四周'];
        const weekData = weeks.map((_, index) => {
            const startDate = new Date(today);
            startDate.setDate(today.getDate() - (index * 7 + 6));
            const endDate = new Date(startDate);
            endDate.setDate(startDate.getDate() + 6);
            const weekRecords = records.filter(record => {
                const recordDate = new Date(record.date);
                return recordDate >= startDate && recordDate <= endDate;
            });
            return weekRecords.reduce((sum, record) => sum + parseFloat(record.usage || 0), 0);
        });
        // For bars: airConditioner, lighting, total (similar grouping)
        const meterNames = [...new Set(records.map(r => r.meter_name))];
        const uniqueMeters = meterNames.length > 0 ? meterNames : ['空调', '照明'];
        const meterWeekData = uniqueMeters.map(meter => 
            weeks.map((_, index) => {
                // Similar filtering for week
                const startDate = new Date(today);
                startDate.setDate(today.getDate() - (index * 7 + 6));
                const endDate = new Date(startDate);
                endDate.setDate(startDate.getDate() + 6);
                return records
                    .filter(record => {
                        const recordDate = new Date(record.date);
                        return recordDate >= startDate && recordDate <= endDate && record.meter_name.includes(meter);
                    })
                    .reduce((sum, record) => sum + parseFloat(record.usage || 0), 0);
            })
        );

        return {
            weeks,
            total: weekData,
            byMeter: meterWeekData,
            meters: uniqueMeters
        };
    }

    // 获取月构成 (group by meter sum)
    function getUsageDistribution(records) {
        const acSum = records.filter(record => record.meter_name.includes('空调')).reduce((sum, record) => sum + parseFloat(record.usage || 0), 0);
        const otherSum = records.filter(record => !record.meter_name.includes('空调')).reduce((sum, record) => sum + parseFloat(record.usage || 0), 0);
        const totalMonth = acSum + otherSum;
        return {
            meters: ['空调', '照明'],
            values: [acSum, otherSum],
            total: totalMonth
        };
    }

    // 获取指定时间范围的用电分布
    function getTimeRangeDistribution(records, days, title) {
        let filtered;
        const today = new Date();
        if (days === 1) {
            const yesterday = new Date(today.getTime() - 86400000);
            const yesterdayStr = yesterday.toISOString().split('T')[0];
            filtered = records.filter(record => record.date === yesterdayStr);
        } else {
            const cutoff = new Date(today.getTime() - days * 86400000);
            const cutoffStr = cutoff.toISOString().split('T')[0];
            filtered = records.filter(record => {
                const recordDate = new Date(record.date);
                return recordDate >= cutoff;
            });
        }
        const dist = getUsageDistribution(filtered);
        return {
            title: title,
            ...dist
        };
    }

    // 更新概览卡片 DOM
    function updateDashboard(data) {
        console.log('updateDashboard 开始, data:', data);
        const rates = ELECTRICITY_RATE;
        const today = new Date().toISOString().split('T')[0];
        const yesterday = new Date(Date.now() - 86400000).toISOString().split('T')[0];
        const monthStart = new Date();
        monthStart.setDate(1);
        const monthRecords = data.records.filter(record => new Date(record.date) >= monthStart);
        const monthUsage = monthRecords.reduce((sum, record) => sum + parseFloat(record.usage || 0), 0);
        console.log('计算结果:', {todayUsage: getUsageByDate(data.records, today), yesterdayUsage: getUsageByDate(data.records, yesterday), monthUsage});

        // 剩余
        document.getElementById('remainingElectricity').textContent = `${data.remaining_electricity || '--'} 度`;
        document.getElementById('remainingCost').textContent = `约 ${((data.remaining_electricity || 0) * rates).toFixed(2)} 元`;

        // 今日
        const todayUsage = getUsageByDate(data.records, today);
        document.getElementById('todayUsage').textContent = `${todayUsage.toFixed(1)} 度`;
        document.getElementById('todayCost').textContent = `${(todayUsage * rates).toFixed(2)} 元`;

        // 昨日
        const yesterdayUsage = getUsageByDate(data.records, yesterday);
        document.getElementById('yesterdayUsage').textContent = `${yesterdayUsage.toFixed(1)} 度`;
        document.getElementById('yesterdayCost').textContent = `${(yesterdayUsage * rates).toFixed(2)} 元`;

        // 月
        document.getElementById('monthUsage').textContent = `${monthUsage.toFixed(1)} 度`;
        document.getElementById('monthCost').textContent = `${(monthUsage * rates).toFixed(2)} 元`;

        // 更新时间
        document.getElementById('lastUpdateTime').textContent = data.info ? data.info.scrape_time : '--';
        console.log('DOM 更新完成');
    }

    // 更新图表函数
    function updateCharts(weeklyData, monthlyData, distribution, distributions) {
        const ctxWeekly = document.getElementById('weeklyChart').getContext('2d');
        const ctxMonthly = document.getElementById('monthlyChart').getContext('2d');
        const ctxPieMonthly = document.getElementById('pieMonthly').getContext('2d');  // 使用 pieMonthly for original pieChart
        // 为4个新饼图准备
        const pieCtxs = {
            yesterday: document.getElementById('pieYesterday')?.getContext('2d'),
            threeDays: document.getElementById('pieThreeDays')?.getContext('2d'),
            weekly: document.getElementById('pieWeekly')?.getContext('2d'),
            monthly: ctxPieMonthly
        };

        // 周度折线图
        console.log('Creating new weeklyChart with labels:', weeklyData.dates);
        if (charts.weeklyChart) {
            charts.weeklyChart.destroy();
        }
        charts.weeklyChart = new Chart(ctxWeekly, {
            type: 'line',
            data: {
                labels: weeklyData.dates.map(d => d.split('-').slice(1).reverse().join('-')),
                datasets: [{
                    label: '总用电 (度)',
                    data: weeklyData.total,
                    borderColor: '#f72585',
                    backgroundColor: 'rgba(247, 37, 133, 0.1)',
                    tension: 0.3,
                    fill: true
                },
                ...(weeklyData.meters.length > 0 ? weeklyData.meters.slice(0, 2).map((meter, idx) => ({
                    label: meter,
                    data: weeklyData.byMeter[idx] || Array(weeklyData.dates.length).fill(0),
                    borderColor: ['#4361ee', '#4cc9f0'][idx] || '#4895ef',
                    backgroundColor: ['rgba(67, 97, 238, 0.1)', 'rgba(76, 201, 240, 0.1)'][idx] || 'rgba(72, 149, 239, 0.1)',
                    tension: 0.3,
                    fill: false
                })) : [])
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                layout: {
                    padding: 10
                },
                plugins: {
                    title: { display: true, text: '近一周用电趋势' },
                    tooltip: {
                        mode: 'index',
                        intersect: false,
                        callbacks: {
                            label: function(context) {
                                const value = context.raw || 0;
                                return `${context.dataset.label}: ${value.toFixed(1)} 度 / ${(value * ELECTRICITY_RATE).toFixed(2)}元`;
                            }
                        }
                    }
                },
                scales: {
                    y: { beginAtZero: true, title: { display: true, text: '用电量 (度)' } }
                }
            }
        });

        // 月度柱状图
        console.log('Creating new monthlyChart with labels:', monthlyData.weeks);
        if (charts.monthlyChart) {
            charts.monthlyChart.destroy();
        }
        charts.monthlyChart = new Chart(ctxMonthly, {
            type: 'bar',
            data: {
                labels: monthlyData.weeks,
                datasets: [{
                    label: '总用电 (度)',
                    data: monthlyData.total,
                    backgroundColor: 'rgba(247, 37, 133, 0.7)',
                },
                ...(monthlyData.meters.length > 0 ? monthlyData.meters.slice(0, 2).map((meter, idx) => ({
                    label: meter,
                    data: monthlyData.byMeter[idx] || Array(monthlyData.weeks.length).fill(0),
                    backgroundColor: ['rgba(67, 97, 238, 0.7)', 'rgba(76, 201, 240, 0.7)'][idx] || 'rgba(72, 149, 239, 0.7)',
                })) : [])
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                layout: {
                    padding: 10
                },
                plugins: {
                    title: { display: true, text: '近一月用电趋势' },
                    tooltip: {
                        mode: 'index',
                        callbacks: {
                            label: function(context) {
                                const value = context.raw || 0;
                                return `${context.dataset.label}: ${value.toFixed(1)} 度 / ${(value * ELECTRICITY_RATE).toFixed(2)}元`;
                            }
                        }
                    }
                },
                scales: {
                    y: { beginAtZero: true, title: { display: true, text: '用电量 (度)' } }
                }
            }
        });

        // 饼图 - 更新原有pieChart使用monthly distribution
        console.log('Creating monthly pieChart with:', distributions.monthly);
        if (charts.pieMonthly) {
            charts.pieMonthly.destroy();
        }
        if (ctxPieMonthly) {
            charts.pieMonthly = new Chart(ctxPieMonthly, {
                type: 'pie',
                data: {
                    labels: distributions.monthly.meters,
                    datasets: [{
                        data: distributions.monthly.values,
                        backgroundColor: ['#4361ee', '#4cc9f0'],
                        hoverOffset: 4
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: true,
                    plugins: {
                        title: { display: true, text: distributions.monthly.title },
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    const value = context.raw || 0;
                                    const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                    const percentage = total > 0 ? ((value / total) * 100).toFixed(1) : 0;
                                    return `${context.label}: ${value.toFixed(1)} 度 (${percentage}%) / ${(value * ELECTRICITY_RATE).toFixed(2)}元`;
                                }
                            }
                        }
                    }
                }
            });
        }

        // 创建4个时间范围饼图
        Object.keys(distributions).forEach(key => {
            const dist = distributions[key];
            const ctx = pieCtxs[key];
            if (!ctx || !dist || dist.values.length === 0) return;

            const chartKey = `pie${key.charAt(0).toUpperCase() + key.slice(1)}`;
            console.log(`Creating ${chartKey} with:`, dist);
            if (charts[chartKey]) {
                charts[chartKey].destroy();
            }
            charts[chartKey] = new Chart(ctx, {
                type: 'pie',
                data: {
                    labels: dist.meters,
                    datasets: [{
                        data: dist.values,
                        backgroundColor: ['#4361ee', '#4cc9f0'],  // 空调蓝, 照明青
                        hoverOffset: 4
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: true,
                    plugins: {
                        title: {
                            display: false
                        },
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    const value = context.raw || 0;
                                    const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                    const percentage = total > 0 ? ((value / total) * 100).toFixed(1) : 0;
                                    return `${context.label}: ${value.toFixed(1)} 度 (${percentage}%) / ${(value * ELECTRICITY_RATE).toFixed(2)}元`;
                                }
                            }
                        }
                    }
                }
            });
        });
    }

    // 加载数据实现
    function loadData() {
        console.log('loadData() 开始执行');
        const savedSettings = localStorage.getItem('roomSettings');
        console.log('从 localStorage 读取 roomSettings:', savedSettings);
        if (!savedSettings) {
            console.log('无保存设置，跳过数据加载');
            return $.Deferred().resolve({data: null, weekly: null, monthly: null, distribution: null});
        }
        const settings = JSON.parse(savedSettings);
        const { building: buildingText, floor: floorText, room: roomText } = settings;
        console.log('解析设置:', {buildingText, floorText, roomText});
        if (!buildingText || !floorText || !roomText) {
            console.log('设置不完整，跳过数据加载');
            return $.Deferred().resolve({data: null, weekly: null, monthly: null, distribution: null});
        }

        // 日期范围：最近 90 天
        const today = new Date().toISOString().split('T')[0];
        const ninetyDaysAgo = new Date(Date.now() - 90 * 24 * 60 * 60 * 1000).toISOString().split('T')[0];
        console.log('查询日期范围:', {start: ninetyDaysAgo, end: today});

        return $.ajax({
            url: '/api/query',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({
                building: buildingText,
                floor: floorText,
                room: roomText,
                start_date: ninetyDaysAgo,
                end_date: today
            })
        }).then(function(data) {
            console.log('AJAX success, 数据响应:', data);
            console.log('loadData received records:', data.records ? data.records.length : 0, 'computed weekly:', getWeeklyData(data.records));
            if (data.error || !data.records || data.records.length === 0) {
                throw new Error('数据加载失败: ' + (data.error || '无记录'));
            }
            console.log('数据加载完成');

            // 计算趋势和构成
            const weekly = getWeeklyData(data.records);
            const monthly = getMonthlyData(data.records);
            const distribution = getUsageDistribution(data.records);
            const distributions = {
                yesterday: getTimeRangeDistribution(data.records, 1, '昨日'),
                threeDays: getTimeRangeDistribution(data.records, 3, '近三日'),
                weekly: getTimeRangeDistribution(data.records, 7, '近一周'),
                monthly: getTimeRangeDistribution(data.records, 30, '近一个月')
            };
            console.log('计算数据:', {weeklyTotal: weekly.total, monthlyTotal: monthly.total, distributionTotal: distribution.total, distributions});

            return {
                data: data,
                weekly: weekly,
                monthly: monthly,
                distribution: distribution,
                distributions: distributions
            };
        }).fail(function(xhr, status, error) {
            console.error('AJAX error:', xhr);
            console.log('数据加载失败');
            let errorMsg = '数据加载失败';
            if (xhr.responseJSON && xhr.responseJSON.error) {
                errorMsg += ': ' + xhr.responseJSON.error;
            }
            throw new Error(errorMsg);
        });
    }