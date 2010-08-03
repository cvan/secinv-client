LittleSIS Client
================
LittleSIS scans the system for OS info, network interfaces, iptables rules,
and configuration files (Apache, PHP, MySQL, OpenSSH sshd). This is the client
agent used in cooperation with the XML-RPC-based LittleSIS server.

# Requirements

* Python 2.4 (or greater)

# Instructions

1. Edit `client/settings.conf` to update the server location, port, and
   miscellaneous settings as you see fit (e.g., system file paths).

2. Edit `client/auth.conf` with the machine's authorization token to compare
   against the token stored on the server.

