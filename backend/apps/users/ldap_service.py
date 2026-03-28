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


GROUPS = ['sdb', 'animatori', 'fma', 'spolupracovnici', 'hostia', 'docasny']


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
    # Najprv odober zo skupiny
    current_group = get_user_group(username)
    if current_group:
        _remove_from_group(username, current_group, conn=conn)
    conn.delete(_user_dn(username))
    conn.unbind()


def set_active(username: str, active: bool):
    """Aktivuje alebo deaktivuje účet (pwdAccountLockedTime)."""
    conn = _conn()
    dn = _user_dn(username)
    if active:
        conn.modify(dn, {'pwdAccountLockedTime': [(MODIFY_DELETE, [])]})
    else:
        conn.modify(dn, {'pwdAccountLockedTime': [(MODIFY_REPLACE, ['000001010000Z'])]})
    conn.unbind()


def get_user_group(username: str) -> str | None:
    conn = _conn()
    user_dn = _user_dn(username)
    for group in GROUPS:
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
    """Presunie používateľa do danej skupiny (odstráni zo všetkých ostatných)."""
    close = conn is None
    if conn is None:
        conn = _conn()

    user_dn = _user_dn(username)

    # Odober zo všetkých skupín
    for g in GROUPS:
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


def _remove_from_group(username: str, group: str, conn=None):
    close = conn is None
    if conn is None:
        conn = _conn()
    user_dn = _user_dn(username)
    conn.modify(_group_dn(group), {'member': [(MODIFY_DELETE, [user_dn])]})
    if close:
        conn.unbind()


def generate_temp_username(prefix: str = 'guest') -> str:
    """Vygeneruje unikátne meno pre dočasného používateľa."""
    suffix = ''.join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(6))
    return f'{prefix}_{suffix}'
