$(document).ready(function() {
    // 默认日期：最近90天
    const today = new Date().toISOString().split('T')[0];
    const ninetyDaysAgo = new Date(Date.now() - 90 * 24 * 60 * 60 * 1000).toISOString().split('T')[0];
    $('#start_date').val(ninetyDaysAgo);
    $('#end_date').val(today);

    // 加载楼栋选项
    $.get('/api/options/buildings')
    .done(function(data) {
        console.log('Buildings response received:', data);  // 添加日志：收到响应
        if (data && data.options && data.options.length > 0) {
            $('#building').empty().append('<option value="">请选择楼栋</option>');
            data.options.forEach(function(option) {
                $('#building').append(`<option value="${option.value}">${option.text}</option>`);
            });
            console.log('Building options appended:', data.options.length);  // 添加日志：append成功
        } else {
            console.log('No options in response:', data);  // 添加日志：无options
            alert('加载楼栋失败: ' + (data ? data.error || '无可用楼栋' : '响应为空') );
        }
    })
    .fail(function(xhr, status, error) {
        console.log('Buildings load error:', {status: xhr.status, textStatus: status, error: error, responseText: xhr.responseText});  // 添加详细错误日志
        alert('网络错误，加载楼栋失败: ' + error);
    });

    // 楼栋变化：加载楼层
    $('#building').change(function() {
        const buildingValue = $(this).val();
        const buildingText = $(this).find('option:selected').text();
        if (buildingValue) {
            $('#floor').prop('disabled', false).empty().append('<option value="">请选择楼层</option>');
            $('#room').prop('disabled', true).empty().append('<option value="">请先选择楼层</option>');

            $.get(`/api/options/floors?building=${buildingValue}`, function(data) {
                if (data.options) {
                    data.options.forEach(function(option) {
                        $('#floor').append(`<option value="${option.value}">${option.text}</option>`);
                    });
                } else {
                    alert('加载楼层失败: ' + (data.error || '未知错误'));
                    $('#floor').prop('disabled', true);
                }
            }).fail(function() {
                alert('网络错误，加载楼层失败');
                $('#floor').prop('disabled', true);
            });
        } else {
            $('#floor').prop('disabled', true);
            $('#room').prop('disabled', true);
        }
    });

    // 楼层变化：加载房间
    $('#floor').change(function() {
        const floorValue = $(this).val();
        const buildingValue = $('#building').val();
        if (floorValue && buildingValue) {
            $('#room').prop('disabled', false).empty().append('<option value="">请选择房间</option>');

            $.get(`/api/options/rooms?building=${buildingValue}&parent=${floorValue}`, function(data) {
                if (data.options) {
                    data.options.forEach(function(option) {
                        $('#room').append(`<option value="${option.value}">${option.text}</option>`);
                    });
                } else {
                    alert('加载房间失败: ' + (data.error || '未知错误'));
                    $('#room').prop('disabled', true);
                }
            }).fail(function() {
                alert('网络错误，加载房间失败');
                $('#room').prop('disabled', true);
            });
        } else {
            $('#room').prop('disabled', true);
        }
    });

    // 表单提交：AJAX查询
    $('#queryForm').submit(function(e) {
        e.preventDefault();
        const buildingText = $('#building option:selected').text();
        const floorText = $('#floor option:selected').text();
        const roomText = $('#room option:selected').text();
        const startDate = $('#start_date').val();
        const endDate = $('#end_date').val();

        console.log('Query submit:', {building: buildingText, floor: floorText, room: roomText, start: startDate, end: endDate});  // 添加日志：查询参数

        if (!buildingText || !floorText || !roomText) {
            alert('请先选择完整的楼栋、楼层和房间');
            return;
        }

        if (!startDate || !endDate) {
            alert('请选择日期范围');
            return;
        }

        $('#loading').show();
        $('#results').hide();

        $.ajax({
            url: '/api/query',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({
                building: buildingText,
                floor: floorText,
                room: roomText,
                start_date: startDate,
                end_date: endDate
            }),
            success: function(data) {
                console.log('Query success:', data);  // 添加日志：成功响应
                $('#loading').hide();
                if (data.remaining_electricity !== undefined) {
                    $('#remaining').text(`剩余电量: ${data.remaining_electricity} 度`);
                } else {
                    $('#remaining').text('剩余电量: -- 度');
                }

                // 清空表格并添加记录
                $('#recordsTable tbody').empty();
                if (data.records && data.records.length > 0) {
                    data.records.forEach(function(record) {
                        $('#recordsTable tbody').append(
                            `<tr>
                                <td>${record.date}</td>
                                <td>${record.meter_name}</td>
                                <td>${record.usage}</td>
                                <td>${record.price}</td>
                            </tr>`
                        );
                    });
                } else {
                    $('#recordsTable tbody').append('<tr><td colspan="4" style="text-align: center;">无记录</td></tr>');
                }

                $('#results').show();
            },
            error: function(xhr) {
                console.log('Query error:', xhr.status, xhr.responseText);  // 添加日志：错误响应
                $('#loading').hide();
                let errorMsg = '查询失败';
                if (xhr.responseJSON && xhr.responseJSON.error) {
                    errorMsg += ': ' + xhr.responseJSON.error;
                }
                alert(errorMsg);
            }
        });
    });

    // 刷新按钮：刷新缓存数据并重新查询
    $('#refreshBtn').click(function() {
        $.get('/api/refresh', function(data) {
            if (data.success) {
                alert('数据已刷新成功');
                // 重新提交当前表单查询
                $('#queryForm').trigger('submit');
            } else {
                alert('刷新失败: ' + (data.error || '未知错误'));
            }
        }).fail(function() {
            alert('网络错误，刷新失败');
        });
    });
});