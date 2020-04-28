
# ---
# name: fullcontact-find-person
# deployed: true
# title: FullContact Find Person
# description: Return a person's profile information based on their email address and LinkedIn profile.
# params:
#   - name: email
#     type: string
#     description: The email address of the person you wish you find.
#     required: true
#   - name: linkedin
#     type: string
#     description: The LinkedIn username of the person you wish to find.
#     required: true
#   - name: properties
#     type: array
#     description: The properties to return (defaults to all properties). See "Returns" for a listing of the available properties.
#     required: false
# returns:
#   - name: full_name
#     type: string
#     description: The full name of the person (default)
#   - name: age_range
#     type: string
#     description: The age range of the person
#   - name: gender
#     type: string
#     description: The gender of the person
#   - name: location
#     type: string
#     description: The location of the person (varies depending on data quality)
#   - name: title
#     type: string
#     description: The current or most recent job title of the person
#   - name: organization
#     type: string
#     description: The current or most recent place of work of the person
#   - name: twitter_url
#     type: string
#     description: The URL of the person's Twitter profile
#   - name: facebook_url
#     type: string
#     description: The URL of the person's Facebook profile
#   - name: linkedin_url
#     type: string
#     description: The URL of the person's LinkedIn profile
#   - name: bio
#     type: string
#     description: A biography of the person
#   - name: avatar_url
#     type: string
#     description: The URL of the person's photo
# examples:
#   - '"tcook@apple.com"'
#   - '"bill.gates@microsoft.com"'
#   - '"jeff@amazon.com", "full_name, title, bio"'
# ---

import json
import urllib
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import itertools
from datetime import *
from cerberus import Validator
from collections import OrderedDict

# main function entry point
def flexio_handler(flex):

    # get the api key from the variable input
    auth_token = dict(flex.vars).get('fullcontact_api_key')
    if auth_token is None:
        flex.output.content_type = "application/json"
        flex.output.write([[""]])
        return

    # get the input
    input = flex.input.read()
    try:
        input = json.loads(input)
        if not isinstance(input, list): raise ValueError
    except ValueError:
        raise ValueError

    # define the expected parameters and map the values to the parameter names
    # based on the positions of the keys/values
    params = OrderedDict()
    params['email'] = {'required': True, 'type': 'string'}
    params['profile'] = {'required': True, 'type': 'string'}
    params['properties'] = {'required': False, 'validator': validator_list, 'coerce': to_list, 'default': '*'}
    input = dict(zip(params.keys(), input))

    # validate the mapped input against the validator
    # if the input is valid return an error
    v = Validator(params, allow_unknown = True)
    input = v.validated(input)
    if input is None:
        raise ValueError

    # map this function's property names to the API's property names
    property_map = OrderedDict()
    property_map['full_name'] = 'fullName'
    property_map['age_range'] = 'ageRange'
    property_map['gender'] = 'gender'
    property_map['location'] = 'location'
    property_map['title'] = 'title'
    property_map['organization'] = 'organization'
    property_map['twitter_url'] = 'twitter'
    property_map['facebook_url'] = 'facebook'
    property_map['linkedin_url'] = 'linkedin'
    property_map['bio'] = 'bio'
    property_map['avatar_url'] = 'avatar'

    # get the properties to return and the property map
    properties = [p.lower().strip() for p in input['properties']]

    # if we have a wildcard, get all the properties
    if len(properties) == 1 and properties[0] == '*':
        properties = list(property_map.keys())

    try:

        # see here for more info:
        # https://docs.fullcontact.com/#person-enrichment
        # https://docs.fullcontact.com/#multi-field-request

        email = input['email'].lower().strip()
        profile = input['profile'].lower().strip()

        data = {}
        if len(email) > 0:
            data['emails'] = [
                input['email'].lower().strip()
            ]
        if len(profile) > 0:
            data['profiles'] = [
                {
                    "service": "linkedin",
                    "username": input['profile'].lower().strip()
                }
            ]
        data = json.dumps(data)

        headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + auth_token
        }
        url = 'https://api.fullcontact.com/v3/person.enrich'

        # get the response data as a JSON object
        response = requests_retry_session().post(url, data=data, headers=headers)
        response.raise_for_status()
        content = response.json()

        # limit the results to the requested properties
        properties = [content.get(property_map.get(p,''),'') or '' for p in properties]
        result = [properties]

        # return the results
        result = json.dumps(result, default=to_string)
        flex.output.content_type = "application/json"
        flex.output.write(result)

    except:
        flex.output.content_type = 'application/json'
        flex.output.write([['']])

def requests_retry_session(
    retries=3,
    backoff_factor=0.3,
    status_forcelist=(500, 502, 504),
    session=None,
):
    session = session or requests.Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

def validator_list(field, value, error):
    if isinstance(value, str):
        return
    if isinstance(value, list):
        for item in value:
            if not isinstance(item, str):
                error(field, 'Must be a list with only string values')
        return
    error(field, 'Must be a string or a list of strings')

def to_string(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, (Decimal)):
        return str(value)
    return value

def to_list(value):
    # if we have a list of strings, create a list from them; if we have
    # a list of lists, flatten it into a single list of strings
    if isinstance(value, str):
        return value.split(",")
    if isinstance(value, list):
        return list(itertools.chain.from_iterable(value))
    return None
