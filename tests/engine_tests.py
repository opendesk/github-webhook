import json
import os
import unittest

from mock import Mock
from pyramid import testing
from webhook import engine

class EngineUnitTests(unittest.TestCase):
    """Testing..."""
    def setUp(self):
        testing.setUp()

    def tearDown(self):
        testing.tearDown()
  
    def test_get_author(self):
        """Should return dummy author..."""
        dummy_data = { "commits":[ { "author":{  "name":"dummy"  }}]}
        result = engine.get_author(dummy_data)
        self.assertEquals('dummy',result)

    def test_get_branch(self):
        """Should return dummy branch..."""
        dummy_data = {  "ref":"refs/heads/dummy" }
        result = engine.get_branch(dummy_data)
        self.assertEquals('dummy',result)

    def test_whitelist(self):
        """only .json files and files/name.ext should pass..."""
        valid_files = ['table.json', 'lala/files/hha/lala.tst']
        result = engine._whitelist(valid_files)
        self.assertEquals(valid_files,result)

        valid_files = ['lala/json/_lala.json.table.json', 'lala/filess/_product.json']
        result = engine._whitelist(valid_files)
        for items in valid_files:
            self.assertNotIn(items,result)

    def test_get_base_url(self):
        """Getting base URL from GIT webhook JSON..."""
        dummy_data = {'commits':[{'url':'https://github.com/andrecp/github_webhook/commit/852d05ed0c096df331'}]}
        result = engine.get_base_url(dummy_data)
        self.assertEquals('https://github.com/andrecp/github_webhook/',result)
        
   
    def test_add_one_table(self):
        """Adding one table..."""
        dummy_data = { "commits":[\
        {\
         "added":[\
            "table.json"\
         ],\
         "removed":[],\
         "modified":[]}]}
        result = engine.get_changes(dummy_data)
        self.assertEquals('table.json',''.join(result[0]))
        self.assertFalse(result[1])

    def test_add_two_tables_update_one(self):
        """Adding two tables and updating one..."""
        dummy_data = { "commits":[\
        {\
         "added":[\
            "table.json",\
            "table2.json"\
         ],\
         "removed":[],\
         "modified":["table3.json"]}]}
        result = engine.get_changes(dummy_data)
        self.assertIn('table.json',result[0])
        self.assertIn('table2.json',result[0])
        self.assertIn('table3.json',result[1])
        self.assertFalse(result[2])

    def test_add_two_tables_update_one_remove_one(self):
        """Adding two tables, updating one and removing other..."""
        dummy_data = { "commits":[\
        {\
         "added":[\
            "table.json",\
            "table2.json"\
         ],\
         "removed":["table3.json"],\
         "modified":["table4.json"]}]}
        result = engine.get_changes(dummy_data)
        self.assertIn('table.json',result[0])
        self.assertIn('table2.json',result[0])
        self.assertIn('table3.json',result[2])
        self.assertIn('table4.json',result[1])


    def test_get_dict_w_last_commits(self):
        """Testing commit history dict resolving..."""
        dummy_data = [\
        {\
         "added":["table.json", "table4.json", "table2.json"],\
         "removed":[],\
         "modified":["lean.json"]},\
         {\
         "added":["chair.json"],\
         "removed":[],\
         "modified":["table.json", "table4.json", "table2.json"]},
         {\
         "added":["table.json"],\
         "removed":["table4.json", "table2.json"],\
         "modified":["luan.jsaon"]},\
        ]
        added, modified, removed = engine._get_dict_w_last_commits(dummy_data)

        # timestamp 3, last added in newer
        self.assertEquals(3,added['table.json'][1])
        # timestamp 2, last modified in 2nd commit
        self.assertEquals(2,modified['table2.json'][1])
        self.assertEquals('table4.json',removed['table4.json'][0])

    def test_get_changes_w_commits_history(self):
        """Testing commit history resolving, order of add,modified,delete matters..."""
        dummy_data = {"commits":[\
        {\
         "added":["table.json", "table4.json", "table2.json"],\
         "removed":[],\
         "modified":["lean.json"]},\
         {\
         "added":["chair.json"],\
         "removed":["chair.json", "table.json"],\
         "modified":["table.json", "table4.json", "table2.json"]},
         {\
         "added":["table.json"],\
         "removed":["table4.json", "table2.json"],\
         "modified":["luan.jsaon"]},\
        ]}
        added, modified, removed = engine.get_changes(dummy_data)

        # We removed it into the second commit
        self.assertIn("table.json",added)
        # timestamp 2, last modified in 2nd commit
        self.assertNotIn("chair.json",added)
        # All other files got re-added, only chair.json left
        self.assertIn("chair.json",removed)

    def test_validated_signature(self):
        """Testing the algorithm for validating a signature key from github..."""
        json_data=open(u'testing_commits/add_from_master_w_security.json', 'rb')
        data = json_data.read(6573)

        return_value = engine.validate_signature(data, u'sha1=28b51de0d6de6d8c19a2ff76882578f7177be5c8')
        self.assertTrue(return_value)

    def test_get_bearer_token(self):
        """Should return the bearer token for the target api..."""
        return_value = engine.get_bearer_token(os.environ.get('GITHUB_WEBHOOK_opendesk_collection__API_URL'))
        self.assertEquals(return_value, os.environ.get(b'GITHUB_WEBHOOK_opendesk_collection__SECRET_TOKEN'))

    def test_create_async_lists_by_structure(self):
        """Should return a list with the requests created and ordered...
        

        '.../lean/desk/design.json'
        '.../lean/desk/standard/product.json'
        '.../lean/desk/standard/wisa/fileset.json'
        '.../lean/desk/standard/ply/fileset.json'
        '.../lean/desk/wayra/product.json'
        '.../lean/desk/wayra/ply/fileset.json'

        -> PUT {design.json} .../lean/desk
        -> wait ...
           -> PUT {product.json} .../lean/desk/standard
           -> PUT {product.json} .../lean/desk/wayra
           -> wait ...
              -> PUT {fileset.json} .../lean/desk/standard/wisa
              -> PUT {fileset.json} .../lean/desk/standard/ply
              -> PUT {fileset.json} .../lean/desk/wayra/ply
        """
        requests = ['ranges/lean/desk/design.json',
                    'ranges/lean/desk/standard/product.json',
                    'ranges/lean/desk/standard/wisa/fileset.json',
                    'ranges/lean/desk/standard/ply/fileset.json',
                    'ranges/lean/desk/wayra/product.json',
                    'ranges/lean/desk/wayra/ply/fileset.json']
        expected_lists =[
                        ['ranges/lean/desk/design.json'],
                        ['ranges/lean/desk/standard/product.json',
                         'ranges/lean/desk/wayra/product.json'],
                        ['ranges/lean/desk/standard/wisa/fileset.json',
                         'ranges/lean/desk/standard/ply/fileset.json',
                         'ranges/lean/desk/wayra/ply/fileset.json']
                        ]

        requests = engine.create_async_lists_by_structure(requests)
        self.assertEquals(requests, expected_lists)