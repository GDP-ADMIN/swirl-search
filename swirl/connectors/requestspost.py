'''
@author:     Sid Probstein
@contact:    sid@swirl.today
'''

from sys import path
from os import environ

import django

import json


import urllib.parse

from swirl.utils import swirl_setdir
path.append(swirl_setdir()) # path to settings.py file
environ.setdefault('DJANGO_SETTINGS_MODULE', 'swirl_server.settings')
django.setup()

import requests

from celery.utils.log import get_task_logger
logger = get_task_logger(__name__)

from swirl.connectors.utils import bind_query_mappings

from swirl.connectors.requests import Requests

########################################
########################################

class RequestsPost(Requests):


    type = "RequestsPost"

    def __init__(self, provider_id, search_id, update, request_id=''):
        super().__init__(provider_id, search_id, update, request_id)

    ########################################

    def validate_query(self, session=None):
        logger.debug(f"{self}: https post request validate_query() returning true")
        try:
            json_object = json.loads(json.dumps(self.provider.post_query_template))
        except ValueError as e:
            logger.warning(f"{self}: https post request validate_query() failed JSON validation, passing anyways")
            return True
        return True

    def get_method(self):
        return 'post'

    def send_request(self, url, params=None, query=None, **kwargs):
        headers = dict({
            "Content-Type": "application/json"
        })
        if 'USE_X_FORM' in self.provider.query_mappings:
            headers = dict({
                "Content-Type": "application/x-www-form-urlencoded"
            })
        headers.update(kwargs.get("headers", {}))
        kwargs['headers'] = headers

        post_json_str = json.dumps(self.provider.post_query_template)

        if post_json_str and post_json_str != '{}' and post_json_str != '"{}"':
            post_json_str     = bind_query_mappings(post_json_str, self.provider.query_mappings, self.provider.url)
            qs_to_provider = self.query_string_to_provider
            vector_qs_to_provider = ""

            if 'USE_BODY_AS_QS' in self.provider.query_mappings:
                body_data = json.loads(query)
                qs_to_provider = body_data.get("query_string", "")
                # Extract the array of floats and ensure it's a list
                vector_qs_to_provider_str = body_data.get("vector_query_string")
                if isinstance(vector_qs_to_provider_str, list):
                    # Convert the list of floats into a comma-separated string
                    vector_qs_to_provider_str = ",".join(map(str, vector_qs_to_provider_str))

            if '{query_string}' in post_json_str:
                if 'NO_URL_ENCODE' in self.provider.query_mappings:
                    post_json_str = post_json_str.replace('{query_string}', qs_to_provider)
                else:
                    post_json_str = post_json_str.replace('{query_string}', urllib.parse.quote_plus(qs_to_provider))

            if '{vector_query_string}' in post_json_str:
                if 'NO_URL_ENCODE' in self.provider.query_mappings:
                    post_json_str = post_json_str.replace('{vector_query_string}', vector_qs_to_provider_str)
                else:
                    post_json_str = post_json_str.replace('{vector_query_string}', urllib.parse.quote_plus(vector_qs_to_provider_str))
            post_json = json.loads(post_json_str)
        else:
            post_json=query

        logger.debug(f"post_json_str:{post_json_str} query:{query} post_json:{post_json}")

        if 'USE_X_FORM' in self.provider.query_mappings:
            return requests.post(url, params=params, data=post_json, **kwargs)
        return requests.post(url, params=params, json=post_json, **kwargs)
