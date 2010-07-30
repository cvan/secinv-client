from ConfigParser import ConfigParser
import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))

# Used to translate path in this directory to an absolute path.
path = lambda *a: os.path.join(ROOT, *a)

# Supress warnings.
import warnings
warnings.filterwarnings('ignore')


# Path to client configuration file.
CLIENT_CONFIG_FN = path('settings.conf')

client_config = ConfigParser()

try:
    client_config.readfp(file(CLIENT_CONFIG_FN))
except IOError:
    sys.exit("Error: Cannot open inventory configuration file '%s'"
             % CLIENT_CONFIG_FN)

## Server.
HOST = client_config.get('server', 'host')
PORT = client_config.get('server', 'port')
AUTH_KEY = client_config.get('server', 'auth_key')
DEBUG = client_config.get('server', 'debug').lower() == 'true' and True or False


## Paths.
RH_RELEASE = os.path.abspath(client_config.get('paths', 'rh_release'))
IP_FORWARD = os.path.abspath(client_config.get('paths', 'ip_forward'))
RPM_PKGS = os.path.abspath(client_config.get('paths', 'rpm_pkgs'))
SSH_CONFIG_FILE = os.path.abspath(client_config.get('paths', 'ssh_config_file'))
IPTABLES = client_config.get('paths', 'iptables')
PHP_INI = client_config.get('paths', 'php_ini')
MY_CNF = client_config.get('paths', 'my_cnf')

IFCONFIG = client_config.get('paths', 'ifconfig')
HOSTNAME = client_config.get('paths', 'hostname')
UNAME = client_config.get('paths', 'uname')
MOUNT = client_config.get('paths', 'mount')
LSOF = client_config.get('paths', 'lsof')
IPTABLES = client_config.get('paths', 'iptables')
IPTABLES_SAVE = client_config.get('paths', 'iptables_save')


## Apache.
APACHE_ROOT = os.path.abspath(client_config.get('apache', 'server_root'))
APACHE_CONF = os.path.abspath(client_config.get('apache', 'conf_file'))

APACHE_IGNORE_DIRECTIVES = [f.strip() for f in \
    re.split(',', client_config.get('apache', 'ignore_directives'))]


## Miscellaneous.
PARSE_CONF_COMMENTS = client_config.get('miscellaneous',
    'parse_conf_comments').lower() == 'true' and True or False



def clean_body(body, comments_prefix=('#')):
    """
    Clean up whitespace, multiline instructions, and comments (if applicable).
    """
    if not type(comments_prefix) in (tuple, list, str):
        raise TypeError

    if type(body) is list:
        lines = body
    else:
        lines = re.split('\n', body)
    
    body = ''

    for index, line in enumerate(lines):
        line = line.strip()

        if not line or (not PARSE_CONF_COMMENTS and line[0] in comments_prefix):
            continue

        # Concatenate multiline instructions delimited by backslash-newlines.
        if line and line[-1] == '\\':
            while line[-1] == '\\':
                line = ' '.join([line[:-1].strip(),
                                 lines[index + 1].strip()])
                del lines[index + 1]

        body += '%s\n' % line

    return body

