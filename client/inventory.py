from ConfigParser import ConfigParser
import os
import re
import subprocess
import string

from apacheparser import *
from common import *

# TODO: Use `logging`.


class Interfaces:
    @classmethod
    def get_interfaces(cls):
        """
        Return dictionary of IP address, MAC address, and netmask for each
        interface.
        """
        i_dict = {}

        open_files = subprocess.Popen(IFCONFIG, shell=True,
                                      stdout=subprocess.PIPE).communicate()[0]
        lines = open_files.split('\n')
        interface = ''

        for line in lines:
            if not line:
                continue

            ls = line.split()

            if ls[0].strip():
                interface = ls[0].strip()
                i_dict[interface] = {'i_ip': '', 'i_mac': '', 'i_mask': ''}

            # Get MAC address.
            if 'HWaddr' in ls:
                i_dict[interface]['i_mac'] = ls[ls.index('HWaddr') + 1].lower()

            # Get IP address and netmask.
            if 'inet' in ls:
                inet = ls[ls.index('inet') + 1]
                if ':' in inet:
                    i_dict[interface]['i_ip'] = inet.split(':')[1]
                else:
                    i_dict[interface]['i_ip'] = inet

                if ':' in ls[-1]:
                    i_dict[interface]['i_mask'] = ls[-1].split(':')[1]
                else:
                    i_dict[interface]['i_mask'] = ls[-1]

        return i_dict


class System:
    @classmethod
    def _get_ip(self):
        """Get `hostname` and return local IP address from hostname."""
        try:
            import socket
            sys_ip = socket.gethostbyaddr(socket.gethostname())[-1][0]
        except (socket.error, socket.herror, socket.gaierror):
            sys_ip = ''
        return sys_ip

    @classmethod
    def _get_hostname(self):
        """Parse `hostname` and return local hostname."""
        full_hn = subprocess.Popen(HOSTNAME, shell=True,
                                   stdout=subprocess.PIPE).communicate()[0]

        p = re.compile(r'([^\.]+)')
        m = p.match(full_hn)

        return m and m.group(0).strip() or ''

    @classmethod
    def _get_kernel_release(self):
        """
        Call `uname -r` and return kernel release version number.
        """
        kernel_rel = subprocess.Popen('%s -r' % UNAME, shell=True,
                                      stdout=subprocess.PIPE).communicate()[0]
        return kernel_rel.strip()

    @classmethod
    def _get_redhat_version(self, filename=RH_RELEASE):
        """
        Parse `redhat-release` file and return release name and version number.
        """
        rh_version = ''
        try:
            rh_file = open(filename, 'r')
            release_line = rh_file.readline()
            rh_file.close()

            p = re.compile(r'Red Hat Enterprise Linux \S+ release ([^\n].+)\n')
            m = p.match(release_line)
            if m:
                rh_version = m.group(1)
        except IOError:
            #raise Exception("Notice: Cannot open redhat-release file '%s'." % filename)
            print "Notice: Cannot open redhat-release file '%s'" % filename
            rh_version = ''

        return rh_version.strip()

    @classmethod
    def _ip_fwd_status(self, filename=IP_FORWARD):
        """
        Parse `ip_forward` file and return a boolean of IP forwarding status.
        """
        ip_fwd = 0
        try:
            ip_file = open(filename, 'r')
            status_line = ip_file.readline().strip()
            ip_file.close()

            if status_line == '1':
                ip_fwd = 1
        except IOError:
            #raise Exception("Notice: Cannot open ip_forward file '%s'." % filename)
            print "Notice: Cannot open ip_forward file '%s'" % filename

        return ip_fwd

    @classmethod
    def _nfs_status(self):
        """
        Check and return an integer of whether a NFS is currently mounted.
        """
        found_nfs = 0

        mount_info = subprocess.Popen('%s -l' % MOUNT, shell=True,
                                      stdout=subprocess.PIPE).communicate()[0]
        mount_info = mount_info.strip('\n')
        lines = mount_info.split('\n')

        for line in lines:
            if not line:
                continue

            p = re.compile(r'.+ type ([^\s].+) ')
            m = p.match(line)
            if m and m.group(1) == 'nfs':
                found_nfs = 1
                break

        return found_nfs

    @classmethod
    def get_system_dict(cls):
        """Build and return dictionary of assets fields."""
        i_dict = {'sys_ip': cls._get_ip(),
                       'hostname': cls._get_hostname(),
                       'kernel_rel': cls._get_kernel_release(),
                       'rh_rel': cls._get_redhat_version(),
                       'nfs': cls._nfs_status(),
                       'ip_fwd': cls._ip_fwd_status()}
        return i_dict


class Services:
    @classmethod
    def get_services(cls):
        """
        Parse `lsof -ni -P` and return a dictionary of all listening processes
        and ports.
        """
        ports_dict = {}

        open_files = subprocess.Popen('%s -ni -P' % LSOF, shell=True,
                                      stdout=subprocess.PIPE).communicate()[0]
        lines = open_files.split('\n')

        for line in lines:
            if not line:
                continue

            chunks = re.split('\s*', line)

            if not '(LISTEN)' in chunks:
                continue

            proc_name = chunks[0]
            full_name = chunks[-2]

            ports_dict[proc_name] = full_name.split(':')[1]

        return ports_dict


class RPMs:
    @classmethod
    def get_rpms(cls, filename=RPM_PKGS):
        """Get all RPMs installed."""
        rpms_dict = {'list': ''}

        try:
            rpmpkgs_file = open(filename, 'r')
            lines = rpmpkgs_file.readlines()
            rpmpkgs_file.close()

            lines_str = ''.join(lines)
            lines_str = lines_str.strip('\n')

            rpms_dict = {'list': lines_str}
        except IOError:
            # TODO: Logging Error.
            #raise Exception("Notice: Cannot open rpmpkgs file '%s'." % filename)
            print "Notice: Cannot open rpmpkgs file '%s'" % filename

        return rpms_dict


class SSHConfig:
    @classmethod
    def parse(cls, filename=SSH_CONFIG_FILE):
        """
        Parse SSH configuration file and a return a dictionary of
        body, parameters/values, and filename.
        """
        body = ''
        items = {}
        filename = path(filename)

        try:
            file_obj = open(filename, 'r')
            lines = file_obj.readlines()
            file_obj.close()

        except IOError:
            #raise Exception("Notice: Cannot open SSH config file '%s'." % filename)
            print "Notice: Cannot open SSH config file '%s'" % filename
            lines = ''

        if lines:
            body = ''
            for index, line in enumerate(lines):
                line = line.strip()

                if not line or (not PARSE_CONF_COMMENTS and line[0] == '#'):
                    continue

                # Concatenate multiline instructions delimited by backslash-newlines.
                if line and line[-1] == '\\':
                    while line[-1] == '\\':
                        line = ' '.join([line[:-1].strip(),
                                         lines[index + 1].strip()])
                        del lines[index + 1]

                if line[0] != '#':
                    ls = re.split('\s*', line)
    
                    if ls[0] in items:
                        items[ls[0]] += [' %s' % ' '.join(ls[1:])]
                    else:
                        items[ls[0]] = [' '.join(ls[1:])]

                body += '%s\n' % line

        ssh_dict = {'body': body, 'items': items, 'filename': filename}

        return ssh_dict


class IPTables:
    @classmethod
    def _status(self):
        """
        Check and return an integer of whether iptables are running.
        """
        ipt_status = 0

        status_info = subprocess.Popen('%s status' % IPTABLES, shell=True,
                                       stdout=subprocess.PIPE).communicate()[0]
        status_info = status_info.strip('\n')

        if status_info != 'Firewall is stopped.':
            ipt_status = 1

        return ipt_status

    @classmethod
    def _parse(self):
        """
        Parse IP tables and a return a dictionary of policies for each table.
        """
        ipt_dict = {}

        lines = subprocess.Popen(IPTABLES_SAVE, shell=True,
                                 stdout=subprocess.PIPE).communicate()[0]
        lines = lines.split('\n')

        table_name = ''
        body = ''

        for index, line in enumerate(lines):
            line = line.strip()

            if not line or (not PARSE_CONF_COMMENTS and line[0] == '#') or \
              (PARSE_CONF_COMMENTS and line.startswith('# Generated by') or \
               line.startswith('# Completed on')):
                continue

            # Concatenate multiline instructions delimited by backslash-newlines.
            if line and line[-1] == '\\':
                while line[-1] == '\\':
                    line = ' '.join([line[:-1].strip(),
                                     lines[index + 1].strip()])
                    del lines[index + 1]

            if line[0] == ':':
                # Chain specification.
                # :<chain-name> <chain-policy> [<packet-counter>:<byte-counter>]

                # Strip packet-counter and byte-counter.
                ls = line.split()
                if len(ls) > 2 and ls[0].strip():
                    chain_name = ls[0].strip()[1:]
                    chain_policy = ls[1].strip()
                    line = ':%s %s' % (chain_name, chain_policy)

            body += '%s\n' % line

        ipt_dict['body'] = body

        return ipt_dict

    @classmethod
    def get_ipt_dict(cls):
        """Build and return dictionary of iptables fields."""
        ipt_dict = {'status': cls._status(),
                    'rules': cls._parse()}
        return ipt_dict


class ApacheConfigList:
    def __init__(self):
        self.apache_configs = []

    def recurse_apache_includes(self, fn, includes_list):
        for i_fn in includes_list:
            i_ac = ApacheConfig()
            i_ac.parse(i_fn)

            i_apache = {'body': i_ac.get_body(),
                        'filename': i_fn,
                        'directives': i_ac.get_directives(),
                        'domains': i_ac.get_domains(),
                        'included': i_ac.get_includes()}

            # Remove circular includes.
            try:
                del i_apache['included'][i_apache['included'].index(fn)]
            except ValueError:
                pass

            self.apache_configs.append(i_apache)

            self.recurse_apache_includes(i_fn, i_apache['included'])

    def recurse(self):
        ac = ApacheConfig()
        ac.parse(APACHE_CONF)

        apache = {'body': ac.get_body(),
                  'filename': APACHE_CONF,
                  'directives': ac.get_directives(),
                  'domains': ac.get_domains(),
                  'included': ac.get_includes()}

        # Remove circular includes.
        try:
            del apache['included'][apache['included'].index(APACHE_CONF)]
        except ValueError:
            pass

        self.apache_configs.append(apache)

        self.recurse_apache_includes(APACHE_CONF, apache['included'])

    def get_apache_configs(self):
        if os.path.exists(APACHE_CONF):
            self.recurse()
        return self.apache_configs


class PHPConfig:
    def get_items(self):
        parameters = {}
        php_config = ConfigParser()

        try:
            php_config.readfp(file(path(PHP_INI)))
            sections = php_config.sections()
        except IOError:
            #sys.exit("Notice: Cannot open PHP configuration file '%s'" % PHP_INI)
            print "Notice: Cannot open PHP configuration file '%s'" % PHP_INI
            sections = []

        for section in sections:
            items = php_config.items(section)

            #parameters[section] = {}
            for item in items:
                #parameters[section][item[0]] = [item[1]]
                if item[0] in parameters:
                    parameters[item[0]] += [item[1]]
                else:
                    parameters[item[0]] = [item[1]]
                #parameters.setdefault(item[0], []).append(item[1])

        return parameters

    def parse(self):
        try:
            file_obj = open(path(PHP_INI), 'r')
            lines = file_obj.readlines()
            file_obj.close()
            
            body = clean_body(lines, ';')
            items = self.get_items()
            php_dict = {'body': body, 'items': items, 'filename': PHP_INI}
        except IOError:
            #raise Exception("Notice: Cannot open PHP configuration file '%s'" % PHP_INI)'
            print "Notice: Cannot open PHP configuration file '%s'" % PHP_INI
            php_dict = {'body': '', 'items': [], 'filename': ''}

        return php_dict


class MySQLConfig:
    def get_items(self):
        parameters = {}
        mysql_config = ConfigParser()

        try:
            mysql_config.readfp(file(path(MY_CNF)))
            sections = mysql_config.sections()
        except IOError:
            #sys.exit("Notice: Cannot open MySQL configuration file '%s'" % MY_CNF)
            print "Notice: Cannot open MySQL configuration file '%s'" % MY_CNF
            sections = []

        for section in sections:
            items = mysql_config.items(section)

            #parameters[section] = {}
            for item in items:
                #parameters[section][item[0]] = [item[1]]
                if item[0] in parameters:
                    parameters[item[0]] += [item[1]]
                else:
                    parameters[item[0]] = [item[1]]
                #parameters.setdefault(item[0], []).append(item[1])

        return parameters

    def parse(self):
        try:
            file_obj = open(path(MY_CNF), 'r')
            lines = file_obj.readlines()
            file_obj.close()

            body = clean_body(lines, '#')
            items = self.get_items()
            my_dict = {'body': body, 'items': items, 'filename': MY_CNF}
        except IOError:
            #raise Exception("Notice: Cannot open MySQL configuration file '%s'" % MY_CNF)'
            print "Notice: Cannot open MySQL configuration file '%s'" % MY_CNF
            my_dict = {'body': '', 'items': [], 'filename': ''}

        return my_dict

