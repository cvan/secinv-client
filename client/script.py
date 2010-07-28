dn = 'hey'
domains = {'hey': [5]}
ports = 10


#if dn in domains:
#    domains[dn] += ports
#else:
#    domains[dn] = ports

domains.setdefault(dn, []).append(ports)

print domains

