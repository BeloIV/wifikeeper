"""
Priama práca s OpenLDAP cez ldap3.
Tento modul nerieši autentifikáciu adminov (to robí django-auth-ldap),
ale CRUD operácie nad WiFi používateľmi (ou=users).
"""
import base64
import binascii
import hashlib
import os
import secrets
import string
from ldap3 import Server, Connection, ALL, NONE, MODIFY_REPLACE, MODIFY_DELETE, MODIFY_ADD
from ldap3.core.exceptions import LDAPException
from ldap3.utils.conv import escape_filter_chars
from django.conf import settings


_FALLBACK_GROUPS = ['animatori', 'spolupracovnici', 'hostia', 'premietaci', 'bar', 'kaviaren', 'zbor', 'treneri', 'mediatim']
_FALLBACK_VLAN = {'animatori': 20, 'spolupracovnici': 30, 'hostia': 40, 'premietaci': 20, 'bar': 20, 'kaviaren': 20, 'zbor': 20, 'treneri': 20, 'mediatim': 20}
_FALLBACK_LABELS = {
    'animatori': 'Animátori', 'spolupracovnici': 'Spolupracovníci', 'hostia': 'Hostia',
    'premietaci': 'Premietanie', 'bar': 'Bar', 'kaviaren': 'Kaviareň',
    'zbor': 'Zbor', 'treneri': 'Tréneri', 'mediatim': 'Mediálny tím',
}


def get_groups() -> list[str]:
    try:
        from apps.users.models import LDAPGroup
        return list(LDAPGroup.objects.values_list('name', flat=True))
    except Exception:
        return _FALLBACK_GROUPS


def get_vlan_map() -> dict[str, int]:
    try:
        from apps.users.models import LDAPGroup
        return {g.name: g.vlan for g in LDAPGroup.objects.all()}
    except Exception:
        return _FALLBACK_VLAN


def get_group_labels() -> dict[str, str]:
    try:
        from apps.users.models import LDAPGroup
        return {g.name: g.label for g in LDAPGroup.objects.all()}
    except Exception:
        return _FALLBACK_LABELS


def _conn():
    server = Server(settings.LDAP_SERVER_URI, get_info=NONE)
    conn = Connection(
        server,
        user=settings.LDAP_BIND_DN,
        password=settings.LDAP_BIND_PASSWORD,
        auto_bind=True,
    )
    return conn


def _user_dn(username: str) -> str:
    return f'uid={username},ou=users,{settings.LDAP_BASE_DN}'


def _group_dn(group: str) -> str:
    return f'cn={group},ou=groups,{settings.LDAP_BASE_DN}'


def _nt_hash(password: str) -> str:
    """Vypočíta NT hash hesla pre MSCHAPv2 autentifikáciu."""
    from Crypto.Hash import MD4
    h = MD4.new()
    h.update(password.encode('utf-16-le'))
    return binascii.hexlify(h.digest()).decode().upper()


def _ssha_hash(password: str) -> str:
    """Vypočíta {SSHA} hash pre atribút userPassword v LDAP."""
    salt = os.urandom(16)
    digest = hashlib.sha1(password.encode('utf-8') + salt).digest()
    return '{SSHA}' + base64.b64encode(digest + salt).decode()


def list_users() -> list[dict]:
    conn = _conn()
    conn.search(
        f'ou=users,{settings.LDAP_BASE_DN}',
        '(objectClass=inetOrgPerson)',
        attributes=['uid', 'cn', 'givenName', 'sn', 'mail', 'pwdAccountLockedTime'],
    )
    users = []
    for entry in conn.entries:
        uid = str(entry.uid) if entry.uid else ''
        if uid == 'dummy':
            continue
        users.append({
            'username': uid,
            'full_name': str(entry.cn) if entry.cn else '',
            'first_name': str(entry.givenName) if entry.givenName else '',
            'last_name': str(entry.sn) if entry.sn else '',
            'email': str(entry.mail) if entry.mail else '',
            'disabled': bool(entry.pwdAccountLockedTime),
            'group': get_user_group(uid),
        })
    conn.unbind()
    return users


def get_user(username: str) -> dict | None:
    conn = _conn()
    conn.search(
        f'ou=users,{settings.LDAP_BASE_DN}',
        f'(uid={escape_filter_chars(username)})',
        attributes=['uid', 'cn', 'givenName', 'sn', 'mail', 'pwdAccountLockedTime'],
    )
    if not conn.entries:
        conn.unbind()
        return None
    entry = conn.entries[0]
    conn.unbind()
    return {
        'username': str(entry.uid),
        'full_name': str(entry.cn) if entry.cn else '',
        'first_name': str(entry.givenName) if entry.givenName else '',
        'last_name': str(entry.sn) if entry.sn else '',
        'email': str(entry.mail) if entry.mail else '',
        'disabled': bool(entry.pwdAccountLockedTime),
        'group': get_user_group(username),
    }


def create_user(username: str, password: str, first_name: str, last_name: str,
                email: str, group: str) -> dict:
    conn = _conn()
    dn = _user_dn(username)
    nt = _nt_hash(password)
    attrs = {
        'objectClass': ['inetOrgPerson', 'sambaSamAccount'],
        'uid': username,
        'cn': f'{first_name} {last_name}'.strip() or username,
        'givenName': first_name,
        'sn': last_name or username,
        'mail': email,
        'userPassword': _ssha_hash(password),
        'sambaNTPassword': nt,
        'sambaSID': f'S-1-5-21-{secrets.randbelow(2**32)}-500',
    }
    conn.add(dn, attributes=attrs)
    if conn.result['result'] != 0:
        raise LDAPException(f'Chyba pri vytváraní používateľa: {conn.result["description"]}')

    # Zaradenie do skupiny
    set_user_group(username, group, conn=conn)
    conn.unbind()
    return get_user(username)


def update_user(username: str, first_name: str = None, last_name: str = None,
                email: str = None, group: str = None) -> dict:
    conn = _conn()
    dn = _user_dn(username)
    changes = {}
    if first_name is not None:
        changes['givenName'] = [(MODIFY_REPLACE, [first_name])]
    if last_name is not None:
        changes['sn'] = [(MODIFY_REPLACE, [last_name])]
        # Aktualizuj cn
        first = first_name or ''
        changes['cn'] = [(MODIFY_REPLACE, [f'{first} {last_name}'.strip() or username])]
    if email is not None:
        changes['mail'] = [(MODIFY_REPLACE, [email])]
    if changes:
        conn.modify(dn, changes)
    conn.unbind()

    if group is not None:
        set_user_group(username, group)

    return get_user(username)


def set_password(username: str, password: str):
    conn = _conn()
    dn = _user_dn(username)
    nt = _nt_hash(password)
    conn.modify(dn, {
        'userPassword': [(MODIFY_REPLACE, [_ssha_hash(password)])],
        'sambaNTPassword': [(MODIFY_REPLACE, [nt])],
    })
    if conn.result['result'] != 0:
        raise LDAPException(f'Chyba pri zmene hesla: {conn.result["description"]}')
    conn.unbind()


def delete_user(username: str):
    conn = _conn()
    current_group = get_user_group(username)
    if current_group:
        _remove_from_group(username, current_group, conn=conn)
    conn.delete(_user_dn(username))
    conn.unbind()
    from django.db import connection as db
    with db.cursor() as cur:
        cur.execute("DELETE FROM radreply WHERE username = %s", [username])


def set_active(username: str, active: bool):
    """Aktivuje alebo deaktivuje účet (pwdAccountLockedTime + radreply)."""
    conn = _conn()
    dn = _user_dn(username)
    if active:
        conn.modify(dn, {'pwdAccountLockedTime': [(MODIFY_DELETE, [])]})
        conn.unbind()
        # Obnov VLAN — zisti skupinu a zapíš radreply
        group = get_user_group(username)
        if group:
            vlan_map = get_vlan_map()
            vlan = vlan_map.get(group)
            if vlan is not None:
                _set_radreply_vlan(username, vlan)
    else:
        conn.modify(dn, {'pwdAccountLockedTime': [(MODIFY_REPLACE, ['000001010000Z'])]})
        conn.unbind()
        # Zablokuj RADIUS prístup — vymaž radreply
        from django.db import connection as db
        with db.cursor() as cur:
            cur.execute("DELETE FROM radreply WHERE username = %s", [username])


def get_user_group(username: str) -> str | None:
    conn = _conn()
    user_dn = _user_dn(username)
    for group in get_groups():
        conn.search(
            f'ou=groups,{settings.LDAP_BASE_DN}',
            f'(&(cn={escape_filter_chars(group)})(member={escape_filter_chars(user_dn)}))',
            attributes=['cn'],
        )
        if conn.entries:
            conn.unbind()
            return group
    conn.unbind()
    return None


def set_user_group(username: str, group: str, conn=None):
    """Presunie používateľa do danej skupiny a aktualizuje VLAN v radreply."""
    close = conn is None
    if conn is None:
        conn = _conn()

    user_dn = _user_dn(username)

    # Odober zo všetkých skupín
    for g in get_groups():
        gdn = _group_dn(g)
        conn.search(
            f'ou=groups,{settings.LDAP_BASE_DN}',
            f'(&(cn={escape_filter_chars(g)})(member={escape_filter_chars(user_dn)}))',
            attributes=['cn'],
        )
        if conn.entries:
            conn.modify(gdn, {'member': [(MODIFY_DELETE, [user_dn])]})

    # Pridaj do novej skupiny
    conn.modify(_group_dn(group), {'member': [(MODIFY_ADD, [user_dn])]})

    if close:
        conn.unbind()

    # Aktualizuj VLAN atribúty v radreply (FreeRADIUS ich číta pri každom authorize)
    vlan_map = get_vlan_map()
    vlan = vlan_map.get(group)
    if vlan is None:
        raise LDAPException(f"Skupina '{group}' nemá VLAN priradenie v databáze.")
    _set_radreply_vlan(username, vlan)


def _set_radreply_vlan(username: str, vlan: int):
    """Zapíše/aktualizuje VLAN Tunnel atribúty pre používateľa v radreply tabuľke."""
    from django.db import connection as db
    with db.cursor() as cur:
        cur.execute("DELETE FROM radreply WHERE username = %s", [username])
        cur.executemany(
            "INSERT INTO radreply (username, attribute, op, value) VALUES (%s, %s, ':=', %s)",
            [
                (username, 'Tunnel-Type', 'VLAN'),
                (username, 'Tunnel-Medium-Type', 'IEEE-802'),
                (username, 'Tunnel-Private-Group-Id', str(vlan)),
            ],
        )


def _remove_from_group(username: str, group: str, conn=None):
    close = conn is None
    if conn is None:
        conn = _conn()
    user_dn = _user_dn(username)
    conn.modify(_group_dn(group), {'member': [(MODIFY_DELETE, [user_dn])]})
    if close:
        conn.unbind()


def get_next_group_id(group: str) -> int:
    """
    Vráti ďalšie voľné poradové číslo pre skupinu.
    Prechádza sn (priezvisko) všetkých členov skupiny, hľadá max číslo.
    """
    users = list_users()
    max_id = 0
    for u in users:
        if u.get('group') == group:
            sn = u.get('last_name', '')
            if sn.isdigit():
                max_id = max(max_id, int(sn))
    return max_id + 1


def generate_temp_username(prefix: str = 'guest') -> str:
    """Vygeneruje unikátne meno pre dočasného používateľa."""
    suffix = ''.join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(6))
    return f'{prefix}_{suffix}'


# ── Správa skupín ─────────────────────────────────────────────────────────────

def create_ldap_group(name: str):
    """Vytvorí groupOfNames záznam v LDAP."""
    conn = _conn()
    dn = _group_dn(name)
    # groupOfNames vyžaduje aspoň jedného člena – použijeme dummy dn
    dummy_dn = f'uid=dummy,ou=users,{settings.LDAP_BASE_DN}'
    conn.add(dn, object_class=['groupOfNames'], attributes={'cn': name, 'member': [dummy_dn]})
    if conn.result['result'] != 0:
        raise LDAPException(f'Chyba pri vytváraní skupiny: {conn.result["description"]}')
    conn.unbind()


def delete_ldap_group(name: str):
    """Vymaže groupOfNames záznam z LDAP."""
    conn = _conn()
    dn = _group_dn(name)
    conn.delete(dn)
    if conn.result['result'] != 0:
        raise LDAPException(f'Chyba pri mazaní skupiny: {conn.result["description"]}')
    conn.unbind()


