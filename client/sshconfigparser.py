import glob
import os
import re
import sys

from common import *


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

                if len(line) == 0 or (not PARSE_CONF_COMMENTS and line[0] == '#'):
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

print SSHConfig.parse()

