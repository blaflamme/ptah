""" type implementation """
import ptah
import sys, colander
import sqlalchemy as sqla
from memphis import config
from zope import interface
from pyramid.httpexceptions import HTTPForbidden
from pyramid.threadlocal import get_current_request

from content import Session, Content
from container import Container
from events import ContentCreatedEvent
from interfaces import ContentSchema, IAction, ITypeInformation
from permissions import View, AddContent, ModifyContent


registeredTypes = {}

class Action(object):
    interface.implements(IAction)

    id = ''
    title = ''
    description = ''
    action = ''
    permission = None

    def __init__(self, id='', **kw):
        self.id = id
        self.__dict__.update(kw)


class TypeInformation(object):
    interface.implements(ITypeInformation)

    add = None # add action, path relative to current container
    description = u''
    permission = AddContent

    filter_content_types = False
    allowed_content_types = ()
    global_allow = True

    def __init__(self, klass, name, title, 
                 schema=ContentSchema, constructor=None, **kw):
        self.__dict__.update(kw)

        self.name = name
        self.title = title
        self.klass = klass
        self.schema = schema

        if constructor is None:
            constructor = self._constructor
        self.constructor = constructor

    def _constructor(self, **data):
        attrs = {}

        if self.schema is not None:
            for node in self.schema:
                val = data.get(node.name, node.default)
                if val is not colander.null:
                    attrs[node.name] = val

        return self.klass(**attrs)

    def create(self, **data):
        content = self.constructor(**data)

        request = get_current_request()
        if request is not None:
            request.registry.notify(ContentCreatedEvent(content))

        return content

    def isAllowed(self, container):
        if not isinstance(container, Container):
            return False

        if self.permission:
            return ptah.checkPermission(
                container, self.permission, throw=False)
        return True

    def checkContext(self, container):
        if not self.isAllowed(container):
            raise HTTPForbidden()

    def listTypes(self, container):
        if container.__type__ is not self or \
               not isinstance(container, Container):
            return ()

        types = []
        if self.filter_content_types:
            for tname in self.allowed_content_types:
                tinfo = registeredTypes.get(tname)
                if tinfo and tinfo.isAllowed(container):
                    types.append(tinfo)

        else:
            for tinfo in registeredTypes.values():
                if tinfo.global_allow and tinfo.isAllowed(container):
                    types.append(tinfo)

        return types


# we have to generate seperate sql query for each type
_sql_get = ptah.QueryFreezer(
    lambda: Session.query(Content)
    .filter(Content.__uuid__ == sqla.sql.bindparam('uuid')))

def resolveContent(uuid):
    return _sql_get.first(uuid=uuid)


def Type(name, title, **kw):
    info = config.DirectiveInfo(allowed_scope=('class',))

    typeinfo = TypeInformation(None, name, title)

    f_locals = sys._getframe(1).f_locals
    if '__mapper_args__' not in f_locals:
        f_locals['__mapper_args__'] = {'polymorphic_identity': name}
    if '__id__' not in f_locals and '__tablename__' in f_locals:
        f_locals['__id__'] = sqla.Column( #pragma: no cover
            'id', sqla.Integer, 
            sqla.ForeignKey('ptah_cms_content.id'), primary_key=True)
    if '__uuid_generator__' not in f_locals:
        f_locals['__uuid_generator__'] = ptah.UUIDGenerator('cms+%s'%name)

        ptah.registerResolver(
            'cms+%s'%name, resolveContent, 
            title = 'Ptah CMS Content resolver for %s type'%title,
            depth = 2)

    info.attach(
        config.ClassAction(
            registerType,
            (typeinfo, name, title), kw,
            discriminator = ('ptah-cms:type', name))
        )

    return typeinfo


def registerType(
    klass, tinfo, name,
    title = '', description = '', schema = ContentSchema,
    global_allow = True, permission = '__denied__',
    actions = None, **kw):

    if actions is None:
        actions = (
            Action(**{'id': 'view',
                      'title': 'View',
                      'action': '',
                      'permission': View}),
            Action(**{'id': 'edit',
                      'title': 'Edit',
                      'action': 'edit.html',
                      'permission': ModifyContent}),
            )

    tinfo.__dict__.update(kw)

    if isinstance(schema, colander._SchemaMeta):
        schema = schema()

    tinfo.schema = schema
    tinfo.factory = klass
    tinfo.description = description
    tinfo.global_allow = global_allow
    tinfo.permission = permission
    tinfo.actions = actions

    registeredTypes[name] = tinfo


@config.addCleanup
def cleanUp():
    registeredTypes.clear()
