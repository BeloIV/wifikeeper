from apps.users import ldap_service as ldap

users = ldap.list_users()
vlan_map = ldap.get_vlan_map()
print(f"Skupiny v DB: {vlan_map}")
print(f"Používateľov: {len(users)}")

for user in users:
    g = user.get('group')
    if not g:
        print(f"SKIP {user['username']} — bez skupiny")
        continue
    vlan = vlan_map.get(g)
    if vlan is None:
        print(f"WARN {user['username']} — skupina '{g}' nie je v DB")
        continue
    ldap._set_radreply_vlan(user['username'], vlan)
    print(f"OK   {user['username']} → VLAN {vlan} ({g})")
