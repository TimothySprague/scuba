 # coding=utf-8
from __future__ import print_function

from .utils import *
from unittest import TestCase

import logging
import os
from os.path import join
from shutil import rmtree
import shlex

import scuba.config


class TestCommonScriptSchema(TmpDirTestCase):
    def test_simple(self):
        '''Simple form: value is a string'''
        node = 'foo'
        result = scuba.config._process_script_node(node, 'dontcare')
        assert_seq_equal(result, ['foo'])

    def test_script_key_string(self):
        '''Value is a mapping: script is a string'''
        node = dict(
            script = 'foo',
            otherkey = 'other',
        )
        result = scuba.config._process_script_node(node, 'dontcare')
        assert_seq_equal(result, ['foo'])

    def test_script_key_list(self):
        '''Value is a mapping: script is a list'''
        node = dict(
            script = [
                'foo',
                'bar',
            ],
            otherkey = 'other',
        )
        result = scuba.config._process_script_node(node, 'dontcare')
        assert_seq_equal(result, ['foo', 'bar'])

    def test_script_key_mapping_invalid(self):
        '''Value is a mapping: script is a mapping (invalid)'''
        node = dict(
            script = dict(
                whatisthis = 'idontknow',
            ),
        )

        with self.assertRaises(scuba.config.ConfigError):
            scuba.config._process_script_node(node, 'dontcare')


class TestConfig(TmpDirTestCase):

    ######################################################################
    # Find config

    def test_find_config_cur_dir(self):
        '''find_config can find the config in the current directory'''
        with open('.scuba.yml', 'w') as f:
            f.write('image: busybox\n')

        path, rel = scuba.config.find_config()
        assert_paths_equal(path, self.path)
        assert_paths_equal(rel, '')


    def test_find_config_parent_dir(self):
        '''find_config cuba can find the config in the parent directory'''
        with open('.scuba.yml', 'w') as f:
            f.write('image: busybox\n')

        os.mkdir('subdir')
        os.chdir('subdir')

        # Verify our current working dir
        assert_paths_equal(os.getcwd(), join(self.path, 'subdir'))

        path, rel = scuba.config.find_config()
        assert_paths_equal(path, self.path)
        assert_paths_equal(rel, 'subdir')

    def test_find_config_way_up(self):
        '''find_config can find the config way up the directory hierarchy'''
        with open('.scuba.yml', 'w') as f:
            f.write('image: busybox\n')

        subdirs = ['foo', 'bar', 'snap', 'crackle', 'pop']

        for sd in subdirs:
            os.mkdir(sd)
            os.chdir(sd)

        # Verify our current working dir
        assert_paths_equal(os.getcwd(), join(self.path, *subdirs))

        path, rel = scuba.config.find_config()
        assert_paths_equal(path, self.path)
        assert_paths_equal(rel, join(*subdirs))

    def test_find_config_nonexist(self):
        '''find_config raises ConfigError if the config cannot be found'''
        with self.assertRaises(scuba.config.ConfigError):
            scuba.config.find_config()

    ######################################################################
    # Load config

    def test_load_config_empty(self):
        '''load_config raises ConfigError if the config is empty'''
        with open('.scuba.yml', 'w') as f:
            pass

        with self.assertRaises(scuba.config.ConfigError):
            scuba.config.load_config('.scuba.yml')

    def test_load_unexpected_node(self):
        '''load_config raises ConfigError on unexpected config node'''
        with open('.scuba.yml', 'w') as f:
            f.write('image: busybox\n')
            f.write('unexpected_node_123456: value\n')

        with self.assertRaises(scuba.config.ConfigError):
            scuba.config.load_config('.scuba.yml')

    def test_load_config_minimal(self):
        '''load_config loads a minimal config'''
        with open('.scuba.yml', 'w') as f:
            f.write('image: busybox\n')

        config = scuba.config.load_config('.scuba.yml')
        self.assertEqual(config.image, 'busybox')

    def test_load_config_with_aliases(self):
        '''load_config loads a config with aliases'''
        with open('.scuba.yml', 'w') as f:
            f.write('image: busybox\n')
            f.write('aliases:\n')
            f.write('  foo: bar\n')
            f.write('  snap: crackle pop\n')

        config = scuba.config.load_config('.scuba.yml')
        self.assertEqual(config.image, 'busybox')
        self.assertEqual(len(config.aliases), 2)
        assert_seq_equal(config.aliases['foo'].script, ['bar'])
        assert_seq_equal(config.aliases['snap'].script, ['crackle pop'])

    def test_load_config__no_spaces_in_aliases(self):
        '''load_config refuses spaces in aliases'''
        with open('.scuba.yml', 'w') as f:
            f.write('image: busybox\n')
            f.write('aliases:\n')
            f.write('  this has spaces: whatever\n')

        with self.assertRaises(scuba.config.ConfigError):
            scuba.config.load_config('.scuba.yml')

    def test_load_config_image_from_yaml(self):
        '''load_config loads a config using !from_yaml'''
        with open('.gitlab.yml', 'w') as f:
            f.write('image: debian:8.2\n')

        with open('.scuba.yml', 'w') as f:
            f.write('image: !from_yaml .gitlab.yml image\n')

        config = scuba.config.load_config('.scuba.yml')
        self.assertEqual(config.image, 'debian:8.2')

    def test_load_config_image_from_yaml_nested_keys(self):
        '''load_config loads a config using !from_yaml with nested keys'''
        with open('.gitlab.yml', 'w') as f:
            f.write('somewhere:\n')
            f.write('  down:\n')
            f.write('    here: debian:8.2\n')

        with open('.scuba.yml', 'w') as f:
            f.write('image: !from_yaml .gitlab.yml somewhere.down.here\n')

        config = scuba.config.load_config('.scuba.yml')
        self.assertEqual(config.image, 'debian:8.2')

    def test_load_config_image_from_yaml_nested_key_missing(self):
        '''load_config raises ConfigError when !from_yaml references nonexistant key'''
        with open('.gitlab.yml', 'w') as f:
            f.write('somewhere:\n')
            f.write('  down:\n')

        with open('.scuba.yml', 'w') as f:
            f.write('image: !from_yaml .gitlab.yml somewhere.NONEXISTANT\n')

        with self.assertRaises(scuba.config.ConfigError):
            scuba.config.load_config('.scuba.yml')

    def test_load_config_image_from_yaml_missing_file(self):
        '''load_config raises ConfigError when !from_yaml references nonexistant file'''
        with open('.scuba.yml', 'w') as f:
            f.write('image: !from_yaml .NONEXISTANT.yml image\n')

        with self.assertRaises(scuba.config.ConfigError):
            scuba.config.load_config('.scuba.yml')

    def test_load_config_image_from_yaml_unicode_args(self):
        '''load_config raises ConfigError when !from_yaml has unicode args'''
        with open('.scuba.yml', 'w') as f:
            f.write('image: !from_yaml .NONEXISTANT.yml ½\n')

        with self.assertRaises(scuba.config.ConfigError):
            scuba.config.load_config('.scuba.yml')

    def test_load_config_image_from_yaml_missing_arg(self):
        '''load_config raises ConfigError when !from_yaml has missing args'''
        with open('.gitlab.yml', 'w') as f:
            f.write('image: debian:8.2\n')

        with open('.scuba.yml', 'w') as f:
            f.write('image: !from_yaml .gitlab.yml\n')

        with self.assertRaises(scuba.config.ConfigError):
            scuba.config.load_config('.scuba.yml')

    ######################################################################
    # process_command

    def test_process_command_image(self):
        '''process_command returns the image and entrypoint'''
        image_name = 'test_image'
        entrypoint = 'test_entrypoint'

        cfg = scuba.config.ScubaConfig(
                image = image_name,
                entrypoint = entrypoint,
                )
        result = cfg.process_command([])
        self.assertEqual(result.image, image_name)
        self.assertEqual(result.entrypoint, entrypoint)

    def test_process_command_empty(self):
        '''process_command handles no aliases and an empty command'''
        cfg = scuba.config.ScubaConfig(
                image = 'na',
                )
        result = cfg.process_command([])
        self.assertEqual(result.script, None)


    def test_process_command_no_aliases(self):
        '''process_command handles no aliases'''
        cfg = scuba.config.ScubaConfig(
                image = 'na',
                )
        result = cfg.process_command(['cmd', 'arg1', 'arg2'])
        self.assertEqual(len(result.script), 1)
        self.assertEqual(shlex.split(result.script[0]), ['cmd', 'arg1', 'arg2'])

    def test_process_command_aliases_unused(self):
        '''process_command handles unused aliases'''
        cfg = scuba.config.ScubaConfig(
                image = 'na',
                aliases = dict(
                    apple = 'banana',
                    cat = 'dog',
                    ),
                )
        result = cfg.process_command(['cmd', 'arg1', 'arg2'])
        self.assertEqual(len(result.script), 1)
        self.assertEqual(shlex.split(result.script[0]), ['cmd', 'arg1', 'arg2'])

    def test_process_command_aliases_used_noargs(self):
        '''process_command handles aliases with no args'''
        cfg = scuba.config.ScubaConfig(
                image = 'na',
                aliases = dict(
                    apple = 'banana',
                    cat = 'dog',
                    ),
                )
        result = cfg.process_command(['apple', 'arg1', 'arg2'])
        self.assertEqual(len(result.script), 1)
        self.assertEqual(shlex.split(result.script[0]), ['banana', 'arg1', 'arg2'])

    def test_process_command_aliases_used_withargs(self):
        '''process_command handles aliases with args'''
        cfg = scuba.config.ScubaConfig(
                image = 'na',
                aliases = dict(
                    apple = 'banana cherry "pie is good"',
                    cat = 'dog',
                    ),
                )
        result = cfg.process_command(['apple', 'arg1', 'arg2 with spaces'])
        self.assertEqual(len(result.script), 1)
        self.assertEqual(shlex.split(result.script[0]), ['banana', 'cherry', 'pie is good', 'arg1', 'arg2 with spaces'])

    def test_process_command_multiline_aliases_used(self):
        '''process_command handles multiline aliases'''
        cfg = scuba.config.ScubaConfig(
                image = 'na',
                aliases = dict(
                    apple = dict(script=[
                        'banana cherry "pie is good"',
                        'so is peach',
                    ]),
                    cat = 'dog',
                    ),
                )
        result = cfg.process_command(['apple'])
        self.assertEqual(len(result.script), 2)
        self.assertEqual(shlex.split(result.script[0]), ['banana', 'cherry', 'pie is good'])
        self.assertEqual(shlex.split(result.script[1]), ['so', 'is', 'peach'])

    def test_process_command_multiline_aliases_forbid_user_args(self):
        '''process_command raises ConfigError when args are specified with multiline aliases'''
        cfg = scuba.config.ScubaConfig(
                image = 'na',
                aliases = dict(
                    apple = dict(script=[
                        'banana cherry "pie is good"',
                        'so is peach',
                    ]),
                    cat = 'dog',
                    ),
                )
        with self.assertRaises(scuba.config.ConfigError):
            cfg.process_command(['apple', 'ARGS', 'NOT ALLOWED'])

    def test_process_command_alias_overrides_image(self):
        '''aliases can override the image'''
        cfg = scuba.config.ScubaConfig(
                image = 'default',
                aliases = dict(
                    apple = dict(
                        script = [
                            'banana cherry "pie is good"',
                            'so is peach',
                        ],
                        image = 'overridden',
                    ),
                ),
            )
        result = cfg.process_command(['apple'])
        self.assertEqual(result.image, 'overridden')

    def test_process_command_alias_overrides_image_and_entrypoint(self):
        '''aliases can override the image and entrypoint'''
        cfg = scuba.config.ScubaConfig(
                image = 'default',
                entrypoint = 'default_entrypoint',
                aliases = dict(
                    apple = dict(
                        script = [
                            'banana cherry "pie is good"',
                            'so is peach',
                        ],
                        image = 'overridden',
                        entrypoint = 'overridden_entrypoint',
                    ),
                ),
            )
        result = cfg.process_command(['apple'])
        self.assertEqual(result.image, 'overridden')
        self.assertEqual(result.entrypoint, 'overridden_entrypoint')

    def test_process_command_alias_overrides_image_and_empty_entrypoint(self):
        '''aliases can override the image and empty/null entrypoint'''
        cfg = scuba.config.ScubaConfig(
                image = 'default',
                entrypoint = 'default_entrypoint',
                aliases = dict(
                    apple = dict(
                        script = [
                            'banana cherry "pie is good"',
                            'so is peach',
                        ],
                        image = 'overridden',
                        entrypoint = '',
                    ),
                ),
            )
        result = cfg.process_command(['apple'])
        self.assertEqual(result.image, 'overridden')
        self.assertEqual(result.entrypoint, '')


    ############################################################################
    # Hooks

    def test_hooks_mixed(self):
        '''hooks of mixed forms are valid'''
        with open('.scuba.yml', 'w') as f:
            f.write('''
                image: na
                hooks:
                  root:
                    script:
                      - echo "This runs before we switch users"
                      - id
                  user: id
                ''')

        config = scuba.config.load_config('.scuba.yml')

        assert_seq_equal(
            config.hooks.get('root'),
            ['echo "This runs before we switch users"', 'id'])

        assert_seq_equal(
            config.hooks.get('user'),
            ['id'])

    def test_hooks_invalid_list(self):
        '''hooks with list not under "script" key are invalid'''
        with open('.scuba.yml', 'w') as f:
            f.write('''
                image: na
                hooks:
                  user:
                    - this list should be under
                    - a 'script'
                ''')

        with self.assertRaises(scuba.config.ConfigError):
            scuba.config.load_config('.scuba.yml')

    def test_hooks_missing_script(self):
        '''hooks with dict, but missing "script" are invalid'''
        with open('.scuba.yml', 'w') as f:
            f.write('''
                image: na
                hooks:
                  user:
                    not_script: missing "script" key
                ''')

        with self.assertRaises(scuba.config.ConfigError):
            scuba.config.load_config('.scuba.yml')


    ############################################################################
    # Env

    def test_env_top_dict(self):
        '''Top-level environment can be loaded (dict)'''
        with open('.scuba.yml', 'w') as f:
            f.write(r'''
                image: na
                environment:
                  FOO: This is foo
                  FOO_WITH_QUOTES: "\"Quoted foo\""    # Quotes included in value
                  BAR: "This is bar"
                  MAGIC: 42
                  SWITCH_1: true        # YAML boolean
                  SWITCH_2: "true"      # YAML string
                  EMPTY: ""
                  EXTERNAL:             # Comes from os env
                  EXTERNAL_NOTSET:      # Missing in os env
                ''')

        with mocked_os_env(EXTERNAL='Outside world'):
            config = scuba.config.load_config('.scuba.yml')

        expect = dict(
            FOO = "This is foo",
            FOO_WITH_QUOTES = "\"Quoted foo\"",
            BAR = "This is bar",
            MAGIC = "42",           # N.B. string
            SWITCH_1 = "True",      # Unfortunately this is due to str(bool(1))
            SWITCH_2 = "true",
            EMPTY = "",
            EXTERNAL = "Outside world",
            EXTERNAL_NOTSET = "",
        )
        self.assertEqual(expect, config.environment)


    def test_env_top_list(self):
        '''Top-level environment can be loaded (list)'''
        with open('.scuba.yml', 'w') as f:
            f.write(r'''
                image: na
                environment:
                  - FOO=This is foo                 # No quotes
                  - FOO_WITH_QUOTES="Quoted foo"    # Quotes included in value
                  - BAR=This is bar
                  - MAGIC=42
                  - SWITCH_2=true
                  - EMPTY=
                  - EXTERNAL                        # Comes from os env
                  - EXTERNAL_NOTSET                 # Missing in os env
                ''')

        with mocked_os_env(EXTERNAL='Outside world'):
            config = scuba.config.load_config('.scuba.yml')

        expect = dict(
            FOO = "This is foo",
            FOO_WITH_QUOTES = "\"Quoted foo\"",
            BAR = "This is bar",
            MAGIC = "42",           # N.B. string
            SWITCH_2 = "true",
            EMPTY = "",
            EXTERNAL = "Outside world",
            EXTERNAL_NOTSET = "",
        )
        self.assertEqual(expect, config.environment)


    def test_env_alias(self):
        '''Alias can have environment which overrides top-level'''
        with open('.scuba.yml', 'w') as f:
            f.write(r'''
                image: na
                environment:
                  FOO: Top-level
                  BAR: 42
                aliases:
                  al:
                    script: Don't care
                    environment:
                      FOO: Overridden
                      MORE: Hello world
                ''')

        config = scuba.config.load_config('.scuba.yml')

        self.assertEqual(config.environment, dict(
                FOO = "Top-level",
                BAR = "42",
            ))

        self.assertEqual(config.aliases['al'].environment, dict(
                FOO = "Overridden",
                MORE = "Hello world",
            ))

        # Does the environment get overridden / merged?
        ctx = config.process_command(['al'])

        self.assertEqual(ctx.environment, dict(
                FOO = "Overridden",
                BAR = "42",
                MORE = "Hello world",
            ))


    ############################################################################
    # Entrypoint

    def test_entrypoint_not_set(self):
        '''Entrypoint can be missing'''
        with open('.scuba.yml', 'w') as f:
            f.write(r'''
                image: na
                ''')

        config = scuba.config.load_config('.scuba.yml')
        self.assertIsNone(config.entrypoint)

    def test_entrypoint_null(self):
        '''Entrypoint can be set to null'''
        with open('.scuba.yml', 'w') as f:
            f.write(r'''
                image: na
                entrypoint:
                ''')

        config = scuba.config.load_config('.scuba.yml')
        self.assertEqual(config.entrypoint, '')     # Null => empty string

    def test_entrypoint_emptry_string(self):
        '''Entrypoint can be set to an empty string'''
        with open('.scuba.yml', 'w') as f:
            f.write(r'''
                image: na
                entrypoint: ""
                ''')

        config = scuba.config.load_config('.scuba.yml')
        self.assertEqual(config.entrypoint, '')

    def test_entrypoint_set(self):
        '''Entrypoint can be set'''
        with open('.scuba.yml', 'w') as f:
            f.write(r'''
                image: na
                entrypoint: my_ep
                ''')

        config = scuba.config.load_config('.scuba.yml')
        self.assertEqual(config.entrypoint, 'my_ep')

    def test_alias_entrypoint_null(self):
        '''Entrypoint can be set to null via alias'''
        with open('.scuba.yml', 'w') as f:
            f.write(r'''
                image: na
                entrypoint: na_ep
                aliases:
                  testalias:
                    entrypoint:
                    script:
                      - ugh
                ''')

        config = scuba.config.load_config('.scuba.yml')
        self.assertEqual(config.aliases['testalias'].entrypoint, '')    # Null => empty string

    def test_alias_entrypoint_empty_string(self):
        '''Entrypoint can be set to an empty string via alias'''
        with open('.scuba.yml', 'w') as f:
            f.write(r'''
                image: na
                entrypoint: na_ep
                aliases:
                  testalias:
                    entrypoint: ""
                    script:
                      - ugh
                ''')

        config = scuba.config.load_config('.scuba.yml')
        self.assertEqual(config.aliases['testalias'].entrypoint, '')

    def test_alias_entrypoint(self):
        '''Entrypoint can be set via alias'''
        with open('.scuba.yml', 'w') as f:
            f.write(r'''
                image: na
                entrypoint: na_ep
                aliases:
                  testalias:
                    entrypoint: use_this_ep
                    script:
                      - ugh
                ''')

        config = scuba.config.load_config('.scuba.yml')
        self.assertEqual(config.aliases['testalias'].entrypoint, 'use_this_ep')
