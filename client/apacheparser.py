import glob
import os
import re
import sys

from common import *


class ApacheNode:
    re_comment = re.compile(r"""^#.*$""")
    re_section_start = re.compile(r"""^<(?P<name>[^/\s>]+)\s*(?P<value>[^>]+)?>$""")
    re_section_end = re.compile(r"""^</(?P<name>[^\s>]+)\s*>$""")
    #re_statement = re.compile(r"""^(?P<name>[^\s]+)\s*(?P<value>.+)?$""")

    def __init__(self, name, values=[], section=False):
        self.name = name
        self.children = []
        self.values = values
        self.section = section

    def add_child(self, child):
        self.children.append(child)
        child.parent = self
        return child

    def find(self, path):
        """Return the first element which matches the path."""
        pathelements = path.strip('/').split('/')
        if not pathelements[0]:
            return self
        return self._find(pathelements)

    def _find(self, pathelements):
        if pathelements: # There is still more to do ...
            next = pathelements.pop(0)
            for child in self.children:
                # Case-insensitive comparison.
                if child.name.lower() == next.lower():
                    result = child._find(pathelements)
                    if result:
                        return result
            return None
        else: # no pathelements left, result is self
            return self

    def findall(self, path):
        """Return all elements which match the path."""
        pathelements = path.strip('/').split('/')
        if not pathelements[0]:
            return [self]
        return self._findall(pathelements)

    def _findall(self, pathelements):
        if pathelements: # there is still more to do ...
            result = []
            next = pathelements.pop(0)
            for child in self.children:
                # Case-insensitive comparison.
                if child.name.lower() == next.lower():
                    result.extend(child._findall(pathelements))
            return result
        else: # no pathelements left, result is self
            return [self]

    def print_r(self, indent=-1):
        """Recursively print node."""
        if self.section:
            if indent >= 0:
                print '    ' * indent + '<' + self.name + ' ' + (' '.join(self.values)) + '>'
            for child in self.children:
                child.print_r(indent + 1)
            if indent >= 0:
                print '    ' * indent + '</' + self.name + '>'
        else:
            if indent >= 0:
                print '    ' * indent + self.name + ' ' + ' '.join(self.values)

    @classmethod
    def parse_file(cls, file):
        """Parse a file."""
        try:
            f = open(file)
            root = cls._parse(f)
            f.close()
            return root
        except IOError:
            return False

    @classmethod
    def parse_string(cls, string):
        """Parse a string."""
        return cls._parse(string.splitlines())

    @classmethod
    def _parse(cls, itobj):
        root = node = ApacheNode('', section=True)

        for line in itobj:
            line = line.strip()

            if not line or cls.re_comment.match(line):
                continue

            # Concatenate multiline directives delimited by backslash-newlines.
            if line and line[-1] == '\\':
                while line[-1] == '\\':
                    line = ' '.join([line[:-1].strip(), itobj.next().strip()])

            m = cls.re_section_start.match(line)
            if m:
                values = m.group('value').split()
                new_node = ApacheNode(m.group('name'), values=values,
                                      section=True)
                node = node.add_child(new_node)
                continue

            m = cls.re_section_end.match(line)
            if m:
                if node.name != m.group('name'):
                    raise Exception("Section mismatch: '%s' should be '%s'" % (
                        m.group('name'), node.name))
                node = node.parent
                continue

            values = line.split()
            name = values.pop(0)

            # Capitalize first letter.
            if name[0].islower():
                name = name[0].upper() + name[1:]

            node.add_child(ApacheNode(name, values=values, section=False))

        return root


class ApacheConfig:
    def __init__(self):
        self.filename = None
        self.ac = None
        self.root = None
        self.directives = {}
        self.domains = {}

    def parse(self, filename):
        self.filename = filename
        self.ac = ApacheNode(filename)
        self.root = self.ac.parse_file(filename)
        self.scan_children(self.root.children)

    def get_body(self):
        re_comment = re.compile(r"""^#.*$""")

        try:
            config_file = open(self.filename, 'r')
            config_lines = config_file.readlines()
            config_file.close()
        except IOError:
            return ''

        return clean_body(config_lines, '#')

    def print_children(self, children, indent=-1):
        """Recursively print children."""
        indent += 1
        for child in children:
            print '\t' * indent + (child.section and '----- ' or '') + \
                  child.name, ' '.join(child.values), \
                  child.section and '-----' or ''
            print_children(child.children, indent)

    def scan_children(self, children, indent=-1):
        """Recursively scan children and build directives dictionary."""
        body_list = []
        for child in children:
            name = child.name
            value = ' '.join(child.values)

            body_list.append({'name': name, 'value': value,
                'children': self.scan_children(child.children, indent)})

            if name in self.directives:
                self.directives[name] += [value]
            # Check for lowercased directive.
            # TODO: Better check.
            elif name.lower() in self.directives:
                self.directives[name.lower()] += [value]
            else:
                self.directives[name] = [value]

        return body_list

    def get_directives(self):
        return self.directives

    def get_domains(self):
        vh = self.root.findall('VirtualHost')

        for v in vh:
            ports_str = ' '.join(v.values)

            # Strip all non-numeric characters.
            p = re.compile(r'[^0-9]+')
            ports_str = p.sub(' ', ports_str).strip()

            ports = re.split(' ', ports_str)

            sn = v.findall('ServerName')
            if sn:
                dn = sn[0].values[0]
                self.domains.setdefault(dn, []).append(ports)

        return self.domains

    def get_includes(self):
        included_list = []

        sr_node = self.root.find('ServerRoot')

        if DEBUG:
            server_root = APACHE_ROOT
        else:
            if sr_node:
                server_root = ''.join(sr_node.values)
                # Strip quotation marks.
                if server_root[0] in ('"', "'") and \
                   server_root[0] == server_root[-1]:
                    server_root = server_root[1:-1]
            else:
                server_root = APACHE_ROOT

        for i in self.root.findall('Include'):
            i = ''.join(i.values)

            i_fn = os.path.join(server_root, i)
            #print '-', i_fn

            # Shell-style filename expansion (e.g., `conf.d/*.conf`).
            included_list += glob.glob(i_fn)

        return included_list

