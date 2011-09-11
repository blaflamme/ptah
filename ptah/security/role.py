from memphis import config
from collections import OrderedDict
from pyramid.location import lineage
from pyramid.security import Allow, Deny, ALL_PERMISSIONS

from interfaces import ILocalRolesAware


class Roles(dict):
    pass

Roles = Roles()


class Role(object):

    def __init__(self, name, title, description=''):
        self.id = 'role:%s'%name
        self.name = name
        self.title = title
        self.description = description

        self.allowed = set()
        self.denied = set()

    def __str__(self):
        return 'Role<%s>'%self.name

    def allow(self, *permissions):
        if self.allowed is ALL_PERMISSIONS:
            return

        if ALL_PERMISSIONS in permissions:
            self.allowed = ALL_PERMISSIONS
            return
        
        for perm in permissions:
            self.allowed.add(perm)

    def deny(self, *permissions):
        for perm in permissions:
            self.denied.add(perm)

    def unset(self, *permissions):
        for perm in permissions:
            if perm in self.allowed:
                self.allowed.remove(perm)
            if perm in self.denied:
                self.denied.remove(perm)


def registerRole(name, title, description=u''):
    info = config.DirectiveInfo()

    role = Role(name, title, description)

    info.attach(
        config.Action(
            registerRoleImpl,
            (role,), discriminator = ('ptah:role', name))
        )

    return role


def registerRoleImpl(role):
    Roles[role.name] = role


def LocalRoles(userid, request):
    context = getattr(request, 'context', None)
    if context is None:
        context = getattr(request, 'root', None)

    roles = OrderedDict()
    for location in lineage(context):
        if ILocalRolesAware.providedBy(location):
            local_roles = location.__local_roles__
            if local_roles:
                for r in local_roles.get(userid, ()):
                    if r not in roles:
                        roles[r] = Allow

    data = [userid]
    for r, val in roles.items():
        if val is Allow:
            data.append(r)

    return data


ACL = []

@config.handler(config.SettingsInitialized)
def initialized(ev):
    global ACL

    for role in Roles.values():
        if role.denied:
            ACL.append((Deny, role.id, role.denied))
        if role.allowed:
            ACL.append((Allow, role.id, role.allowed))


@config.addCleanup
def cleanup():
    ACL[:] = []
