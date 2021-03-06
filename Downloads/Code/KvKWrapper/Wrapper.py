import json
import requests
import warnings

warnings.filterwarnings("ignore")

from fuzzywuzzy import fuzz
from APIConfig import APIConfig


class Wrapper(APIConfig):

    def __init__(self, company_name=None):
        super().__init__()
        self.company_name = company_name.strip() if company_name else None
        self.best_match_kvk = self.free_text_search()
        self.list_of_branches = self.retrieve_kvk_id_best_match()
        self.profile()


    # A function to check if json is really json file, if not catch a value error and return false
    def is_json(self, myjson):
        try:
            json_object = json.loads(myjson)
        except ValueError:
            return False
        return True

    #Determine match quality of search string with response string
    #This overcomes the problem where the search call returns a company which does not match the company you want
    #For example: search "Gemeente Utrecht" gives Gereformeerd kerkgenootschap Utrecht.

    def get_fuzzy_score(self, items):

        fuzzy_dict = dict()

        for item in items:

            # Sometimes either businessname or shortbusinessname is provided
            try:
                cur_comp = item["tradeNames"]["businessName"]

            except:
                try:
                    cur_comp = item["tradeNames"]["shortBusinessName"]
                except:
                    pass
            cur_comp = cur_comp.upper()
            fuzzy_dict[cur_comp] = fuzz.ratio(self.company_name, cur_comp)

        best_match = max(fuzzy_dict, key=fuzzy_dict.get)
        text = 'Best Free-Search Text Match for {} is: {}, with matching score {}'.format(self.company_name, best_match, max(fuzzy_dict.values()))
        print(text)

        if fuzzy_dict.get(best_match) < 75:
            print("No accurate match found in KvK for this company name")
            return False
        else:
            return best_match


    # Function to retrieve a kvk number based on a name of a company. It's the same as doing a search, multiple results coul
    # occur.
    def free_text_search(self):

        if self.company_name:
            self.company_name = self.company_name.upper()

            # use the openkvk API to search for dossiers based on company name
            r = requests.get(self.kvk_search.format(self.company_name, self.user_key))

            kvk_name = dict()

            # if request is successful (200), check if json is really json and use first result and append to array.
            if r.status_code == 200:

                if self.is_json(r.text):

                    r_json = json.loads(r.text)

                    if r_json:

                        items = r_json['data']['items']

                        print(items)

                        best_match = self.get_fuzzy_score(items)

            # At this point we have the right kvk id.
            # For this kvk id, we want all branchNumbers

            # If best match has a matching score of 75 or higher return company.
            # Otherwise throw error

            #get kvk id of best match

            for x in items:
                print(x, best_match)
                if x['tradeNames']['shortBusinessName'].upper() == best_match:
                    kvk_id = x['kvkNumber']
                    print(kvk_id)
                    break

            return kvk_id

        else:
            return False

    # At this point we have the right kvk id.
    # For this kvk id, we want all branchNumbers
    def retrieve_kvk_id_best_match(self):

        if self.best_match_kvk != False:
            r = requests.get(self.kvk_search.format(self.best_match_kvk, self.user_key))

            if r.status_code == 200:
                if self.is_json(r.text):
                    r_json = json.loads(r.text)
                    print(r_json)
                    if r_json:

                        items = r_json['data']['items']

                        print([x['branchNumber'] for x in items if x['isBranch'] == True])
                        return [x['branchNumber'] for x in items if x['isBranch'] == True]

    def profile(self):

        data_agg = {}

        for branches in self.list_of_branches:

            # use API RESTurl to get company info
            q = self.best_match_kvk + " " + branches
            print('query', q)
            request_string  = self.kvk_profile.format(branches, self.user_key)

            print(request_string)

            r = requests.get(request_string)

            if r.status_code == 200 and r.text:

                if self.is_json(r.text):

                    data = json.loads(r.text)

                    item = data.get('data', {}).get('items', [{}])[0]
                    data_agg[branches] = item

        self.data = data_agg