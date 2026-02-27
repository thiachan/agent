module.exports = {
  apps: [
    {
      name: 'agent-backend',
      cwd: '/home/ubuntu/AGENT/backend',
      interpreter: '/home/ubuntu/AGENT/backend/venv/bin/python',
      script: '-m',
      args: 'uvicorn main:app --host 0.0.0.0 --port 8000 --limit-concurrency 1000 --timeout-keep-alive 5 --ws-max-size 16777216',
      watch: false,
      autorestart: true,
      restart_delay: 3000,
      max_restarts: 20,
      env: {
        PYTHONPATH: '/home/ubuntu/AGENT/backend',
      },
      error_file: '/tmp/agent-backend-err.log',
      out_file: '/tmp/agent-backend-out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss',
    },
    {
      name: 'agent-frontend',
      cwd: '/home/ubuntu/AGENT',
      script: 'node_modules/.bin/next',
      args: 'start -H 0.0.0.0',
      watch: false,
      autorestart: true,
      restart_delay: 3000,
      max_restarts: 20,
      error_file: '/tmp/agent-frontend-err.log',
      out_file: '/tmp/agent-frontend-out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss',
    },
  ],
}
