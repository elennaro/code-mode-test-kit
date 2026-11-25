"""Stand-in for a load test: a job that takes 60 seconds whatever starts it."""
import time

time.sleep(60)
print("load test done: 60 s, 0 errors")
