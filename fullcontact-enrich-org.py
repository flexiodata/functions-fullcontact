
# ---
# name: fullcontact-enrich-org
# deployed: true
# title: FullContact Organization Enrichment
# description: Return information about an organization based on domain name.
# params:
#   - name: domain
#     type: string
#     description: The domain name of the organization from which you want to retrieve information. For example, "apple.com".
#     required: true
#   - name: properties
#     type: array
#     description: The properties to return (defaults to all properties). See "Returns" for a listing of the available properties.
#     required: false
# returns:
#   - name: name
#     type: string
#     description: The name of the organization (default)
#   - name: location
#     type: string
#     description: The location or address of the organization
#   - name: twitter_url
#     type: string
#     description: The URL of the organization's Twitter profile
#   - name: linkedin_url
#     type: string
#     description: The URL of the organization's LinkedIn profile
#   - name: bio
#     type: string
#     description: A biography of the organization
#   - name: logo
#     type: string
#     description: The URL of the organization's logo
#   - name: website
#     type: string
#     description: The URL of the organization's website
#   - name: founded
#     type: string
#     description: The year the organization was founded
#   - name: employees
#     type: string
#     description: The approximate number of employees in the organization
#   - name: locale
#     type: string
#     description: The locale of the organization
#   - name: category
#     type: string
#     description: The category of the organization; possible values are **Adult**, **Email Provider**, **Education**, **SMS**, or **Other**
# examples:
#   - '"apple.com"'
#   - '"stripe.com", "twitter_url, linkedin_url"'
#   - '"fullcontact.com", "website, logo, founded, employees"'
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
    params['domain'] = {'required': True, 'type': 'string'}
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
    property_map['name'] = 'name'
    property_map['location'] = 'location'
    property_map['twitter_url'] = 'twitter'
    property_map['linkedin_url'] = 'linkedin'
    property_map['bio'] = 'bio'
    property_map['logo'] = 'logo'
    property_map['website'] = 'website'
    property_map['founded'] = 'founded'
    property_map['employees'] = 'employees'
    property_map['locale'] = 'locale'
    property_map['category'] = 'category'

    # get the properties to return and the property map
    properties = [p.lower().strip() for p in input['properties']]

    # if we have a wildcard, get all the properties
    if len(properties) == 1 and properties[0] == '*':
        properties = list(property_map.keys())

    # see here for more info:
    # https://docs.fullcontact.com/#company-enrichment

    data = json.dumps({
        'domain': input['domain'].lower().strip()
    })
    headers = {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + auth_token
    }
    url = 'https://api.fullcontact.com/v3/company.enrich'

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

def requests_retry_session(
    retries=3,
    backoff_factor=0.3,
    status_forcelist=(429, 500, 502, 503, 504),
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
