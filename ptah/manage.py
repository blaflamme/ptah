from memphis import view
from zope import interface
from webob.exc import HTTPForbidden

from ptah.settings import PTAH
from ptah.interfaces import IAuthentication, IPtahManageRoute, IPtahModule


class PtahModule(object):
    interface.implements(IPtahModule)

    name = ''
    title = ''
    description = ''

    def url(self, request):
        return '%s/'%self.name

    def bind(self, manager, request):
        clone = self.__class__.__new__(self.__class__)
        clone.__dict__.update(self.__dict__)
        clone.__name__ = self.name
        clone.__parent__ = manager
        clone.request = request
        return clone

    def available(self, request):
        return True


class PtahManageRoute(object):
    interface.implements(IPtahManageRoute)

    __name__ = 'ptah-manage'
    __parent__ = view.DefaultRoot()

    def __init__(self, request):
        self.request = request
        self.registry = request.registry

        login = self.registry.getUtility(IAuthentication).getCurrentLogin()
        if login and login in PTAH.managers:
            pass

        #raise HTTPForbidden()

    def __getitem__(self, key):
        mod = self.registry.queryUtility(IPtahModule, key)

        if mod is not None:
            return mod.bind(self, self.request)

        raise KeyError(key)


view.registerRoute(
    'ptah-manage', '/ptah-manage/*traverse', PtahManageRoute)

view.static('ptah', 'ptah:templates/static')

view.registerLayout(
    '', IPtahManageRoute, parent='page',
    template=view.template("ptah:templates/ptah-layout.pt"))

view.registerPagelet(
    'ptah-module-actions',
    template = view.template('ptah:templates/moduleactions.pt'))


class LayoutPage(view.Layout):
    view.layout('page', IPtahManageRoute,
                template=view.template("ptah:templates/ptah-page.pt"))

    def update(self):
        request = self.request
        registry = request.registry

        self.user = registry.getUtility(IAuthentication).getCurrentUser()

        mod = self.maincontext
        while not IPtahModule.providedBy(mod):
            mod = getattr(mod, '__parent__', None)
            if mod is None:
                break

        self.module = mod


class ManageView(view.View):
    view.pyramidView('index.html', IPtahManageRoute,
                     route = 'ptah-manage', default = True, layout='page',
                     template = view.template('ptah:templates/manage.pt'))

    def update(self):
        reg = self.request.registry

        mods = []
        for name, mod in reg.getUtilitiesFor(IPtahModule):
            mods.append((mod.title, mod))

        mods.sort()
        self.modules = [mod for _t, mod in mods]