"""雪花算法（Snowflake）：分布式唯一 ID 生成器。"""
import os  # 读取环境变量中的机器标识
import threading  # 进程内多线程并发需要加锁保证序号不重复
import time  # 使用毫秒时间戳作为 ID 的高位

# 时间起点：2024-01-01 00:00:00 UTC，缩短时间戳位数，延长可用年限
EPOCH = 1704067200000

WORKER_ID = int(os.environ.get('SNOWFLAKE_WORKER_ID', '1')) & 0x3FF  # 10 位机器标识，支持 0-1023

_lock = threading.Lock()  # 互斥锁，避免同一毫秒内多线程取到相同序号
_last_timestamp = 0  # 上一次生成 ID 使用的毫秒时间戳
_sequence = 0  # 当前毫秒内的序号（0-4095）


def next_id():
    """生成一个 64 位正整数 ID：时间戳(41) + 机器号(10) + 序号(12)。"""
    global _last_timestamp, _sequence

    with _lock:  # 全程持锁，保证并发下单调递增且不冲突
        timestamp = int(time.time() * 1000)  # 当前毫秒时间戳
        if timestamp < _last_timestamp:  # 系统时钟回拨，退化为使用上次时间戳
            timestamp = _last_timestamp
        if timestamp == _last_timestamp:  # 同一毫秒内自增序号
            _sequence = (_sequence + 1) & 0xFFF  # 序号溢出时归零
            if _sequence == 0:  # 当前毫秒序号用尽，等待下一毫秒
                while timestamp <= _last_timestamp:
                    timestamp = int(time.time() * 1000)
        else:
            _sequence = 0  # 进入新的毫秒，序号重置
        _last_timestamp = timestamp  # 记录本次时间戳
        return ((timestamp - EPOCH) << 22) | (WORKER_ID << 12) | _sequence  # 拼装最终 ID
