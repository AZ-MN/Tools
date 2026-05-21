# 一键生成3000条门店测试数据INSERT语句
import random

# 输出文件路径
output_file = "insert_store_3000.sql"

# INSERT表头（和你的字段完全对应）
sql_header = """INSERT INTO `zt-store`.`store` (
    `id`, `weaver_store_id`, `brand_id`, `brand_name`, `brand_sort`, `brand_type`, `title`, `codeno`, `store_level`, 
    `city_area_id`, `city_area_name`, `zone_area_id`, `group_area_id`, `group_area_name`, `zone_area_name`, `store_area_id`, 
    `manage_area`, `manage_zone`, `manage_zone_id`, `city_code`, `phone`, `email`, `weaver_dept_manage_user_id`, 
    `dept_manage_user_id`, `dept_manage_user_name`, `manage_area_id`, `country_id`, `country_sort`, `country_name`, 
    `province_id`, `province_name`, `city_id`, `city_name`, `county_id`, `county_name`, `address`, `lng`, `lat`, 
    `photos`, `open_day`, `manager_user_id`, `manager_name`, `manager_mobile`, `partners`, `managers`, `financail_name`, 
    `company_name`, `tax_code`, `open_status`, `is_basement`, `open_shop_id`, `douyin_shop_id`, `business_day`, 
    `member_api_shield`, `area`, `cap`, `alias`, `baiwang_qr`, `service_tax_code`, `close_time`, `spm_ext`, 
    `status`, `del_flag`, `create_time`, `update_time`
) VALUES
"""

values_list = []
# id范围：2001 ~ 5000，正好3000条
for i in range(2001, 5001):
    # 随机经纬度，和你的逻辑一致
    lng = round(random.uniform(0, 180), 6)
    lat = round(random.uniform(0, 90), 6)
    # 单条值，完全匹配你的存储过程规则
    value = f"""({i}, {2000+i}, 17, '琪航品牌', 0, 0, '黄浦陆家浜路店_{i}', '001-001-0101-01021-{str(i).zfill(4)}', 1,
28, '上海市', 56, 152, '东区四组', '上海东区', 152, '', '', 0, '', '1380013{str(i).zfill(5)}', 'store{i}@test.com', 1,
17558, '', 0, 47, 0, '中国', 0, '', 0, '', 0, '', '地址_{i}', {lng}, {lat}, NULL, '2023-03-07', 0, '店长_{i}', '1390013{str(i).zfill(5)}',
NULL, NULL, '', '2', '', 0, 0, '0', '1', '2023-03-17', 0, 0, 0, '1', '', '', NULL, NULL, 0, 0, NOW(), NOW())"""
    values_list.append(value)

# 拼接成完整批量SQL
full_sql = sql_header + ",\n".join(values_list) + ";"

# 保存到文件
with open(output_file, "w", encoding="utf-8") as f:
    f.write(full_sql)

print("生成完成！共3000条数据，SQL已保存到 insert_store_3000.sql")