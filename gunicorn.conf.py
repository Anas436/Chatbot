import multiprocessing

# Bind to the Render-provided port
bind = "0.0.0.0:10000"

# Optimize for memory-constrained environment
workers = 1
worker_class = "sync"
worker_connections = 1000
timeout = 120
keepalive = 2

# Memory optimization
max_requests = 1000
max_requests_jitter = 100
preload_app = True
