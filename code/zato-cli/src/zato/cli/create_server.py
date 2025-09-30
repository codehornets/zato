# -*- coding: utf-8 -*-

"""
Copyright (C) 2024, Zato Source s.r.o. https://zato.io

Licensed under AGPLv3, see LICENSE.txt for terms and conditions.
"""

# stdlib
from copy import deepcopy
from dataclasses import dataclass

# Zato
from zato.cli import common_odb_opts, common_scheduler_server_api_client_opts, common_scheduler_server_address_opts, \
    sql_conf_contents, ZatoCommand
from zato.common.api import CONTENT_TYPE, Default_Service_File_Data, NotGiven, SCHEDULER
from zato.common.crypto.api import ServerCryptoManager
from zato.common.simpleio_ import simple_io_conf_contents
from zato.common.util.api import as_bool, get_demo_py_fs_locations
from zato.common.util.config import get_scheduler_api_client_for_server_password, get_scheduler_api_client_for_server_username
from zato.common.util.open_ import open_r, open_w

# ################################################################################################################################
# ################################################################################################################################

if 0:
    from zato.common.typing_ import any_

# ################################################################################################################################
# ################################################################################################################################

# For pyflakes
simple_io_conf_contents = simple_io_conf_contents

# ################################################################################################################################
# ################################################################################################################################

server_conf_dict = deepcopy(CONTENT_TYPE)

# ################################################################################################################################
# ################################################################################################################################

server_conf_template = """[main]
gunicorn_bind=0.0.0.0:{{port}}
gunicorn_worker_class=gevent
gunicorn_workers={{gunicorn_workers}}
gunicorn_timeout=1234567890
gunicorn_user=
gunicorn_group=
gunicorn_proc_name=
gunicorn_logger_class=
gunicorn_graceful_timeout=1

work_dir=../../work

deployment_lock_expires=1073741824 # 2 ** 30 seconds = +/- 34 years
deployment_lock_timeout=180

token=zato+secret://zato.server_conf.main.token

[http_response]
code_400_message=400 Bad Request
code_400_content_type=text/plain
code_401_message=401 Unauthorized
code_401_content_type=text/plain
code_403_message=403 Forbidden
code_403_content_type=text/plain
code_404_message=404 Not Found
code_404_content_type=text/plain
code_405_message=405 Not Allowed
code_405_content_type=text/plain
code_500_message=500 Internal Server Error
code_500_content_type=text/plain

[crypto]
use_tls=False
tls_version=TLSv1
tls_ciphers=ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-AES128-SHA256:ECDHE-RSA-AES128-SHA256:ECDHE-ECDSA-AES128-SHA:ECDHE-RSA-AES256-SHA384:ECDHE-RSA-AES128-SHA:ECDHE-ECDSA-AES256-SHA384:ECDHE-ECDSA-AES256-SHA:ECDHE-RSA-AES256-SHA:DHE-RSA-AES128-SHA256:DHE-RSA-AES128-SHA:DHE-RSA-AES256-SHA256:DHE-RSA-AES256-SHA:ECDHE-ECDSA-DES-CBC3-SHA:ECDHE-RSA-DES-CBC3-SHA:EDH-RSA-DES-CBC3-SHA:AES128-GCM-SHA256:AES256-GCM-SHA384:AES128-SHA256:AES256-SHA256:AES128-SHA:AES256-SHA:DES-CBC3-SHA:!DSS
tls_client_certs=optional
priv_key_location=zato-server-priv-key.pem
pub_key_location=zato-server-pub-key.pem
cert_location=zato-server-cert.pem
ca_certs_location=zato-server-ca-certs.pem

[odb]
db_name={{odb_db_name}}
engine={{odb_engine}}
extra=echo=False
host={{odb_host}}
port={{odb_port}}
password=zato+secret://zato.server_conf.odb.password
pool_size={{odb_pool_size}}
username={{odb_user}}
use_async_driver=True

[scheduler]
scheduler_host={{scheduler_host}}
scheduler_port={{scheduler_port}}
scheduler_use_tls={{scheduler_use_tls}}
scheduler_api_username={{scheduler_api_client_for_server_username}}
scheduler_api_password={{scheduler_api_client_for_server_password}}

[hot_deploy]
pickup_dir=../../pickup/incoming/services
backup_history=100
backup_format=bztar
delete_after_pick_up=False
max_batch_size=1000 # In kilobytes, default is 1 megabyte
redeploy_on_parent_change=True

# These three are relative to work_dir
current_work_dir=./hot-deploy/current
backup_work_dir=./hot-deploy/backup
last_backup_work_dir=./hot-deploy/backup/last

[misc]
return_internal_objects=False
internal_services_may_be_deleted=False
initial_cluster_name={{initial_cluster_name}}
initial_server_name={{initial_server_name}}
queue_build_cap=30000000 # All queue-based connections need to initialize in that many seconds
http_proxy=
locale=
ensure_sql_connections_exist=True
http_server_header=Apache
needs_x_zato_cid=False
return_tracebacks=True
default_error_message="An error has occurred"
startup_callable=
service_invoker_allow_internal="demo.ping", "/zato/api/invoke/service_name"

[http]
methods_allowed=GET, POST, DELETE, PUT, PATCH, HEAD, OPTIONS

[kvdb]
host={{kvdb_host}}
port={{kvdb_port}}
unix_socket_path=
password=zato+secret://zato.server_conf.kvdb.password
db=0
socket_timeout=
charset=
errors=
use_redis_sentinels=False
redis_sentinels=
redis_sentinels_master=
shadow_password_in_logs=True
log_connection_info_sleep_time=5 # In seconds

[startup_services]
zato.updates.check-updates=
demo.input-logger=Sample payload for a startup service

[user_config]
# All paths are either absolute or relative to the directory server.conf is in
user=./user.conf

[component_enabled]
email=True
search=True
odoo=True

[content_type]
json = {JSON}

[preferred_address]
address=
ip=10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16, eth0
boot_if_preferred_not_found=False
allow_loopback=False

[logging]
http_access_log_ignore=
rest_log_ignore=/zato/admin/invoke, /metrics, /zato/ping

[os_environ]
sample_key=sample_value

[command_set_scheduler]

""".format(**server_conf_dict)

# ################################################################################################################################

pickup_conf = """#[hot-deploy.user.local-dev]
#pickup_from=/uncomment/this/stanza/to/enable/a/custom/location
"""

# ################################################################################################################################

demo_zrules_contents = """
# ################################################################################################################################

rule
    Airport_01_Flight_Delays
docs
    "Handles passenger notifications and accommodations during flight delays exceeding threshold times."
when
    flight_delay > 120 and
    passenger.type in ['platinum', 'diamond'] and
    is_international == True
then
    send_notification = True
    offer_accomodation = True
    template = 'DelayAlert'

# ################################################################################################################################

rule
    Airport_02_Passenger_Flow
docs
    "Optimizes processing point operations in response to passenger volume and terminal congestion."
defaults
    max_wait_time = 25
when
    processing_point.wait_time > max_wait_time and
    departing_flights_count.next_hour >= 5 and
    terminal.passenger_density > 75
then
    should_open_lane = True
    redeploy_staff = 'FloatingAssistant'
    staff_count = 2

# ################################################################################################################################

rule
    rule_3
docs
    This is a docstring
    it can be multiline
defaults
    max = {'a':'b'}
when
    abc == 123 or
    abc == 456
    # result1.customer_type in ['abc', 'def']
then
    fee_waiver = True
    dedicated_advisor = True
    status = {'key1':'value1', 'key2':'value2'}

# ################################################################################################################################
""".strip()

# ################################################################################################################################

user_conf_contents = """[sample_section]
string_key=sample_string
list_key=sample,list
"""

# ################################################################################################################################

secrets_conf_template = """
[secret_keys]
key1={keys_key1}

[zato]
well_known_data={zato_well_known_data} # Pi number
server_conf.kvdb.password={zato_kvdb_password}
server_conf.main.token={zato_main_token}
server_conf.odb.password={zato_odb_password}
"""

# ################################################################################################################################

default_odb_pool_size = 60

# ################################################################################################################################

directories = (
    'config',
    'config/repo',
    'config/repo/static',
    'logs',
    'pickup',
    'pickup/incoming',
    'pickup/processed',
    'pickup/incoming/services',
    'pickup/incoming/user',
    'pickup/incoming/user-conf',
    'work',
    'work/hot-deploy',
    'work/hot-deploy/current',
    'work/hot-deploy/backup',
    'work/hot-deploy/backup/last',
)

# ################################################################################################################################
# ################################################################################################################################

@dataclass(init=False)
class SchedulerConfigForServer:
    scheduler_host: 'str'
    scheduler_port: 'int'
    scheduler_use_tls: 'bool'

    class api_client:

        class from_server_to_scheduler:
            username: 'str'
            password: 'str'

        class from_scheduler_to_server:
            username: 'str'
            password: 'str'

# ################################################################################################################################
# ################################################################################################################################

class Create(ZatoCommand):
    """ Creates a new Zato server
    """
    needs_empty_dir = True

    opts:'any_' = deepcopy(common_odb_opts)

    opts.append({'name':'cluster_name', 'help':'Name of the cluster to join'})
    opts.append({'name':'server_name', 'help':'Server\'s name'})
    opts.append({'name':'--pub-key-path', 'help':'Path to the server\'s public key in PEM'})
    opts.append({'name':'--priv-key-path', 'help':'Path to the server\'s private key in PEM'})
    opts.append({'name':'--cert-path', 'help':'Path to the server\'s certificate in PEM'})
    opts.append({'name':'--ca-certs-path', 'help':'Path to list of PEM certificates the server will trust'})
    opts.append({'name':'--secret-key', 'help':'Server\'s secret key (must be the same for all servers)'})
    opts.append({'name':'--http-port', 'help':'Server\'s HTTP port'})
    opts.append({'name':'--scheduler-host', 'help':'Deprecated. Use --scheduler-address-for-server instead.'})
    opts.append({'name':'--scheduler-port', 'help':'Deprecated. Use --scheduler-address-for-server instead.'})
    opts.append({'name':'--threads', 'help':'How many main threads the server should use', 'default':1}) # type: ignore

    opts += deepcopy(common_scheduler_server_address_opts)
    opts += deepcopy(common_scheduler_server_api_client_opts)

# ################################################################################################################################

    def __init__(self, args:'any_') -> 'None':

        # stdlib
        import os
        import uuid

        super(Create, self).__init__(args)
        self.target_dir = os.path.abspath(args.path)
        self.dirs_prepared = False
        self.token = uuid.uuid4().hex.encode('utf8')

# ################################################################################################################################

    def allow_empty_secrets(self):
        return True

# ################################################################################################################################

    def prepare_directories(self, show_output:'bool') -> 'None':

        # stdlib
        import os

        if show_output:
            self.logger.debug('Creating directories..')

        for d in sorted(directories):
            d = os.path.join(self.target_dir, d)
            if show_output:
                self.logger.debug('Creating %s', d)
            os.mkdir(d)

        self.dirs_prepared = True

# ################################################################################################################################

    def _get_scheduler_config(self, args:'any_', secret_key:'bytes') -> 'SchedulerConfigForServer':

        # stdlib
        import os

        # Local variables
        use_tls = NotGiven

        # Our response to produce
        out = SchedulerConfigForServer()

        # Extract basic information about the scheduler the server will be invoking ..
        use_tls, host, port = self._extract_address_data(
            args,
            'scheduler_address_for_server',
            'scheduler_host',
            'scheduler_port',
            SCHEDULER.DefaultHost,
            SCHEDULER.DefaultPort,
        )

        # .. now, we can assign host and port to the response ..
        out.scheduler_host = host
        out.scheduler_port = port

        # Extract API credentials
        cm = ServerCryptoManager.from_secret_key(secret_key)
        scheduler_api_client_for_server_username = get_scheduler_api_client_for_server_username(args)
        scheduler_api_client_for_server_password = get_scheduler_api_client_for_server_password(args, cm)

        out.api_client.from_server_to_scheduler.username = scheduler_api_client_for_server_username
        out.api_client.from_server_to_scheduler.password = scheduler_api_client_for_server_password

        # This can be overridden through environment variables
        env_keys = ['Zato_Server_To_Scheduler_Use_TLS', 'ZATO_SERVER_SCHEDULER_USE_TLS']
        for key in env_keys:
            if value := os.environ.get(key):
                use_tls = as_bool(value)
                break
        else:
            if use_tls is NotGiven:
                use_tls = False

        out.scheduler_use_tls = use_tls # type: ignore

        # .. finally, return the response to our caller.
        return out

# ################################################################################################################################

    def _add_demo_service(self, fs_location:'str', full_path:'str') -> 'None':

        with open_w(fs_location) as f:
            data = Default_Service_File_Data.format(**{
                'full_path': full_path,
            })
            _ = f.write(data)

# ################################################################################################################################

    def execute(
        self,
        args:'any_',
        default_http_port:'any_'=None,
        show_output:'bool'=True,
        return_server_id:'bool'=False
    ) -> 'int | None':

        # stdlib
        import os
        import platform
        from datetime import datetime
        from traceback import format_exc

        # Cryptography
        from cryptography.fernet import Fernet

        # SQLAlchemy
        from sqlalchemy.exc import IntegrityError

        # Python 2/3 compatibility
        from six import PY3

        # Zato
        from zato.common.api import SERVER_JOIN_STATUS
        from zato.common.crypto.const import well_known_data
        from zato.common.defaults import http_plain_server_port
        from zato.common.odb.model import Cluster, Server
        from zato.common.util.logging_ import get_logging_conf_contents

        logging_conf_contents = get_logging_conf_contents()

        files = {
            'config/repo/logging.conf': logging_conf_contents,
            'config/repo/sql.conf': sql_conf_contents,
        }

        default_http_port = default_http_port or http_plain_server_port

        engine = self._get_engine(args)
        session = self._get_session(engine) # type: ignore

        cluster = session.query(Cluster).filter(Cluster.name == args.cluster_name).first() # type: ignore

        if not cluster:
            self.logger.error("Cluster `%s` doesn't exist in ODB", args.cluster_name)
            return self.SYS_ERROR.NO_SUCH_CLUSTER

        server = Server(cluster=cluster)
        server.name = args.server_name
        if isinstance(self.token, (bytes, bytearray)): # type: ignore
            server.token = self.token.decode('utf8') # type: ignore
        else:
            server.token = self.token
        server.last_join_status = SERVER_JOIN_STATUS.ACCEPTED # type: ignore
        server.last_join_mod_by = self._get_user_host() # type: ignore
        server.last_join_mod_date = datetime.utcnow() # type: ignore
        session.add(server)

        try:
            if not self.dirs_prepared:
                self.prepare_directories(show_output)

            repo_dir = os.path.join(self.target_dir, 'config', 'repo')

            # Note that server crypto material is optional so if none was given on input
            # this command will be a no-op.
            self.copy_server_crypto(repo_dir, args)

            if show_output:
                self.logger.debug('Created a repo in {}'.format(repo_dir))
                self.logger.debug('Creating files..')

            for file_name, contents in sorted(files.items()):
                file_name = os.path.join(self.target_dir, file_name)
                if show_output:
                    self.logger.debug('Creating {}'.format(file_name))
                f = open_w(file_name)
                _ = f.write(contents)
                f.close()

            logging_conf_loc = os.path.join(self.target_dir, 'config/repo/logging.conf')

            logging_conf = open_r(logging_conf_loc).read()
            _ = open_w(logging_conf_loc).write(logging_conf.format(log_path=os.path.join(self.target_dir, 'logs', 'zato.log')))

            if show_output:
                self.logger.debug('Logging configuration stored in {}'.format(logging_conf_loc))

            odb_engine=args.odb_type
            if odb_engine.startswith('postgresql'):
                odb_engine = 'postgresql+pg8000'

            server_conf_loc = os.path.join(self.target_dir, 'config/repo/server.conf')
            server_conf = open_w(server_conf_loc)

            # There will be multiple keys in future releases to allow for key rotation
            secret_key = args.secret_key or Fernet.generate_key()

            try:
                threads = int(args.threads)
            except Exception:
                threads = 1

            # Build the scheduler's configuration
            scheduler_config = self._get_scheduler_config(args, secret_key)

            # Substitue the variables ..
            server_conf_data = server_conf_template.format(
                    port=getattr(args, 'http_port', None) or default_http_port,
                    gunicorn_workers=threads,
                    odb_db_name=args.odb_db_name or args.sqlite_path,
                    odb_engine=odb_engine,
                    odb_host=args.odb_host or '',
                    odb_port=args.odb_port or '',
                    odb_pool_size=default_odb_pool_size,
                    odb_user=args.odb_user or '',
                    kvdb_host=self.get_arg('kvdb_host'),
                    kvdb_port=self.get_arg('kvdb_port'),
                    initial_cluster_name=args.cluster_name,
                    initial_server_name=args.server_name,
                    scheduler_host=scheduler_config.scheduler_host,
                    scheduler_port=scheduler_config.scheduler_port,
                    scheduler_use_tls=scheduler_config.scheduler_use_tls,
                    scheduler_api_client_for_server_username=scheduler_config.api_client.from_server_to_scheduler.username,
                    scheduler_api_client_for_server_password=scheduler_config.api_client.from_server_to_scheduler.password,
                )

            # .. and special-case this one as it contains the {} characters
            # .. which makes it more complex to substitute them.
            server_conf_data = server_conf_data.replace('/zato/api/invoke/service_name', '/zato/api/invoke/{service_name}')

            _ = server_conf.write(server_conf_data)
            server_conf.close()

            pickup_conf_loc = os.path.join(self.target_dir, 'config/repo/pickup.conf')
            pickup_conf_file = open_w(pickup_conf_loc)
            _ = pickup_conf_file.write(pickup_conf)
            pickup_conf_file.close()

            user_conf_loc = os.path.join(self.target_dir, 'config/repo/user.conf')
            user_conf = open_w(user_conf_loc)
            _ = user_conf.write(user_conf_contents)
            user_conf.close()

            # On systems other than Windows, where symlinks are not fully supported,
            # for convenience and backward compatibility,
            # create a shortcut symlink from incoming/user-conf to config/repo/user-conf.

            system = platform.system()
            is_windows = 'windows' in system.lower()

            if not is_windows:
                user_conf_dir = os.path.join(self.target_dir, 'config', 'repo', 'user-conf')
                user_conf_src = os.path.join(self.target_dir, 'pickup', 'incoming', 'user-conf')
                os.symlink(user_conf_src, user_conf_dir)

                # Add default rules
                demo_zrules_loc = os.path.join(user_conf_dir, 'demo.zrules')
                demo_zrules = open_w(demo_zrules_loc)
                _ = demo_zrules.write(demo_zrules_contents)
                demo_zrules.close()

            fernet1 = Fernet(secret_key)

            secrets_conf_loc = os.path.join(self.target_dir, 'config/repo/secrets.conf')
            secrets_conf = open_w(secrets_conf_loc)

            kvdb_password = self.get_arg('kvdb_password') or ''
            kvdb_password = kvdb_password.encode('utf8')
            kvdb_password = fernet1.encrypt(kvdb_password)
            kvdb_password = kvdb_password.decode('utf8')

            odb_password = self.get_arg('odb_password') or ''
            odb_password = odb_password.encode('utf8')
            odb_password = fernet1.encrypt(odb_password)
            odb_password = odb_password.decode('utf8')

            zato_well_known_data = fernet1.encrypt(well_known_data.encode('utf8'))
            zato_well_known_data = zato_well_known_data.decode('utf8')

            if isinstance(secret_key, (bytes, bytearray)):
                secret_key = secret_key.decode('utf8')

            zato_main_token = fernet1.encrypt(self.token)
            zato_main_token = zato_main_token.decode('utf8')

            _ = secrets_conf.write(secrets_conf_template.format(
                keys_key1=secret_key,
                zato_well_known_data=zato_well_known_data,
                zato_kvdb_password=kvdb_password,
                zato_main_token=zato_main_token,
                zato_odb_password=odb_password,
            ))
            secrets_conf.close()

            bytes_to_str_encoding = 'utf8' if PY3 else ''

            simple_io_conf_loc = os.path.join(self.target_dir, 'config/repo/simple-io.conf')
            simple_io_conf = open_w(simple_io_conf_loc)
            _ = simple_io_conf.write(simple_io_conf_contents.format(
                bytes_to_str_encoding=bytes_to_str_encoding
            ))
            simple_io_conf.close()

            if show_output:
                self.logger.debug('Core configuration stored in {}'.format(server_conf_loc))

            # Prepare paths for the demo service ..
            demo_py_fs = get_demo_py_fs_locations(self.target_dir)

            # .. and create it now.
            self._add_demo_service(demo_py_fs.pickup_incoming_full_path, demo_py_fs.pickup_incoming_full_path)
            self._add_demo_service(demo_py_fs.work_dir_full_path, demo_py_fs.pickup_incoming_full_path)

            # Initial info
            self.store_initial_info(self.target_dir, self.COMPONENTS.SERVER.code)

            session.commit()

        except IntegrityError:
            msg = 'Server name `{}` already exists'.format(args.server_name)
            if self.verbose:
                msg += '. Caught an exception:`{}`'.format(format_exc())
            self.logger.error(msg)
            session.rollback()

            return self.SYS_ERROR.SERVER_NAME_ALREADY_EXISTS

        except Exception:
            self.logger.error('Could not create the server, e:`%s`', format_exc())
            session.rollback()
        else:
            if show_output:
                self.logger.debug('Server added to the ODB')

        if show_output:
            if self.verbose:
                msg = """Successfully created a new server.
You can now start it with the 'zato start {}' command.""".format(self.target_dir)
                self.logger.debug(msg)
            else:
                self.logger.info('OK')

        # This is optional - need only by quickstart.py and needs to be requested explicitly,
        # otherwise it would be construed as a non-0 return code from this process.
        if return_server_id:
            return server.id # type: ignore

# ################################################################################################################################
# ################################################################################################################################
