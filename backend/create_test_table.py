"""临时脚本：创建测试业务表 biz_student（验证后可保留作演示数据）。"""
import os
import sys

sys.path.insert(0, r'd:\other\django-base-admin\backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django

django.setup()

from django.db import connection

with connection.cursor() as cursor:
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS `biz_student` (
          `id`          BIGINT UNSIGNED NOT NULL COMMENT '主键ID',
          `name`        VARCHAR(50)  NOT NULL COMMENT '学生姓名',
          `age`         INT          DEFAULT NULL COMMENT '年龄',
          `gender`      TINYINT(1)   DEFAULT 0 COMMENT '性别（字典sys_user_sex）',
          `phone`       VARCHAR(20)  DEFAULT NULL COMMENT '手机号',
          `email`       VARCHAR(100) DEFAULT NULL COMMENT '邮箱',
          `enroll_date` DATE         DEFAULT NULL COMMENT '入学日期',
          `score`       DECIMAL(5,2) DEFAULT NULL COMMENT '总分',
          `address`     VARCHAR(255) DEFAULT NULL COMMENT '家庭住址',
          `remark`      VARCHAR(500) DEFAULT NULL COMMENT '备注',
          `create_by`   VARCHAR(64)  DEFAULT NULL COMMENT '创建人',
          `create_time` DATETIME     DEFAULT NULL COMMENT '创建时间',
          `update_by`   VARCHAR(64)  DEFAULT NULL COMMENT '更新人',
          `update_time` DATETIME     DEFAULT NULL COMMENT '更新时间',
          `is_deleted`  TINYINT(1)   NOT NULL DEFAULT 0 COMMENT '逻辑删除',
          PRIMARY KEY (`id`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='学生信息表'
    """)
print('biz_student 表已就绪')
