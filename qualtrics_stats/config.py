# A SQLAlchemy connection string
DB_CONN_STRING = 'mysql+oursql://harvard:Biz6sU1UtURniPoi@atlas2.cifappqfiyph.us-east-1.rds.amazonaws.com/atlas'

# Address and port to listen on on `serve`
SERVER_LISTEN_ADDR = '0.0.0.0:8080'

# Where cron creates the json results
# {} -> job.id
CRON_RESULTS_PATH = "./json/{}.json"

# Authentication parameters for the admin panel
# The password is generated like this:
# >>> binascii.hexlify(scrypt.hash(password, '6cFp3RgPkd8ABVZugrbu', N=1 << 16))
ADMIN_USER = 'admin'
ADMIN_PASS = 'e09724d24f4ccd1f72862285fbc565266b7b6922607c7e77fae24ec155937311e2378a75ea5bbaee5c9c80dcf3e374605dd41a03fee51e170226435e036c1fcf'
