""" snippet tests """
import sys, unittest
from zope import interface
from pyramid.httpexceptions import HTTPNotFound
from memphis import config, view
from memphis.config import api
from memphis.view.snippet import ISnippet, Snippet, SnippetType, render_snippet

from base import Base


class TestSnippet(Base):

    def _setup_memphis(self):
        pass

    def test_snippettype_register(self):
        class ITestsnippet(interface.Interface):
            pass

        view.snippettype('test', Context)
        self._init_memphis()

        from memphis.view.snippet import stypes

        self.assertTrue('test' in stypes)

        st = stypes['test']
        self.assertTrue(isinstance(st, SnippetType))
        self.assertEqual(st.name, 'test')
        self.assertEqual(st.context, Context)

    def test_snippet_register_errors(self):
        class TestSnippet(view.Snippet):
            pass

        view.snippettype('test1', Context)
        view.snippettype('test2', Context)

        view.register_snippet('test1', Context, TestSnippet)
        view.register_snippet('test2', Context, TestSnippet)

        self.assertRaises(ValueError, self._init_memphis)

    def test_snippet_register_nopt(self):
        class ITestSnippet(interface.Interface):
            pass

        class TestSnippet(view.Snippet):
            pass

        view.register_snippet(ITestSnippet, Context, TestSnippet)

        self.assertRaises(LookupError, self._init_memphis)

    def test_snippet_register(self):
        class TestSnippet(view.Snippet):
            def render(self):
                return 'test snippet'

        view.snippettype('test', Context)
        view.register_snippet('test', Context, TestSnippet)
        self._init_memphis()

        self.assertEqual(
            render_snippet('test', Context(), self.request), 'test snippet')

    def test_snippet_register_declarative(self):
        global TestSnippet

        view.snippettype('pt', Context)

        class TestSnippet(view.Snippet):
            view.snippet('pt')

            def render(self):
                return 'test'

        self._init_memphis()

        self.assertEqual(render_snippet('pt', Context(), self.request), 'test')

    def test_snippet_register_with_template(self):
        class TestSnippet(view.Snippet):
            pass

        def template(*args, **kw):
            keys = kw.keys()
            keys.sort()
            return '|'.join(keys)

        view.snippettype('test', Context)
        view.register_snippet('test', klass=TestSnippet, template = template)
        self._init_memphis()

        self.assertEqual(
            render_snippet('test', Context(), self.request),
            'context|format|request|view')

    def test_snippet_register_without_class(self):
        view.snippettype('test', Context)
        view.register_snippet('test', Context)
        self._init_memphis()

        snippet = config.registry.getMultiAdapter(
            (Context(), self.request), ISnippet, 'test')

        self.assertTrue(isinstance(snippet, Snippet))
        self.assertEqual(str(snippet.__class__),
                         "<class 'memphis.view.snippet.Snippet None'>")

    def test_snippet_register_with_not_Snippet_class(self):
        class TestSnippet(object):
            pass

        view.snippettype('test', Context)
        view.register_snippet('test', Context, TestSnippet)
        self._init_memphis()

        snippet = config.registry.getMultiAdapter(
            (Context(), self.request), ISnippet, 'test')

        self.assertTrue(isinstance(snippet, Snippet))
        self.assertTrue(isinstance(snippet, TestSnippet))

    def test_snippet_rendersnippet_not_found(self):
        self._init_memphis()

        self.assertRaises(
            HTTPNotFound,
            render_snippet, 'test', Context(), self.request)

    def test_snippet_render_with_exception(self):
        class TestSnippet(view.Snippet):
            def render(self):
                raise ValueError('Unknown')

        view.snippettype('test', Context)
        view.register_snippet('test', Context, TestSnippet)
        self._init_memphis()

        self.assertRaises(
            ValueError,
            render_snippet, 'test', Context(), self.request)

    def test_snippet_render_additional_params_to_template(self):
        class TestSnippet(view.Snippet):
            def update(self):
                return {'param1': 1, 'param2': 2}

        def template(*args, **kw):
            keys = kw.keys()
            keys.sort()
            return '|'.join(keys)

        view.snippettype('test', Context)
        view.register_snippet('test', klass=TestSnippet, template = template)
        self._init_memphis()

        self.assertTrue(
            'param1|param2|' in render_snippet('test', Context(), self.request))

    def test_snippet_View_snippet(self):
        class TestSnippet(view.Snippet):
            def render(self):
                return 'test snippet'

        view.snippettype('test', Context)
        view.register_snippet('test', Context, TestSnippet)
        self._init_memphis()

        base = view.View(None, self.request)

        # snippettype is string
        self.assertEqual(base.snippet('unknown', Context()), '')
        self.assertEqual(base.snippet('test', Context()), 'test snippet')

        # by default use view context
        base.context = Context()
        self.assertEqual(base.snippet('test'), 'test snippet')


    def test_snippet_View_snippet_with_error(self):
        class TestSnippet(view.Snippet):
            def render(self):
                raise ValueError('Error')

        view.snippettype('test', Context)
        view.register_snippet('test', Context, TestSnippet)
        self._init_memphis()

        base = view.View(None, self.request)
        self.assertEqual(base.snippet('test', Context()), '')


class Context(object):
    pass
