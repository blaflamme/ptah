from zope import interface
from pyramid import security
from pyramid.threadlocal import get_current_request

from interfaces import IAuthentication, ISearchableAuthProvider

providers = {}


def registerProvider(name, provider):
    providers[name] = provider


class Principal(object):

    def __init__(self, id, name, login):
        self.id = id
        self.name = name
        self.login = login

    def __str__(self):
        return self.name


class Authentication(object):
    interface.implements(IAuthentication)

    def authenticate(self, credentials):
        for pname, provider in providers.items():
            info = provider.authenticate(credentials)
            if info is not None:
                id, name, login = info
                return Principal('user://%s:%s'%(pname, id), name, login)

    def getPrincipal(self, uuid):
        if not uuid or not uuid.startswith('user://'):
            return
        
        uri = uuid.split('user://', 1)[1]
        pid, id = uri.split(':', 1)

        provider = providers.get(pid)
        if provider is not None:
            info = provider.getPrincipalInfo(id)
            if info is not None:
                name, login = info
                return Principal(uuid, name, login)

    def isAnonymous(self):
        id = security.authenticated_userid(get_current_request())
        if id:
            return False
        return True
        
    def getCurrentPrincipal(self):
        id = security.authenticated_userid(get_current_request())
        if id:
            return self.getPrincipal(id)

    def search(self, term):
        for pname, provider in providers.items():
            if ISearchableAuthProvider.providedBy(provider):
                for id, name, login in provider.search(term):
                    yield Principal('user://%s:%s'%(pname, id), name, login)


authService = Authentication()
