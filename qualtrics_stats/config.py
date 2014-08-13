# A SQLAlchemy connection string
DB_CONN_STRING = 'sqlite:///qualtrics_stats.db'
# DB_CONN_STRING = 'mysql+oursql://root:password@localhost/qualtrics_stats'

# Address and port to listen on on `serve`
SERVER_LISTEN_ADDR = '0.0.0.0:8080'

# Where cron creates the json results
# {} -> job.id
CRON_RESULTS_PATH = "./json/{}.json"

# Authentication parameters for the admin panel
# The password is generated like this:
# >>> binascii.hexlify(scrypt.hash(password, '6cFp3RgPkd8ABVZugrbu', N=1 << 16))
ADMIN_USER = 'admin'
ADMIN_PASS = '030c9959ba9381a12a0831492c97cb023d3f74d67c548a6db24d3ef2cc24ddd9af0aaa5c04718cd13be9dd60a426393bcd540730408f2cf582c42e60b61b4b2d'
