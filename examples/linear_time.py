import drore
import re
import time


def timeit(func, *args):
    start_time = time.monotonic()
    _ = func(*args)
    end_time = time.monotonic()
    func_name = f"{func.__module__}.{func.__name__}"
    print(func_name, "took", end_time - start_time, "seconds")

timeit(re.match, r'(a+)+b', 'a'*27 + 'c')
timeit(drore.match, r'(a+)+b', 'a'*27 + 'c')

print()
with drore.DebugMode():
    drore.match(r'a++b', 'aaaaaaaac')
