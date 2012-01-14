from __future__ import with_statement

import os

from gears.asset_attributes import AssetAttributes
from gears.assets import Asset
from gears.environment import Environment
from gears.exceptions import FileNotFound
from gears.processors import DirectivesProcessor

from mock import Mock, patch, sentinel
from unittest2 import TestCase


ASSETS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), 'assets'))


class DirectiveProcessorTests(TestCase):

    def setUp(self):
        self.environment = Environment('assets')

    def create_processor(self, path, source='', context=None, calls=None):
        if context is None:
            context = {}
        if calls is None:
            calls = set()
        asset_attributes = AssetAttributes(self.environment, path)
        return DirectivesProcessor(asset_attributes, source, context, calls)

    @patch('gears.assets.Asset.__init__')
    def test_get_asset(self, init):
        init.return_value = None
        processor = self.create_processor(
            'js/script.js', '', sentinel.context, sentinel.calls)
        asset = processor.get_asset(sentinel.attributes, sentinel.absolute_path)
        init.assert_called_once_with(
            sentinel.attributes, sentinel.absolute_path, sentinel.context,
            sentinel.calls)

    def test_relative_path(self):
        processor = self.create_processor('js/script.js.coffee')
        relative_path = processor.get_relative_path
        self.assertEqual(relative_path('app'), 'js/app.js.coffee')
        self.assertEqual(relative_path('news/app'), 'js/news/app.js.coffee')
        self.assertEqual(relative_path('../admin/app'), 'admin/app.js.coffee')

    def test_find(self):
        with patch.object(self.environment, 'find'):
            self.create_processor('js/script.js.coffee').find('app')
            self.assertEqual(self.environment.find.call_count, 1)

            asset_attributes, logical = self.environment.find.call_args[0]
            self.assertTrue(logical)
            self.assertEqual(asset_attributes.path, 'js/app.js.coffee')
            self.assertIs(asset_attributes.environment, self.environment)

    def test_parse_multiline_comment(self):
        processor = self.create_processor('js/script.js')
        directives = processor.parse_directives('\n'.join((
            '/*',
            ' * =require_self',
            ' *= require header',
            ' * =require body',
            ' * =require "footer"',
            ' */')))
        self.assertEqual(list(directives), [
            ['require_self'],
            ['require', 'header'],
            ['require', 'body'],
            ['require', 'footer']])

    def test_parse_slash_commend(self):
        processor = self.create_processor('js/script.js')
        directives = processor.parse_directives('\n'.join((
            '//= require "file with whitespaces"',
            '// =require another_file')))
        self.assertEqual(list(directives), [
            ['require', 'file with whitespaces'],
            ['require', 'another_file']])

    def test_parse_dash_comment(self):
        processor = self.create_processor('js/script.js.coffee')
        directives = processor.parse_directives('\n'.join((
            '#= require models',
            '# =require views')))
        self.assertEqual(list(directives), [
            ['require', 'models'],
            ['require', 'views']])

    def test_process_require_directive(self):
        processor = self.create_processor('js/script.js')
        processor.find = Mock(
            return_value=(sentinel.asset_attributes, sentinel.absolute_path))
        processor.get_asset = Mock()

        body = []
        processor.process_require_directive('app', body)
        processor.find.assert_called_once_with('app')
        processor.get_asset.assert_called_once_with(
            sentinel.asset_attributes, sentinel.absolute_path)
        self.assertEqual(body, [processor.get_asset.return_value])

    def test_process_require_directory_directive(self):

        def item(path):
            return AssetAttributes(self.environment, path), os.path.join(ASSETS_DIR, path)

        def list(path, suffix):
            return (item('js/templates/%s.js.handlebars' % name) for name in 'bca')

        def get_asset(asset_attributes, *args):
            return asset_attributes.path

        processor = self.create_processor('js/script.js')
        processor.get_asset = Mock(side_effect=get_asset)
        self.environment.list = Mock(side_effect=list)

        body = []
        processor.process_require_directory_directive('templates', body)
        self.environment.list.assert_called_once_with('js/templates', ['.js'])
        self.assertEqual(body, ['js/templates/a.js.handlebars',
                                'js/templates/b.js.handlebars',
                                'js/templates/c.js.handlebars'])
