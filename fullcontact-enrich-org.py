
# ---
# name: fullcontact-enrich-org
# deployed: true
# title: FullContact People Enrichment
# description: Return information about an organization by supplying the domain name
# params:
#   - name: domain
#     type: string
#     description: The domain name from which you to retrieve information. For example, "apple.com".
#     required: true
#   - name: properties
#     type: array
#     description: The properties to return (defaults to 'full_name'). See "Notes" for a listing of the available properties.
#     required: false
# examples:
#   - '"apple.com"'
#   - '"stripe.com", "twitter_url, linkedin_url"'
#   - '"fullcontact.com", "website, logo, founded, employees"'
# notes: |
#   The following properties are allowed:
#     * `name`: the name of the organization
#     * `location`: the location or address of the organization
#     * `twitter_url`: URL of the organization's Twitter profile
#     * `linkedin_url`: URL of the organization's LinkedIn profile
#     * `bio`: biography of the organization
#     * `logo`: URL of the organization's logo
#     * `website`: URL of the organization's website
#     * `founded`: the year the organization was founded
#     * `employees`: the approximate number of employees in the organization
#     * `locale`: the locale of the organization
#     * `category`: the category of the organization -- possible values are `Adult`, `Email Provider`, `Education`, `SMS`, or `Other`
# ---

import json
import requests
import urllib
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
    params['properties'] = {'required': False, 'validator': validator_list, 'coerce': to_list, 'default': 'full_name'}
    input = dict(zip(params.keys(), input))

    # validate the mapped input against the validator
    # if the input is valid return an error
    v = Validator(params, allow_unknown = True)
    input = v.validated(input)
    if input is None:
        raise ValueError

    try:

        # see here for more info:
        # https://docs.fullcontact.com/#person-enrichment
        data = json.dumps({
            'domain': input['domain']
        })
        headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + auth_token
        }
        url = 'https://api.fullcontact.com/v3/company.enrich'

        # get the response data as a JSON object
        response = requests.post(url, data=data, headers=headers)
        content = response.json()

        # map this function's property names to the API's property names
        property_map = {
            'name': content.get('name', ''),
            'location': content.get('location', ''),
            'twitter_url': content.get('twitter', ''),
            'linkedin_url': content.get('linkedin', ''),
            'bio': content.get('bio', ''),
            'logo': content.get('logo', ''),
            'website': content.get('website', ''),
            'founded': content.get('founded', ''),
            'employees': content.get('employees', ''),
            'locale': content.get('locale', ''),
            'category': content.get('category', '')
        }

        # limit the results to the requested properties
        properties = [property_map.get(p.lower().strip(), '') for p in input['properties']]
        result = [properties]

        # return the results
        result = json.dumps(result, default=to_string)
        flex.output.content_type = "application/json"
        flex.output.write(result)

    except:
        raise RuntimeError

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
