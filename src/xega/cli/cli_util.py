from datetime import datetime


def generate_benchmark_id():
    return (
        datetime.now().strftime("%Y-%m-%d-%H:%M:%S")
        + "-"
        + hex(hash(str(datetime.now().timestamp())))[-6:]
    )
