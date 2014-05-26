# A SQLAlchemy connection string
DB_CONN_STRING = 'sqlite:///qualtrics_stats.db'
# DB_CONN_STRING = 'mysql+oursql://root:password@localhost/qualtrics_stats'

# Address and port to listen on on `serve`
SERVER_LISTEN_ADDR = '0.0.0.0:8080'

# Where cron creates the json results
# {} -> job.id
CRON_RESULTS_PATH = "./json/{}.json"
