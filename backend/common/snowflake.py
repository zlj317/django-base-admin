"""雪花算法（Snowflake）：分布式唯一 ID 生成器。"""
# 模块用途：在应用层生成全局唯一、趋势递增的 64 位整数主键，替代数据库自增。
# 被谁调用：common/fields.py 的 SnowflakeIDField 默认值，以及需要提前拿到主键的业务代码。
# 关键约定：单进程内线程安全；多进程部署时必须给每个进程配置不同的 SNOWFLAKE_WORKER_ID，
#           否则不同进程落在同一毫秒时可能生成重复 ID；系统时钟回拨时沿用上次时间戳。
import os  # 读取环境变量中的机器标识
import threading  # 进程内多线程并发需要加锁保证序号不重复
import time  # 使用毫秒时间戳作为 ID 的高位

# 时间起点：2024-01-01 00:00:00 UTC，缩短时间戳位数，延长可用年限
EPOCH = 1704067200000

# 机器号取值范围 0-1023（10 位）；& 0x3FF 做兜底截断，避免配置越界污染时间戳所在的位。
WORKER_ID = int(os.environ.get('SNOWFLAKE_WORKER_ID', '1')) & 0x3FF  # 10 位机器标识，支持 0-1023

_lock = threading.Lock()  # 互斥锁，避免同一毫秒内多线程取到相同序号
_last_timestamp = 0  # 上一次生成 ID 使用的毫秒时间戳
_sequence = 0  # 当前毫秒内的序号（0-4095）


# 模块唯一入口：调用方都通过 next_id() 取号，不直接读写内部状态，便于后续替换算法。
def next_id():
    # 返回 64 位正整数，可直接写入 BIGINT 主键列；同一进程内趋势递增，便于索引插入。
    """生成一个 64 位正整数 ID：时间戳(41) + 机器号(10) + 序号(12)。"""
    # 函数会写入这两个模块级变量，必须先声明 global，否则赋值只会创建局部变量。
    global _last_timestamp, _sequence

    # 锁范围覆盖“读时间 → 判定序号 → 拼装返回”全过程，保证同一毫秒内序号分配有序不重复。
    with _lock:  # 全程持锁，保证并发下单调递增且不冲突
        # time.time() 是秒级浮点，乘 1000 后取整得到毫秒，与 EPOCH 的单位保持一致。
        timestamp = int(time.time() * 1000)  # 当前毫秒时间戳
        # NTP 校时或人工改表可能让时间倒退，此时不能生成更小的 ID，先退化为上次时间戳。
        if timestamp < _last_timestamp:  # 系统时钟回拨，退化为使用上次时间戳
            timestamp = _last_timestamp
        # 同一毫秒内靠 12 位序号区分，单毫秒最多 4096 个 ID。
        if timestamp == _last_timestamp:  # 同一毫秒内自增序号
            _sequence = (_sequence + 1) & 0xFFF  # 序号溢出时归零
            # 序号回绕为 0 说明本毫秒额度已用尽，忙等进入下一毫秒，避免产生重复 ID。
            if _sequence == 0:  # 当前毫秒序号用尽，等待下一毫秒
                while timestamp <= _last_timestamp:
                    # 循环重新采样系统时间，直到进入新的一毫秒；此处持有锁自旋，极端高并发下会有短暂等待。
                    timestamp = int(time.time() * 1000)
        # 时间戳前进说明进入新毫秒，序号必须归零，否则会与上一毫秒的序号区间重叠。
        else:
            # 跨入新毫秒，序号从 0 重新计数。
            _sequence = 0  # 进入新的毫秒，序号重置
        # 无论走哪个分支都要记录，作为下一轮的比较基准（时钟回拨判定也依赖它）。
        _last_timestamp = timestamp  # 记录本次时间戳
        # 位运算拼装：41 位毫秒差左移 22 位，机器号左移 12 位，末 12 位放序号。
        return ((timestamp - EPOCH) << 22) | (WORKER_ID << 12) | _sequence  # 拼装最终 ID
